# 3. Manually Edit the Data Dictionary

Here are some more things you might want to do after autocreating your dataset.

<hr>

## Define Concept Relationships

By default, every subcollection you create in your dataset will have a many:1 or many:many relationship to
the subject collection.

But there can also be relationships between subcollections. For example, you might have a `visit`
collection and a `procedure` collection where every procedure is associated with one visit. Use the
`ConceptRelationship` model to define these relationships. They must be set manually, they do not get autocreated.

See {ref}`Plan your Data Schema sections 6 & 7<data-schema-6>` for how to determine subcollection relationships.

<hr>

## Special ID Concept

Because of the way stacking/aggregation works in reports, it's usually good to have unique IDs for 
your various collections. For example, if a user wants to guarantee one row per procedure event, 
the easiest way to do this is by stacking results on a procedure event ID.

You might not have appropriate IDs available in your source data, or you might not have IDs 
you want to expose because of PHI restrictions. You might be tempted to create a random ID, 
but this would change every time the data is refreshed and cause problems with saved queries. 
Instead, use one of Chiron's specialized processors for generating auto IDs. These can be set up so 
that they don't change when the ETL is rerun.

<hr>

### Subject IDs

**SITUATION: I have a PHI subject ID field in my source data, but I want users to see a deidentified ID.**

Using {ref}`AutoSubjectIdHandler<auto-subject-id-handler>`, you can provide your private subject ID as input and it will generate a
new deidentified subject ID.

*EXAMPLE:* {ref}`example5`

**SITUATION: I don't have a unique subject ID but I want one.**

Again you can use . But since you don't have an ID to use as input, you
need to provide a group of fields that together uniquely identify a subject (name, demographic details, etc.).

*EXAMPLE:* {ref}`example6`

**SITUATION: I used a subject ID field for subject matching and now want to expose it to users as a concept.**

ID fields used for subject matching between different sources are stored in your subject collection (in `_ids`)
but don't get exposed to users. One advantage of these fields is that they can be populated
from multiple sources - something that isn't possible with concepts. 

You can expose these IDs to users by copying the data into a regular Chiron concept using the 
{ref}`SubjectMatchingToTextHandler<subject-matching-to-text-handler>`.

*EXAMPLE:* {ref}`example7`

### Subcollection IDs

**SITUATION: I want to create a unique, deidentified ID for every record in my subcollection.**

Using {ref}`AutoSubcollectionIdHandler<auto-subcollection-id-handler>`, you can generate a deidentified subcollection ID using
other concepts(s) as input.

*EXAMPLE:* {ref}`example8`

<hr>

(custom_age_date_concepts)=
## Custom Age/Date Concepts

For identifying when events happened, Chiron works down to the level of 1 day (times are not currently supported).
There are three types of input data you might have coming from your sources:

- **absolute date(s)** - includes DOB, DOD or start/end date of an event
- **age in years as float** - age at event in years as a float value (decimal indicates fraction of a year)
- **age in days as integer** - age at event as number of days old

And then Chiron has three types of date/age concepts available:

- **date**
    - use when you want to show absolute dates when things happen
	- applying PHI restrictions will round all dates to years in the UI
- **detailed age**
    - internally stores age as days old
    - gives a high level of detail without exposing dates, which are often PHI
- **current age**
    - always stores/shows a deidentified value
    - gives the patient's current age in years, or "90 and above"
     
Use this table to lookup your situation, based on what type of input data you have and what type of concept you want to create:

|Input format|Desired Chiron format|Approach|
|---|---|---|
|absolute date(s)|date|use {ref}`date-handler`|
|absolute date(s)|current age|{ref}`example9`|
|absolute date(s)|detailed age|{ref}`example10`|
|age in years as float|date|(not supported)|
|age in years as float|current age|use {ref}`current-age-handler`|
|age in years as float|detailed age|use {ref}`detailed-age-handler` with source_format="year float"|
|age in days as integer|date|(not supported)|
|age in days as integer|current age|(not supported)|
|age in days as integer|detailed age|use {ref}`detailed-age-handler`|

<hr>

(how-to-event-collections)=
## Turning Collections into Events

Event collections allow users to perform special types of temporal queries. For an explanation of
event collections, see {ref}`understanding-event-collections`.

### Choose Dates or Ages

Your entire chiron instance can either use absolute dates or detailed ages to define events.
Set this in your chiron setting {ref}`CHIRON_EVENT_CONCEPT_TYPE<chiron-settings-dd>`.

### Select Appropriate Event Concept(s)

The {ref}`Collection model<collection-model>` has fields `event_date_field` and `event_end_date_field`. For a point event, specify
the date or age concept in `event_date_field`. For an interval event, also specify `event_end_date_field`.
Note that the concept data type (date or detailed age) must match with what you specified in 
`chiron_settings.CHIRON_EVENT_CONCEPT_TYPE`.

If you want to turn a collection into an event collection but don't have an appropriate concept in place, 
see {ref}`custom_age_date_concepts` for tips on how to create these type of concepts.

### Check That It's Working

In the UI in a query definition, criteria sets defined on event collections will show a date option
indicated with a calendar button (you may need to scroll over the criteria set for buttons to appear).
This button will open up a menu for defining a temporal query.

