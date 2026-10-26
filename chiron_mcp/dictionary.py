"""Plain words for Chiron's tables, variables and values (plan P3).

chiron_query resolves what a question says ("ER visits", "died", "A1c", "Synthea 300")
to Chiron's own tables, variables and recorded values with these lists. They describe
the DATA, never a particular question or its answer:

- TABLES: words for each kind of record (a Chiron collection).
- FIELDS: words for each variable, by collection and the variable's short name (the
  part of its concept id after "<collection>__"). A dataset without that variable
  simply never matches it.
- VALUE_WORDS: clinical abbreviations and lay terms, rewritten to words that appear in
  recorded values ("COPD" -> "chronic obstructive pulmonary disease").
- CODES: coded values (gender "F", marital "W") and the words that mean them.

Everything here is matched after normalising case, spacing and punctuation. A variable
or value not listed is still found by its own name in Chiron; these lists only add the
words people use for it.
"""

from __future__ import annotations

import re

TABLES = {
    "subject": ("patient", "patients", "person", "people", "demographic", "demographics", "subject"),
    "condition": ("condition", "conditions", "diagnosis", "diagnoses", "diagnosed", "disease",
                  "diseases", "problem", "problems", "dx"),
    "medication": ("medication", "medications", "medicine", "medicines", "drug", "drugs",
                   "prescription", "prescriptions", "prescribed", "med", "meds", "rx"),
    "procedure": ("procedure", "procedures"),
    "encounter": ("encounter", "encounters", "visit", "visits", "admission", "admissions"),
    "observation": ("observation", "observations", "lab", "labs", "lab test", "lab tests", "test",
                    "tests", "result", "results", "measurement", "measurements", "vital",
                    "vitals", "vital sign", "vital signs", "reading", "readings"),
}

# The variable each kind of record is named by: "condition: asthma" filters on this one.
NAME_FIELD = {"condition": "description", "medication": "description", "procedure": "description",
              "observation": "description", "encounter": "encounterclass"}
# The variable holding a record's own date: "diagnosed in 2018", "started before 2010".
DATE_FIELD = {"condition": "start", "medication": "start", "procedure": "start",
              "observation": "date", "encounter": "start"}
# The variable holding a lab or vital's number.
VALUE_FIELD = {"observation": "value"}

