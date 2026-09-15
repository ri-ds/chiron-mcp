"""The invariants that must hold, or the server is unsafe."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from chiron_mcp import server as S

DS = "dataset1_stored"
fails = []

def check(label, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {detail[:150]}")
    if not cond: fails.append(label)

who = os.environ["CHIRON_MCP_USERNAME"]
print(f"===== identity: {who}\n")

if who == "agguser":
    for name, fn in [
        ("count_cohort", lambda: S.chiron_count_cohort(DS, [])),
        ("run_table", lambda: S.chiron_run_table(DS, [], [{"concept_id": "encounter_id"}])),
        ("concept_values", lambda: S.chiron_concept_values(DS, "encounter_id")),
        ("export_table", lambda: S.chiron_export_table(DS, [], [{"concept_id":"encounter_id"}], 5)),
    ]:
        r = fn()
        check(f"agg refused on {name}", "error" in r and "cannot see subject-level" in r["error"], str(r)[:120])
    sys.exit(1 if fails else 0)

# --- deid identity -------------------------------------------------------
# An errored cohort_def must never execute: clean_cohort_def reduces it to [],
# which matches EVERY subject.
bogus = [{"collection_id": "nope", "list": [{"concept_id": "does_not_exist"}]}]
r = S.chiron_count_cohort(DS, bogus)
check("errored cohort_def refused (not silently whole-dataset)",
      "error" in r, str(r)[:160])

# --- real filter round trip ---------------------------------------------
vals = S.chiron_concept_values(DS, "encounter_id", limit=3)
first = vals["values"][0]["category"] if vals.get("values") else None
print(f"\n>>> filtering encounter_id == {first!r}")
edit = S.chiron_edit_cohort(DS, [], {
    "type": "add_entry",
    "concept_id": "encounter_id",
    "chiron_text_field_selection": str(first),
})
print("edit:", json.dumps(edit, default=str)[:400])
check("filter applied", edit.get("successful"), str(edit.get("errors")))

if edit.get("successful"):
    cd = edit["cohort_def"]
    base = S.chiron_count_cohort(DS, [])["subject_count"]
    filt = S.chiron_count_cohort(DS, cd)
    print("counts:", base, "->", filt)
    check("filtered count <= unfiltered", filt.get("subject_count", 99) <= base,
          f"{filt.get('subject_count')} vs {base}")
    check("filtered cohort is not whole-dataset", not filt.get("is_whole_dataset"), str(filt))

# export interlock
r = S.chiron_export_table(DS, [], [{"concept_id": "encounter_id"}], 0)
check("export refuses without acknowledged count", "error" in r, str(r)[:120])

print()
sys.exit(1 if fails else 0)
