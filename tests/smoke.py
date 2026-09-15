"""End-to-end smoke test against the live Chiron instance."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from chiron_mcp import server as S

def show(label, obj, n=700):
    txt = json.dumps(obj, default=str)
    print(f"\n--- {label}\n{txt[:n]}")

DS = os.environ.get("CHIRON_MCP_TEST_DATASET") or next(
    (d["dataset_id"] for d in S.chiron_datasets()["datasets"] if d.get("accessible")),
    None,
)
if not DS:
    sys.exit("No dataset reachable by this identity.")
show("datasets", S.chiron_datasets())
c = S.chiron_find_concepts(DS, limit=6)
show("find_concepts", c)

cid = c["concepts"][0]["concept_id"] if c.get("concepts") else None
print(f"\n>>> using concept {cid}")
d = S.chiron_describe_concept(DS, cid, include_statistics=False)
show("describe_concept.filter_input", d.get("filter_input"))

show("concept_values", S.chiron_concept_values(DS, cid, limit=5))
show("count empty cohort", S.chiron_count_cohort(DS, []))
show("run_table", S.chiron_run_table(DS, [], [{"concept_id": cid}]), 500)
show("saved_reports", S.chiron_saved_reports(DS), 400)
show("operator gate (should refuse)", S.chiron_schema_diagram(DS), 300)
