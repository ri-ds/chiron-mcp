
# 1. Plan your Data Schema

{ref}`Collections<collection-def>` will be set up based on the actual cardinality of your data. There are objectively wrong ways to do it, and setting it up wrong will lead to unintuitive or incorrect results when your users start to run queries.

Don't try to use Collections to customize how Concepts are grouped in the UI. If you need your data organized a specific way in your UI, that's what {ref}`Categories<category-def>` are for. Unlike Collections, Categories can be organized any way you like with zero effect on how the data is stored or queried.


**1. Any data that's 1:1 with subject should go in the subject collection.**
   
It doesn't matter if the data is coming from different sources or related to different domains. The subject collection can be as wide as you need it to be.

**2. If you have _single concepts_ that are many:1 with the subject, they can still go into the subject collection.**
   
For example, "race" might be allowed to have multiple values. You can incorporate "race" directly into the subject collection and people with multiple races will have an array of values stored.<br><br>If "race" from your source data is repetitive, the data will be simplified to a set of distinct, non-null values before being stored. For example, if someone has source race values of `["white", "white", "white", null, "asian"]`, that would be stored in Chiron as `["white", "asian"]`.

**3. If you have _2 or more concept_ that are many:1 with the subject as a cohesive group, they must go into a subcollection.**

For example, `procedure name` and `procedure date` would need their own collection.

You cannot just put them into the subject collection as arrays like we did in step 2, because the relationship between each name and date would be lost. For example, if a person had 5 different procedures with 5 different dates, this would show up in the output as a cartesian product of 25 values because Chiron will store two arrays (one for the names and one for the dates) that it doesn't understand how to pair up.

**4. you will have one subcollection for each cohesive group of values that are many:1 with subjects.**

For example, if subjects can have 0:many encounters, then any concepts 1:1 with encounter will go into an `encounter` subcollection. If encounters in turn can have 0:many associated procedures, you will want a separate `procedure` subcollection to store any concepts that are 1:1 with procedures.

A good question to ask is "What does a single document in my subcollection represent?" If you can't answer this, there's a good chance your subcollection isn't defined correctly.

Just like with the subject collection, the one exception to this rule is _single concepts_ that are many:1 with the subcollection. For example, if an encounter has a `reason_for_visit` concept that can list any number of reasons, that single concept can be included in the `encounter` collection as an array rather than making a whole new subcollection for it.

**5. Chiron also allows subcollections that are many:many with the subject.**

For example, you might have a `primary_care_provider` subcollection with one document per provider. Rather than a provider being associated with a single subject, each provider could be associated with any number of subjects.

Nothing special needs to be done to set this up. If the {ref}`get_subject_match_def() method<ref-standard-load-mixin>` on your {ref}`source processor<processor-def>` returns multiple subject IDs, then a many:many relationship with subjects will automatically be set up.

(data-schema-6)=
## Relationships Between Subcollections 

6. Once you have all your collections configured, the last step is to set up any relationships between subcollections.**

For example, if procedures are always associated with encounters, it's good to define that relationship. Using the
{ref}`collection-relationship-model`, you would define the primary key as the `encounter_id` concept in the `encounter` collection, and the foreign key as the `encounter_id` concept in the `procedure` collection.

Chiron will not break if these relationships are not defined, but they help avoid cartesian products in results (because they tell Chiron how data from different subcollections can be paired together). So subcollection relationships should be used whenever they are appropriate.

(data-schema-7)=
7. In a more rare situation, you might have a many:many relationship between subcollections.**

For example biospecimen might be associated with multiple studies, and each study can have any number of biospecimen. In this case, your primary key will be set up the same, but your foreign key field will need to be stored as an array of values. Your primary key could be the `biospecimen_id` in the `biospecimen` collection. And your foreign key could be `biospecimen_ids` in the `study` collection, which can contain an array when a study is associated with mulitple biospecimen.

Also note that for many:many, it doesn't matter which side the primary/foreign key goes on. We could just as easily achieve the same results with the primary key as the `study_id` in the `study` collection, and the foreign key as `study_ids` array concept in the `biospecimen` collection.