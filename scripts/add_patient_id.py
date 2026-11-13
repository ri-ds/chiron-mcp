"""Give a Synthea dataset a "patient ID" variable, set up like dataset1_stored's.

    python scripts/add_patient_id.py synthea-10k --category demographics --first
    python scripts/add_patient_id.py synthea-10k --dry-run
    python scripts/add_patient_id.py synthea-10k --remove

In the deploy bundle:

    docker compose exec -T chiron python /app/scripts/add_patient_id.py synthea-10k \\
        --category demographics --first

dataset1_stored has `patient_id`: name "patient ID", a SubjectHyperlinkHandler on the
patients file's `Id` column, on the subject collection, multivalue, usable in cohorts,
tables and analysis, not flagged PHI. Chiron shows it as type "ID", linked to the
patient's timeline. The Synthea builder skipped `Id`, so the Synthea datasets lack it.

This adds the same variable without re-running the ETL (a single-source run on the
subject collection would cascade-delete every other table):

1. the concept and its handler argument, copied from dataset1's patient_id settings,
   placed in --category (first in it with --first) or, without a category, above the
   categories as dataset1 has it;
2. its lookup table, built by Chiron's own generate_sql_alchemy_lookup_table_for_concept;
3. one row per patient, valued with the patients file's Id. Chiron kept that Id at load
   time as the subject's "id" identifier (it matched every other file to patients by
   it). Checked: every patient has exactly one value, every value is a UUID, and, when
   --patients-csv is given, the set equals the file's Id column;
4. the indexes Chiron's ETL creates for such a column (names quoted: Chiron's own
   create_indexes cannot handle a hyphenated dataset id);
5. Chiron's concept search, rebuilt so the variable is searchable in the UI.

Refuses if the dataset already has the variable. If a later step fails, the table is
dropped and the concept deleted again. --remove takes the variable out the same way.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset", help="the dataset's unique_id, e.g. synthea-10k")
    ap.add_argument("--category", help="put the variable in this category of the dataset (by name)")
    ap.add_argument("--first", action="store_true", help="first in its category (order below the lowest there)")
    ap.add_argument("--name", default=None, help='the variable\'s name (default: the template\'s, "patient ID")')
    ap.add_argument("--template", default="patient_id", help="the concept whose settings are copied (default: dataset1_stored's patient_id)")
    ap.add_argument("--patients-csv", help="the patients file, to check the stored IDs against its Id column")
    ap.add_argument("--dry-run", action="store_true", help="report what would be done and change nothing")
    ap.add_argument("--remove", action="store_true", help="take the variable out again (table, concept, search)")
    args = ap.parse_args()

    from chiron_mcp.bootstrap import ensure_django

    ensure_django()
    from django.db import transaction
    from sqlalchemy import MetaData, text

    from chiron import models
    from chiron.etl.chiron_etl import ChironEtl
    from chiron.query_engine import get_db_writer
    from chiron.query_engine.postgres import database

    ds = models.Dataset.objects.filter(unique_id=args.dataset).first()
    if ds is None:
        print(f"no dataset {args.dataset!r}")
        return 2
    subject = ds.root_collection
    if subject is None:
        print(f"{args.dataset} has no root collection")
        return 2
    pid = f"{args.dataset}__{subject.permanent_id}__id".lower()
    writer = get_db_writer(ds, False)
    schema = database.get_schema_name_for_dataset(ds, False)
    existing = models.Concept.objects.filter(permanent_id=pid).first()

    def rebuild_search() -> None:
        ChironEtl(ds.id, 1000, False, None, False, False).create_concept_search_collection()
        print("concept search rebuilt")

    def drop_table(table_name: str) -> None:
        with writer.engine.connect() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table_name}"'))
            conn.commit()

    if args.remove:
        if existing is None:
            print(f"{pid} does not exist; nothing to remove.")
            return 1
        table_name = f"lkp_{pid}"
        if args.dry_run:
            print(f"would drop {schema}.{table_name}, delete concept {pid} and rebuild the search")
            return 0
        drop_table(table_name)
        with transaction.atomic():
            models.ConceptHandlerArg.objects.filter(concept=existing).delete()
            existing.delete()
        print(f"removed {pid} and {schema}.{table_name}")
        rebuild_search()
        return 0

    if existing is not None:
        print(f"{pid} already exists; nothing was changed.")
        return 1
    model = models.Concept.objects.filter(permanent_id=args.template).first()
    if model is None:
        print(f"no template concept {args.template!r} (dataset1_stored's patient_id is the usual one)")
        return 2
    source = models.Source.objects.get(collection=subject)

    category = None
    order = model.order
    if args.category:
        category = models.Category.objects.filter(dataset=ds, name__iexact=args.category).first()
        if category is None:
            names = sorted(c.name for c in models.Category.objects.filter(dataset=ds))
            print(f"no category {args.category!r} on {args.dataset}; it has: {names}")
            return 2
        if args.first:
            lowest = min((c.order for c in models.Concept.objects.filter(category=category)), default=1.0)
            order = min(0.0, float(lowest) - 1.0) if lowest <= 0 else 0.0

    # What Chiron kept at load time: each patient's Id, as the "id" identifier.
    with writer.engine.connect() as conn:
        subjects = conn.execute(text(f'SELECT count(*) FROM "{schema}".subject')).scalar()
        with_id = conn.execute(text(
            f"SELECT count(DISTINCT _subject_id) FROM \"{schema}\".subject_identification WHERE id_name = 'id'")).scalar()
        sample = [r[0] for r in conn.execute(text(
            f"SELECT id_value FROM \"{schema}\".subject_identification WHERE id_name = 'id' LIMIT 3"))]
    print(f"{args.dataset}: {subjects:,} patients, {with_id:,} with an 'id' identifier; sample {sample}")
    if with_id != subjects:
        print("not every patient has an 'id' identifier; stopping")
        return 1
    print(f"variable: {pid} ({args.name or model.name}, {model.concept_handler}), "
          f"category {category.name if category else 'none'}, order {order:g}, template {args.template}")
    if args.dry_run:
        print("dry run: nothing changed")
        return 0

    # 1. The concept, with the template's settings.
    with transaction.atomic():
        concept = models.Concept.objects.create(
            permanent_id=pid, name=args.name or model.name, name_plural=model.name_plural,
            description=model.description, source=source,
            concept_handler=model.concept_handler, collection=subject,
            category=category, order=order, multivalue=model.multivalue, published=model.published,
            include_in_cohort_def=model.include_in_cohort_def,
            include_in_table_def=model.include_in_table_def,
            include_in_analysis_def=model.include_in_analysis_def,
            has_phi=model.has_phi, exclude_from_aggregated=model.exclude_from_aggregated,
            prefilter_mode=model.prefilter_mode,
        )
        for arg in model.concepthandlerarg_set.all():
            models.ConceptHandlerArg.objects.create(concept=concept, name=arg.name, value=arg.value)
    print(f"concept {pid} created")

    table_name = None
    try:
        # 2. Its lookup table, by Chiron's own definition.
        metadata = MetaData()
        database.generate_sql_alchemy_table_for_subject_collection(subject, metadata)
        table = database.generate_sql_alchemy_lookup_table_for_concept(concept, metadata)
        table_name = table.name
        table.create(writer.engine, checkfirst=True)
        print(f"table {schema}.{table.name} created")

        # 3. One row per patient: the Id the patients file gave it.
        t0 = time.monotonic()
        with writer.engine.connect() as conn:
            n = conn.execute(text(f'''
                INSERT INTO "{schema}"."{table.name}" (_collection_id, "{pid}")
                SELECT i._subject_id, i.id_value
                FROM "{schema}".subject_identification i
                WHERE i.id_name = 'id'
                ORDER BY i._subject_id''')).rowcount
            conn.commit()
            rows = conn.execute(text(f'SELECT _collection_id, "{pid}" FROM "{schema}"."{table.name}"')).fetchall()
        stored = {r[1] for r in rows}
        per_patient = len(rows) == len({r[0] for r in rows})
        bad = [v for v in stored if not UUID.match(str(v))]
        print(f"{n:,} patient IDs stored in {time.monotonic() - t0:.1f} s ({subjects:,} patients); "
              f"one per patient: {per_patient}; non-UUID values: {len(bad)}; distinct: {len(stored):,}")
        ok = n == subjects and per_patient and not bad and len(stored) == subjects
        if args.patients_csv:
            with open(args.patients_csv, newline="", encoding="utf-8") as fh:
                ids = {row["Id"] for row in csv.DictReader(fh)}
            same = ids == stored
            print(f"check against {Path(args.patients_csv).name}: {len(ids):,} Ids in the file, identical: {same}")
            ok = ok and same
        if not ok:
            raise RuntimeError("the stored IDs do not check out")

        # 4. The indexes Chiron's ETL makes for this kind of column.
        with writer.engine.connect() as conn:
            for field in [pid] + [f"{pid}__{sub}" for sub in
                                  concept._instantiate_concept_handler(chironuser=None).get_stored_data_type()]:
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS "idx_{field}" '
                                  f'ON "{schema}"."{table.name}" ("{field}")'))
            conn.commit()
        print("indexes created")
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {exc}; taking the variable out again")
        if table_name:
            drop_table(table_name)
        with transaction.atomic():
            models.ConceptHandlerArg.objects.filter(concept=concept).delete()
            concept.delete()
        return 1

    # 5. Concept search, so the UI's variable search finds it.
    rebuild_search()
    print(f"done: {args.name or model.name} is {'first in ' + category.name if category and args.first else 'in place'} on {args.dataset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
