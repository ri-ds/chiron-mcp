# Version 3
   
## Version 3.1.0 (released 4/1/22)

1. New `CollectionRelationship` table in the data dictionary allows you to define 1:many and many:many relationships between subcollections.
   - See {ref}`data-model-explainer` for explanation of subcollection relationships and see the new data dictionary model {ref}`collection-relationship-model`.
2. The collections API flags collections with dates defined using new "has_event" property. 
3. New API endpoint to get the Chiron version number.

## Version 3.0.0 (released 2/11/22)

1. Added Analysis view 
   - This is a new tool that allows for the generation of pivot-table style datasets.
   - The new API endpoint group `analysis_def` work similarly to `table_def` and are used to define an analysis dataset.
   - The new API endpoints `analysis_tools` work similarly to `query_tools` and are used to actually run the queries.
   - The analysis view can be turned on/off in settings.

2. Added new aggregated permission level
   - The ChironUser model was modified for this. 
   - We already had 2 access levels, 1 for full PHI and 1 for deidentified data. This release adds a third access level for aggregated data.
   - Users with this access level will not have access to anything that would give them subject-level data.

3. Added caching for performance improvement
   - Caching can be turned on/off in settings. 
   - It is recommended to keep it off in development environments and on in production environments.