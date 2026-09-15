# Version 2

## Version 2.1.3 (released 12/13/21)

1. Updated to work with Pymongo v4

2. Some endpoints didn't allow you to pass a cohort_def/table_def, instead automatically using
the latest snapshot. Now all should work the same - you can either pass the definition or the
latest snapshot will be assumed.


## Version 2.1.0 (released 11/15/21)

1. Some minor changes to the database schema. Django migrations will need to be run.

2. Minor changes to cohort def:

   - All criteria sets in an extended cohort def now have a criteria_set_name that uniquely identifies the criteria set.
   - The criteria_set_name is either auto-generated or comes from the criteria set alias (also new)
   - The criteria set alias can be set using the new cohort def transformation option set_criteria_set_alias. This is an optional feature.
   - Criteria set with a date rule used to have an event_id with a unique name like "EVENT 1". That has been removed, use the criteria_set_name instead.

3. Major changes to table def:

   - most changes affect the table def options for the concept endpoint: /api/concepts/lab_event_name/?include_table_def_options=true
   - Some options for aggregation now have additional inputs for customization of that option.
   - During an add_entry transformation to the table def, can provide "entry_alias" to give user a way to create their own column headers.
   - For cohort def with multiple criteria sets for the same collection, typically data matching any of them will be included when calculating aggregation value. With new option "aggregation_criteria_set" can specify a specific criteria set to limit results.


## Version 2.0.0 (released 10/21/21)

1. Major overhaul of the query engine. Instead of generating the full report in MongoDB, pulls the
data it needs from MongoDB and does most of the report generation in Python.