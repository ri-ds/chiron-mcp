(example7)=
# subject ID concept from Chiron subject ID field



EXAMPLE: We are loading from multiple sources that all match subjects on a Study ID. After all the
data is loaded into Chiron, we want to make this Study ID available as a concept in the interface.

<hr>

The Chiron subject collection has a special `_ids` section that is used to store one or more
subject IDs for each subject document. In an autocreate source entry, these IDs are defined
using `subject_id_field` (simple scenario) or `subject_matching` (more complex scenarios).

The IDs are only used internally during the ETL for matching new records to existing subjects. But
sometimes you might want make one of these IDs available in the interface. To do this, we can
iterate the Chiron subject collection at the end of the ETL and copy the subject ID field to a
concept.

1. You data dictionary should already be set up to load your sources, matching patients on
   the study ID field. In the simplest case, this will be in the Chiron subject collection as
   `_ids.id`.
   
2. In the data dictionary, we're going to add a new source for iterating the subject collection in the Chiron database:
   
```{eval-rst}
:name:
   give any name you want, ex. "chiron_subject_collection"

:collection:
   select the subject collection for this dataset

:processor:
   SourceSelf

:execution_order:
   should be run after other sources, since we need to be sure that all the `_ids.id` field
   values have already been loaded.
```


3. In the data dictionary, create a concept for our study ID
     
```{eval-rst}
:permanent_id:
   give any name you want, ex. "study_id"

:name:
   "study ID"

:source:
   select the source you created in step 2
   
:concept_handler:
   SubjectMatchingToTextHandler

:collection:
   select the collection the calculated field will go in, i.e. the subject collection
   
:Concept handler args:
    Provide the name of the subject field in `_ids` that you want to use
    (name="subject_id_name", value="id").
   
:Concept-source dependencies:
    Select any sources that create new subjects with study_id values (if Chiron knows this concept
    depends on these sources, it will help protect you from doing something stupid like loading
    them in the wrong order)
   
```

The remaining fields can be filled in as you wish.
    
4. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.
