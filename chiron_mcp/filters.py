"""The cohort filter input schema, which Chiron does not expose anywhere.

Chiron has no machine-readable schema for cohort filter inputs.  A filter is
submitted as HTML *form field names* -- `cd_numeric_min`, `selected_categories`,
`chiron_text_field_selection` -- and the only source of truth is each processor's
`validate_form()` body in chiron/processors/cohort_def/.

Those bodies were read directly and transcribed here so the model can be told what
a given concept actually accepts.  Each entry maps a CohortDefProcessor class name
to its documented fields.

Line references are to chiron/processors/cohort_def/<module>.py.
"""

from __future__ import annotations

# Fields every numeric/date-ish processor shares.
_EXCLUDE = (
    "exclude_selected",
    "bool, optional (default false) -- invert the filter, excluding the selected values",
)
_NULLS = (
    "include_null_and_missing",
    "bool, optional (default false) -- also match subjects with no value",
)

FILTER_SCHEMAS: dict[str, dict] = {
    "CohortDefCategory": {
        "summary": "Pick one or more discrete values.",
        "fields": [
            (
                "selected_categories",
                "list[str], REQUIRED -- values to match. An empty string in the list means "
                "the null/missing category. Rejected with 'Please select at least one value.' "
                "if empty.",
            ),
            _EXCLUDE,
        ],
        "source": "category.py validate_form",
    },
    "CohortDefBoolean": {
        "summary": "Pick true/false/unknown values.",
        "fields": [
            ("selected_categories", "list[str], REQUIRED -- the boolean categories to match"),
        ],
        "source": "boolean.py validate_form",
    },
    "CohortDefNumber": {
        "summary": "Numeric range filter.",
        "fields": [
            ("cd_numeric_min", "number, optional -- lower bound (inclusive)"),
            ("cd_numeric_max", "number, optional -- upper bound (inclusive)"),
            _EXCLUDE,
            _NULLS,
        ],
        "source": "number.py validate_form",
    },
    "CohortDefNumberWithCategories": {
        "summary": "Numeric range filter that also carries discrete categories.",
        "fields": [
            ("cd_numeric_min", "number, optional -- lower bound (inclusive)"),
            ("cd_numeric_max", "number, optional -- upper bound (inclusive)"),
            ("selected_categories", "list[str], optional -- discrete values to include as well"),
            _EXCLUDE,
            _NULLS,
        ],
        "source": "number_with_categories.py validate_form",
    },
    "CohortDefDate": {
        "summary": "Date filter. `query_type` selects absolute range vs relative age.",
        "fields": [
            ("query_type", "str, REQUIRED -- which date mode to use; see form options"),
            ("cd_numeric_min", "date/number, optional -- lower bound"),
            ("cd_numeric_max", "date/number, optional -- upper bound"),
            ("days_ago", "number, optional -- relative-date bound"),
            _EXCLUDE,
            _NULLS,
        ],
        "source": "date.py validate_form",
    },
    "CohortDefDateDeid": {
        "summary": "De-identified date filter (same shape as CohortDefDate).",
        "fields": [
            ("query_type", "str, REQUIRED -- which date mode to use"),
            ("cd_numeric_min", "number, optional -- lower bound"),
            ("cd_numeric_max", "number, optional -- upper bound"),
            ("days_ago", "number, optional -- relative-date bound"),
            _EXCLUDE,
            _NULLS,
        ],
        "source": "date_deid.py validate_form",
    },
    "CohortDefDetailedAge": {
        "summary": "Age filter expressed as years plus days.",
        "fields": [
            ("cd_age_min_year", "int, optional -- minimum age, years part"),
            ("cd_age_min_day", "int, optional -- minimum age, days part"),
            ("cd_age_max_year", "int, optional -- maximum age, years part"),
            ("cd_age_max_day", "int, optional -- maximum age, days part"),
            _EXCLUDE,
            _NULLS,
        ],
        "source": "detailed_age.py validate_form",
    },
    "CohortDefText": {
        "summary": "Free-text term match.",
        "fields": [
            (
                "chiron_text_field_selection",
                "str, REQUIRED -- one term per line (newline separated). A term wrapped in "
                "slashes, /like this/, is treated as a regex. KNOWN ISSUE: the maintainers' "
                "own tests document regex text filters as not working correctly.",
            ),
            (
                "ignore_warnings",
                "bool, optional -- terms not present in the data raise the warning "
                "'Entry X not found' and the filter is REJECTED. Set this true to accept "
                "the filter anyway. Required for any term that is a typo, a regex, or a "
                "value absent from this dataset.",
            ),
            _EXCLUDE,
            _NULLS,
        ],
        "source": "text.py validate_form",
    },
    "CohortDefOntology": {
        "summary": "Ontology term match; selecting a parent term matches all descendants.",
        "fields": [
            ("chiron_ontology_field_selection", "str, REQUIRED -- one ontology term per line"),
            ("include_ontology_unknown", "bool, optional -- also match unmapped values"),
            (
                "ignore_warnings",
                "bool, optional -- accept terms that produced warnings (see CohortDefText)",
            ),
            _EXCLUDE,
            _NULLS,
        ],
        "source": "ontology.py validate_form",
    },
}

# CohortDefTextCustomSort inherits the text form.
FILTER_SCHEMAS["CohortDefTextCustomSort"] = dict(
    FILTER_SCHEMAS["CohortDefText"], source="text_custom_sort.py (inherits text.py)"
)


def describe(processor) -> dict:
    """Return the input-field schema for a concept's resolved processor."""
    name = type(processor).__name__
    schema = FILTER_SCHEMAS.get(name)
    if not schema:
        return {
            "processor": name,
            "summary": (
                "No transcribed schema for this processor. Inspect its validate_form() in "
                "chiron/processors/cohort_def/ before filtering on this concept."
            ),
            "fields": [],
        }
    return {
        "processor": name,
        "summary": schema["summary"],
        "fields": [{"name": n, "spec": s} for n, s in schema["fields"]],
        "source": f"chiron/processors/cohort_def/{schema['source']}",
    }
