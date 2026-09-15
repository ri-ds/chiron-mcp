(example6)=
# subject ID when your source data doesn't have one



EXAMPLE: We have a source `demographics` that loads demographic info, but there's not really any
subject ID in our source data. We would like to create an artificial subject ID that's unique for
each subject.

<hr>

Since we don't have a single concept that's unique for each subject, we need to come up with a combination of
non-unique concepts that will be unique when used together. For example, you might be able to use
`first_name`, `last_name`, and `birthdate`.

The combination of concept will be used to generate a deidentified ID. We want the ID to be stable over time, 
so we should choose concepts that aren't likely to change. For example, you wouldn't want to include
an age field that will be different every year.

The concept handler we will use for this is `AutoSubjectIdHandler`.  Note that this handler
currently only works with arrays of dicts, not querysets, so it can't be used directly with a 
Django source. Instead, we will load the demographic data into our Chiron subject collection first, and then
iterate the Chiron subject collection itself as a source to generate our deidentified ID.

1. Set up the data dictionary to load the source `demographics`.
   
2. In the data dictionary, we're going to add a new source for iterating the subject collection in the Chiron database:
   
```{eval-rst}
:name:
   give any name you want, ex. "chiron_subject_collection"

:collection:
   select the subject collection for this dataset

:processor:
   SourceSelf

:execution_order:
   must be run after source `demographics` so that the input fields are already loaded
```


3. In the data dictionary, create a concept for our deidentified subject ID
     
```{eval-rst}
:permanent_id:
   give any name you want, ex. "deid_subject_id"

:name:
   "subject ID"

:source:
   select the source you created in step 2
   
:concept_handler:
   AutoSubjectIdHandler

:collection:
   select the collection the calculated field will go in, i.e. the subject collection
   
:Concept handler args:
    You need to specify the permanent ID for the concepts you will use as a comma-separated list\
    (name="input_fields", value="first_name_qyxtzoxyzq, last_name_ztkmkdnnme, dob_ppgfnxwyfv").
   
:Concept-concept dependencies:
    include `first_name_qyxtzoxyzq`, `last_name_ztkmkdnnme`, `dob_ppgfnxwyfv` (if Chiron knows this concept
    depends on the MRN concept, it will help protect you from doing something stupid like loading
    them in the wrong order)
   
```

The remaining fields can be filled in as you wish.
    
4. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.
