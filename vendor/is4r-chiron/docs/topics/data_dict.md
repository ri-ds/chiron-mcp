
(understanding-dd)=
# Data Dictionary Components

The Chiron data dictionary contains all the metadata about your research data. Chiron will use the data dictionary to build the research database and import the data automatically.

(dataset-def)=
**Datasets**

Datasets are a top-level way of separating unrelated data into separate buckets. Each dataset will have its own research database, and will not have any relationships to the other datasets. In the user interface, users access a single dataset at a time, and a user can have different permissions on different datasets.

For chiron instances with only 1 dataset, most of the dataset functionality will be hidden.

(collection-def)=
**Collections**

Collections in the data dictionary represent database tables. Tables may also have child lookup tables for fields that allow multivalue.

Every dataset will have one subject collection (specified in `Dataset.root_collection`) to store data that is 1:1 with the subject. Then you can have any number of subcollections for a dataset that are 1:many or many:many with the subject.

**Event Collections**

Any collection that has a date associated with each record can be turned into an event collection. Event collections allow for some useful longitudinal query features that are not available for standard collections. For systems that don't store exact dates due to privacy concerns, age in days can be used instead. Events with a single date for each record are **point events**, and ones with a start and end date for each record are **interval events**.

(concept-def)=
**Concepts**

Each collection can have any number of concepts. The subject collection could have concepts like birthdate and gender. A biospecimen collection could have concepts like collection date and sample amount.

**Multivalue Concepts**

If you have a group of concepts that are 1:many or many:many with a subject, you store those in a subcollection. However, sometimes you may just have a single concept where a subject can have multiple values. In this situation, you can flag the concept as multivalue instead of having to create an entire collection for a single concept. For example, if subjects in your system are allowed to have more than 1 race, you can flag your race concept as multivalue instead of creating a race collection.

Concepts in subcollections can also be multivalue. In this case, the term "multivalue" doesn't refer to the cardinality of the concept in relation to the subject, but in relation to the subcollection that it's in. For example, say you have subjects take weekly surveys, and on the survey there's a multiple choice field for all types of exercise they had that week. You could have a survey subcollection where each subject has multiple surveys, and then within that survey subcollection you could have an exercise_type concept flagged as multivalue, where each survey could indicate multiple types of exercise.

(source-def)=
**Sources**

A Source is a 2D table of data to load into Chiron. It can be any Python iterable that returns records that correspond to the collection it's being loaded into.

For example, a SubjectDemographics table in a database could be a Source for the Subject collection. A CSV file with one row per patient medication could be a Source for a Medication collection.

Chiron manages the ETL process from your Sources into the research database. There's built-in support for data coming from a database through the Django ORM or from CSV files. If you have data coming from other types of sources, you can write your own Source processor class to enable Chiron to consume it.

(category-def)=
**Categories**

Categories define a hierarchical structure for users to browse concepts. They have no effect on queries or how the data is stored in the research database.

