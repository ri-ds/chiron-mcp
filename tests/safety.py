"""The invariants that must hold, or the server is unsafe.

Discovers the dataset, the concept and the identity's access level at runtime, so it
works against any Chiron deployment. Override the dataset with CHIRON_MCP_TEST_DATASET.

    CHIRON_MCP_USERNAME=<user> .venv/bin/python tests/safety.py

Exit code 0 means every invariant held.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chiron_mcp import server as S  # noqa: E402

fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {detail[:140]}")
    if not cond:
        fails.append(label)


def pick_dataset() -> tuple[str, str]:
    """Return (dataset_id, access_level) for the first dataset this identity can use."""
    forced = os.environ.get("CHIRON_MCP_TEST_DATASET")
    info = S.chiron_datasets(forced) if forced else S.chiron_datasets()
    if "error" in info:
        sys.exit(f"cannot list datasets: {info['error']}")
    usable = [d for d in info["datasets"] if d.get("accessible")]
    if not usable:
        sys.exit(
            "No dataset is reachable by this identity. Grant one with:\n"
            "  .venv/bin/python scripts/grant_access.py --user <user> "
            "--datasets <dataset> --level deid"
        )
    return usable[0]["dataset_id"], usable[0]["access_level"]


# Processors whose filter takes a single term, which is all this test needs. Date,
# number and age processors want min/max pairs and are deliberately skipped.
SIMPLE = ("CohortDefCategory", "CohortDefBoolean", "CohortDefText", "CohortDefTextCustomSort")


def pick_concept(ds: str) -> tuple[str, str] | tuple[None, None]:
    """Find a concept with a single-term filter and at least one real value."""
    for c in (S.chiron_find_concepts(ds, limit=40).get("concepts") or []):
        cid = c["concept_id"]
        desc = S.chiron_describe_concept(ds, cid, include_statistics=False)
        processor = desc.get("filter_input", {}).get("processor", "")
        if processor not in SIMPLE:
            continue
        if S.chiron_concept_values(ds, cid, limit=3).get("values"):
            return cid, processor
    return None, None


def main() -> int:
    ds, level = pick_dataset()
    print(f"===== identity: {os.environ.get('CHIRON_MCP_USERNAME')} "
          f"| dataset: {ds} | access: {level}\n")

    # --- aggregate identities must be refused subject-level data ----------------
    if level == "agg":
        probes = [
            ("count_cohort", lambda: S.chiron_count_cohort(ds, [])),
            ("run_table", lambda: S.chiron_run_table(ds, [], [{"concept_id": "any"}])),
            ("concept_values", lambda: S.chiron_concept_values(ds, "any")),
            ("export_table", lambda: S.chiron_export_table(ds, [], [{"concept_id": "any"}], 5)),
        ]
        for name, fn in probes:
            r = fn()
            check(
                f"agg refused on {name}",
                "error" in r and "subject-level" in r["error"],
                str(r)[:120],
            )
        print()
        return 1 if fails else 0

    # --- an errored cohort_def must never execute -------------------------------
    # clean_cohort_def reduces an errored definition to [], and an empty cohort_def
    # matches EVERY subject, so running one would silently return the whole dataset.
    bogus = [{"collection_id": "no_such_collection", "list": [{"concept_id": "nope"}]}]
    check(
        "errored cohort_def refused (not silently whole-dataset)",
        "error" in S.chiron_count_cohort(ds, bogus),
        str(S.chiron_count_cohort(ds, bogus))[:140],
    )

    # --- a failed transformation must not hand back a chainable cohort ----------
    bad = S.chiron_edit_cohort(ds, [], {"type": "add_entry", "concept_id": "no_such_concept"})
    check(
        "failed filter returns no reusable cohort_def",
        not bad.get("successful") and "cohort_def" not in bad,
        f"keys={sorted(bad)}",
    )

    # --- a real filter must narrow the cohort -----------------------------------
    concept_id, processor = pick_concept(ds)
    if not concept_id:
        print("SKIP  no single-term filterable concept found on this dataset")
    else:
        vals = S.chiron_concept_values(ds, concept_id, limit=3)
        term = vals["values"][0]["category"] if vals.get("values") else None

        # The input field name depends on the concept's processor. This is exactly what
        # chiron_describe_concept exists to answer.
        transformation = {"type": "add_entry", "concept_id": concept_id}
        if "Category" in processor or "Boolean" in processor:
            transformation["selected_categories"] = [str(term)]
        else:
            transformation["chiron_text_field_selection"] = str(term)
            transformation["ignore_warnings"] = True

        print(f"\n>>> filtering {concept_id} ({processor}) == {term!r}")
        edit = S.chiron_edit_cohort(ds, [], transformation)
        check("filter applied", bool(edit.get("successful")), str(edit.get("errors")))

        if edit.get("successful"):
            base = S.chiron_count_cohort(ds, [])["subject_count"]
            filt = S.chiron_count_cohort(ds, edit["cohort_def"])
            print(f"counts: {base} -> {filt.get('subject_count')}")
            check(
                "filtered count <= unfiltered",
                filt.get("subject_count", base + 1) <= base,
                f"{filt.get('subject_count')} vs {base}",
            )
            check(
                "filtered cohort is not whole-dataset",
                not filt.get("is_whole_dataset"),
                json.dumps(filt, default=str)[:120],
            )

    # --- the unbounded export must require an acknowledged count ----------------
    r = S.chiron_export_table(ds, [], [{"concept_id": concept_id or "any"}], 0)
    check("export refuses without acknowledged count", "error" in r, str(r)[:120])

    print()
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