FIELDS = {
    "subject": {
        "gender": ("gender", "sex"),
        "birthdate": ("birthdate", "birth date", "date of birth", "dob", "born", "birth"),
        "deathdate": ("deathdate", "death date", "date of death", "died", "death", "deceased",
                      "dead", "deaths"),
        "married": ("married", "marital status", "marital", "marriage status"),
        "income": ("income", "annual income", "earn", "earns", "earning", "earnings", "salary"),
        "healthcare_expenses": ("healthcare expenses", "total healthcare expenses", "health care expenses",
                                "expenses", "healthcare spending", "lifetime healthcare expenses"),
        "healthcare_coverage": ("healthcare coverage", "health care coverage", "coverage",
                                "insurance coverage"),
        "race": ("race", "racial"),
        "ethnicity": ("ethnicity", "ethnic"),
        "county": ("county", "counties"),
        "city": ("city", "cities", "town"),
        "zip": ("zip", "zip code", "postcode", "postal code"),
        "state": ("state",),
        "study_group_a": ("study group a", "group a", "arm a"),
        "study_group_b": ("study group b", "group b", "arm b"),
        "study_group_c": ("study group c", "group c", "arm c"),
        "id": ("patient id", "id", "subject id", "patient identifier"),
    },
    "encounter": {
        "encounterclass": ("visit type", "encounter class", "class", "type of visit", "setting",
                           "encounter type", "kind of visit"),
        "description": ("visit description", "encounter description", "visit reason"),
        "total_claim_cost": ("cost", "visit cost", "claim cost", "total claim cost", "total cost",
                             "cost of the visit", "charge", "price", "costing", "costs", "billed"),
        "base_encounter_cost": ("base cost", "base encounter cost", "base visit cost"),
        "payer": ("payer", "insurer", "insurance", "billed to", "paid by", "health plan", "insurance company"),
        "payer_coverage": ("payer coverage", "amount covered", "insurance paid", "covered amount"),
        "start": ("visit date", "date", "when", "start", "started", "on"),
        "stop": ("stop", "end", "ended", "discharge"),
        "organization": ("organization", "hospital", "clinic", "facility"),
        "provider": ("provider", "doctor", "clinician"),
        "code": ("code",),
    },
    "condition": {
        "description": ("condition", "diagnosis", "disease", "name"),
        "start": ("diagnosis date", "onset", "date", "when", "start", "started", "diagnosed"),
        "stop": ("resolved", "end", "stop", "ended"),
        "code": ("code", "snomed"),
    },
    "medication": {
        "description": ("medication", "drug", "name", "medicine"),
        "reasondescription": ("reason", "prescribed for", "indication", "why",
                              "reason description", "prescription reason"),
        "start": ("start", "started", "date", "when", "prescribed on", "began"),
        "stop": ("stop", "stopped", "end", "ended"),
        "dispenses": ("dispenses", "fills", "refills", "dispensed"),
        "totalcost": ("total cost", "cost", "price"),
        "base_cost": ("base cost",),
        "code": ("code", "rxnorm"),
    },
    "procedure": {
        "description": ("procedure", "name"),
        "start": ("date", "when", "performed", "start", "done"),
        "base_cost": ("cost", "base cost", "price"),
        "code": ("code", "snomed"),
    },
    "observation": {
        "description": ("lab", "test", "vital", "measurement", "name", "observation"),
        "value": ("value", "result", "reading", "level", "measurement value"),
        "units": ("units", "unit"),
        "date": ("date", "when", "measured", "taken"),
        "category": ("category", "kind"),
        "code": ("code", "loinc"),
    },
}

# Rewritten to words that occur in recorded values. Keys and values are normalised text.
VALUE_WORDS = {
    # conditions
    "copd": "chronic obstructive pulmonary disease",
    "chronic obstructive lung disease": "chronic obstructive pulmonary disease",
    "emphysema": "chronic obstructive pulmonary disease",
    "htn": "hypertension",
    "high blood pressure": "hypertension",
    "hypertensive": "hypertension",
    "t2d": "type 2 diabetes",
    "t2dm": "type 2 diabetes",
    "dm2": "type 2 diabetes",
    "type ii diabetes": "type 2 diabetes",
    "diabetes type 2": "type 2 diabetes",
    "diabetes mellitus type 2": "type 2 diabetes",
    "type 2 diabetic": "type 2 diabetes",
    "mdd": "major depressive disorder",
    "major depression": "major depressive disorder",
    "clinical depression": "major depressive disorder",
    "cad": "coronary arteriosclerosis",
    "coronary artery disease": "coronary arteriosclerosis",
    "atherosclerosis": "coronary arteriosclerosis",
    "oa": "osteoarthritis",
    "underactive thyroid": "hypothyroidism",
    "low thyroid": "hypothyroidism",
    "obese": "obesity",
    # labs and vitals
    "a1c": "hemoglobin a1c",
    "hba1c": "hemoglobin a1c",
    "hb a1c": "hemoglobin a1c",
    "hgba1c": "hemoglobin a1c",
    "glycated hemoglobin": "hemoglobin a1c",
    "glycosylated hemoglobin": "hemoglobin a1c",
    "haemoglobin a1c": "hemoglobin a1c",
    "tsh": "thyrotropin",
    "thyroid stimulating hormone": "thyrotropin",
    "bmi": "body mass index",
    "sbp": "systolic blood pressure",
    "systolic": "systolic blood pressure",
    "systolic bp": "systolic blood pressure",
    "dbp": "diastolic blood pressure",
    "diastolic": "diastolic blood pressure",
    "diastolic bp": "diastolic blood pressure",
    "pulse": "heart rate",
    "hr": "heart rate",
    "weight": "body weight",
    "height": "body height",
    "hdl": "cholesterol in hdl",
    "hdl cholesterol": "cholesterol in hdl",
    "good cholesterol": "cholesterol in hdl",
    "total cholesterol": "cholesterol mass volume in serum or plasma",
    "cholesterol total": "cholesterol mass volume in serum or plasma",
    "serum cholesterol": "cholesterol mass volume in serum or plasma",
    "blood sugar": "glucose",
    "blood glucose": "glucose",
    "fev1 fvc": "fev1 fvc",
    "fev1 fvc ratio": "fev1 fvc",
    "lung function": "fev1 fvc",
    # visits
    "er": "emergency",
    "ed": "emergency",
    "emergency room": "emergency",
    "emergency department": "emergency",
    "emergency room admission": "emergency",
    "emergency visit": "emergency",
    "emergency admission": "emergency",
    "urgent care": "urgentcare",
    "urgent care visit": "urgentcare",
    "check up": "wellness",
    "checkup": "wellness",
    "annual physical": "wellness",
    "wellness visit": "wellness",
    "outpatient visit": "outpatient",
    "ambulatory visit": "ambulatory",
    # payers
    "self pay": "self pay",
    "selfpay": "self pay",
    "uninsured": "self pay",
    "out of pocket": "self pay",
    "blue cross": "bcbs",
    "blue cross blue shield": "bcbs",
    "united healthcare": "unitedhealth",
    "unitedhealthcare": "unitedhealth",
    # procedures
    "chest x ray": "plain chest x ray",
    "chest xray": "plain chest x ray",
    "cxr": "plain chest x ray",
    "throat swab": "throat culture",
    "strep test": "throat culture",
    "depression screen": "depression screening",
    "phq": "depression screening",
}

