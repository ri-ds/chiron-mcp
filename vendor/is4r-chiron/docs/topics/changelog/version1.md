# Version 1

## Version 1.3.0 (released 6/18/21)

1. There is a new model Project, and Reports can have a project associated with them. Projects
at this point are only used to help group reports.

2. Along with the new model Project is a new set of API endpoints.

   - see API Endpoints -> {ref}`api-endpoints-projects`

3. There is a new model ContentFlag that allows users to "star" reports that they are interested
in. There is a new API endpoint for flagging reports.

   - see API Endpoints -> {ref}`api-endpoints-reports-flag`

4. There is a small Django project with some dummy data for manual testing.




## Version 1.2.0 (released 4/29/21)

1. In table definition entries, "aggregation_style" and "aggregation_method" are now "aggregate"
(boolean) and "aggregation_method".

   - see Transforming Table Definitions -> {ref}`table-def-transformations-add-entry`

2. Two tranformation methods for adding and editing table def entries have been merged into one.

   - see Transforming Table Definitions -> {ref}`table-def-transformations-add-entry`

3. In the API concept detail view, "entry_id" query parameter was changed to "cohort_def_entry_id".

   - see API endpoint {ref}`api-concepts-detail-get`

4. Boolean cohort_def forms now works exactly like category cohort_def forms (except no exclude_selected option).

   - return categories are "True", "False", and null.

5. Cohort def statistics for dates, numbers: "histogram_data_string" was changed to "histogram_data"
and is now a JSON data structure instead of a JSON string.

6. A lot of method renaming and reorganizing of CohortDefProcessor and DisplayProcessor. If you have
any custom ones, you'll want to review the abstract methods and check everything.

   - see classes {ref}`cohort-def-processor-abstract` and {ref}`display-processor-abstract`


