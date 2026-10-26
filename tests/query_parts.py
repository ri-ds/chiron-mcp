"""chiron_query's pieces that need no database: words to values, limits, dates.

Offline: value matching runs on recorded values given here (the synthea spellings), so
it needs no Chiron database and no model. The whole tool is checked against the SQL
answer keys by chiron-benchmark's scripts/tool_check.py.

    .venv/bin/python tests/query_parts.py

Exit code 0 means every check held.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp import dictionary as D  # noqa: E402
from chiron_mcp import query as Q  # noqa: E402
from chiron_mcp.identity import AccessError  # noqa: E402

fails: list[str] = []


def check(name: str, ok: bool, detail="") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:220])
    if not ok:
        fails.append(name)


class Concept:
    def __init__(self, name):
        self.name = name


def var(short, kind="category", collection="condition"):
    return Q.Var(Concept(short), f"ds__{collection}__{short}", collection, short, kind)


def groups_of(counts: dict):
    # the same merge chiron_breakdown uses, reimplemented minimal: case + truncation
    from chiron_mcp import server as S
    return S._groups(counts, 10 ** 6)[0]


def match(v, counts, phrase):
    try:
        return Q._match_group(v, groups_of(counts), counts, phrase)
    except AccessError as exc:
        return str(exc)


CONDITIONS = {"Asthma": 8623, "ASTHMA": 8, "asthma": 10, "Asthm": 11,
              "Chronic obstructive pulmonary disease": 1782, "CHRONIC OBSTRUCTIVE PULMONARY DISEASE": 2,
              "Chronic obstructive pulmonary diseas": 1, "Essential hypertension": 21195,
              "Essential hypertensio": 24, "Type 2 diabetes mellitus": 6896, "Hypothyroidism": 4249,
              "Coronary arteriosclerosis": 2499, "Body mass index 30+ - obesity": 24051,
              "Major depressive disorder": 9714, "Major depressive disorde": 10, "Osteoarthritis": 6383}
LABS = {"Hemoglobin A1c/Hemoglobin.total in Blood": 44677, "Thyrotropin [Units/volume] in Serum or Plasma": 35888,
        "Cholesterol in HDL [Mass/volume]": 13031, "Cholesterol [Mass/volume] in Serum or Plasma": 12983,
        "Glucose [Mass/volume] in Blood": 44783, "Body mass index (BMI) [Ratio]": 3560282,
        "Systolic Blood Pressure": 3560282, "Diastolic Blood Pressure": 3560282, "Heart rate": 3560282,
        "Body Weight": 3560282, "Body Height": 3560282, "FEV1/FVC": 9065}
CLASSES = {"wellness": 1, "ambulatory": 1, "outpatient": 1, "urgentcare": 1, "emergency": 1}
PAYERS = {"medicare": 1, "bcbs": 1, "unitedhealth": 1, "medicaid": 1, "self-pay": 1, "aetna": 1}
MEDS = {"Metformin hydrochloride 500 MG Oral Tablet": 4529, "Insulin glargine 100 UNT/ML Injection": 4553,
        "Albuterol 0.09 MG/ACTUAT Inhaler": 7146, "Atorvastatin 20 MG Oral Tablet": 1635}

cond, lab = var("description"), var("description", collection="observation")
for phrase, want in (("asthma", "Asthma"), ("Asthma", "Asthma"), ("COPD", "Chronic obstructive pulmonary disease"),
                     ("hypertension", "Essential hypertension"), ("high blood pressure", "Essential hypertension"),
                     ("HTN", "Essential hypertension"), ("T2DM", "Type 2 diabetes mellitus"),
                     ("type 2 diabetes", "Type 2 diabetes mellitus"), ("underactive thyroid", "Hypothyroidism"),
                     ("MDD", "Major depressive disorder"), ("obesity", "Body mass index 30+ - obesity"),
                     ("CAD", "Coronary arteriosclerosis"), ("osteoarthritis", "Osteoarthritis")):
    g = match(cond, CONDITIONS, phrase)
    check(f"condition {phrase!r}", isinstance(g, dict) and g["label"] == want, str(g)[:120])
g = match(cond, CONDITIONS, "asthma")
check("asthma takes every spelling", isinstance(g, dict) and set(g["values"]) == {"Asthma", "ASTHMA", "asthma", "Asthm"},
      str(g))
g = match(cond, CONDITIONS, "major depressive disorder")
check("a cut-off spelling is included", isinstance(g, dict) and "Major depressive disorde" in g["values"], str(g))
check("an unknown condition is refused with the values", "Asthma" in str(match(cond, CONDITIONS, "gout")))

for phrase, want in (("HbA1c", "Hemoglobin A1c"), ("A1c", "Hemoglobin A1c"), ("TSH", "Thyrotropin"),
                     ("HDL", "Cholesterol in HDL"), ("total cholesterol", "Cholesterol [Mass/volume]"),
                     ("BMI", "Body mass index"), ("systolic blood pressure", "Systolic"), ("blood glucose", "Glucose"),
                     ("FEV1/FVC", "FEV1/FVC"), ("weight", "Body Weight")):
    g = match(lab, LABS, phrase)
    check(f"lab {phrase!r}", isinstance(g, dict) and g["label"].startswith(want), str(g)[:120])
check("'cholesterol' alone asks which", "several" in str(match(lab, LABS, "cholesterol")))
check("'blood pressure' alone asks which", "several" in str(match(lab, LABS, "blood pressure")))

ec, pay, med = var("encounterclass", collection="encounter"), var("payer", collection="encounter"), var("description", collection="medication")
for phrase, want in (("ER", "emergency"), ("emergency room", "emergency"), ("emergency", "emergency"),
                     ("urgent care", "urgentcare"), ("checkup", "wellness"), ("ambulatory", "ambulatory")):
    g = match(ec, CLASSES, phrase)
    check(f"visit {phrase!r}", isinstance(g, dict) and g["label"] == want, str(g))
for phrase, want in (("self-pay", "self-pay"), ("self pay", "self-pay"), ("Medicaid", "medicaid"),
                     ("blue cross", "bcbs")):
    g = match(pay, PAYERS, phrase)
    check(f"payer {phrase!r}", isinstance(g, dict) and g["label"] == want, str(g))
for phrase, want in (("metformin", "Metformin"), ("insulin glargine", "Insulin glargine"), ("insulin", "Insulin"),
                     ("atorvastatin", "Atorvastatin")):
    g = match(med, MEDS, phrase)
    check(f"medication {phrase!r}", isinstance(g, dict) and g["label"].startswith(want), str(g))

gender = var("gender", collection="subject")
g = match(gender, {"F": 49933, "M": 49842, "f": 59, "m": 53}, "women")
check("'women' is F and f", isinstance(g, dict) and set(g["values"]) == {"F", "f"}, str(g))
g = match(var("married", collection="subject"), {"W": 1, "M": 1, "S": 1, "D": 1}, "widowed")
check("'widowed' is W", isinstance(g, dict) and g["values"] == ["W"], str(g))
g = match(var("ethnicity", collection="subject"), {"hispanic": 1, "nonhispanic": 1}, "Latino")
check("'Latino' is hispanic", isinstance(g, dict) and g["values"] == ["hispanic"], str(g))

# limits: strict ones move by far less than a cent, inclusive ones not at all
f, _ = Q.number_fields(">", 4500)
check("over 4,500 keeps 4,500.01, drops 4,500", 4500 < f["cd_numeric_min"] < 4500.01, str(f))
f, _ = Q.number_fields(">=", 6.5)
check(">= 6.5 is inclusive", f == {"cd_numeric_min": 6.5}, str(f))
f, _ = Q.number_fields("<", 5.7)
check("below 5.7 keeps 5.69, drops 5.7", 5.69 < f["cd_numeric_max"] < 5.7, str(f))
f, _ = Q.number_fields("above", "4.5")
check("'above' as a word", 4.5 < f["cd_numeric_min"] < 4.51, str(f))
f, _ = Q.number_fields(None, between=[239, 200])
check("between is inclusive, any order", f == {"cd_numeric_min": 200, "cd_numeric_max": 239}, str(f))
f, _ = Q.number_fields(">", "$150,000")
check("$ and commas read", 150000 < f["cd_numeric_min"] < 150000.01, str(f))

dvar, yvar = var("deathdate", "date", "subject"), var("deathdate", "year", "subject")
for cond_, want in (({"year": 2020}, ("01/01/2020", "12/31/2020")),
                    ({"before": "1945-01-01"}, (None, "12/31/1944")),
                    ({"before": 1945}, (None, "12/31/1944")),
                    ({"after": 2010}, ("01/01/2011", None)),
                    ({"year_between": [2010, 2015]}, ("01/01/2010", "12/31/2015")),
                    ({"op": "<", "value": "1960-01-01"}, (None, "12/31/1959")),
                    ({"op": ">=", "value": "2018-01-01"}, ("01/01/2018", None)),
                    ({"has_value": True}, ("01/01/1800", None))):
    f, _ = Q.date_fields(dvar, cond_)
    check(f"date {cond_}", (f.get("cd_numeric_min"), f.get("cd_numeric_max")) == want and f["query_type"] == "date_range",
          str(f))
f, _ = Q.date_fields(yvar, {"year": 2020})
check("a year-only date takes years", (f.get("cd_numeric_min"), f.get("cd_numeric_max")) == ("2020", "2020"), str(f))

check("value_words rewrites inside a phrase", "chronic obstructive pulmonary disease patients" in D.value_words("copd patients"))

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)