# Coded values: variable short name -> {recorded code (normalised): words that mean it}.
CODES = {
    "gender": {"f": ("female", "females", "woman", "women", "girl", "girls", "f"),
               "m": ("male", "males", "man", "men", "boy", "boys", "m")},
    "married": {"m": ("married", "m"), "d": ("divorced", "d"),
                "w": ("widowed", "widow", "widows", "widower", "widowers", "w"),
                "s": ("single", "never married", "unmarried", "s")},
    "ethnicity": {"hispanic": ("hispanic", "latino", "latina", "latinx", "hispanic or latino"),
                  "nonhispanic": ("non hispanic", "nonhispanic", "not hispanic", "non latino")},
    "race": {"white": ("white", "caucasian"), "black": ("black", "african american", "black or african american"),
             "asian": ("asian",), "native": ("native", "native american", "american indian", "alaska native"),
             "other": ("other",)},
}

# Datasets: extra words for a dataset id beyond its id and display name.
DATASET_WORDS = {
    "synthea-small": ("synthea 300", "300", "small", "synthea small"),
    "synthea-100k": ("synthea 100k", "100k", "100,000", "100000", "synthea 100 000"),
    "synthea-10k": ("synthea 10k", "10k", "10,000"),
}


def norm(text) -> str:
    """Lower case, punctuation as spaces, single spaces: "Body mass index (BMI) [Ratio]"
    -> "body mass index bmi ratio"."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+]+", " ", str(text or "").lower())).strip()


def value_words(phrase: str) -> list[str]:
    """The phrase and what it is rewritten to, normalised, most specific first."""
    p = norm(phrase)
    out = [p]
    if p in VALUE_WORDS:
        out.append(norm(VALUE_WORDS[p]))
    # also rewrite a known abbreviation inside a longer phrase ("copd patients")
    for k, v in VALUE_WORDS.items():
        if k != p and re.search(rf"\b{re.escape(k)}\b", p):
            out.append(norm(re.sub(rf"\b{re.escape(k)}\b", v, p)))
    return list(dict.fromkeys(x for x in out if x))
