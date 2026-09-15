(example5)=
# deidentified subject ID from PHI subject ID



EXAMPLE: We have a single source `patients` loading concept `MRN` that we don't want to expose to some of our users. We would
like to create a deidentified subject ID as an alternative.

<hr>

We will use an asymmetric encryption algorithm using the MRN as input to generate our deidentified ID.

The concept handler we will use for this is `AutoSubjectIdHandler`.  Note that this handler
currently only works with arrays of dicts, not querysets, so it can't be used directly with a 
Django source. Instead, we will load the MRN into our Chiron subject collection first, and then
iterate the Chiron subject collection itself as a source to generate our deidentified ID.

1. Set up the data dictionary to load the source `patients`.
   
2. In the data dictionary, we're going to add a new source for iterating the subject collection in the Chiron database:
   
```{eval-rst}
:name:
   give any name you want, ex. "chiron_subject_collection"

:collection:
   select the subject collection for this dataset

:processor:
   SourceSelf

:execution_order:
   must be run after source `patients` so that the input fields are already loaded
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
    You need to specify the permanent ID for the MRN concept (name="input_fields", value="mrn_qyxtzoxyzq").
   
:Concept-concept dependencies:
    include `mrn_qyxtzoxyzq` (if Chiron knows this concept
    depends on the MRN concept, it will help protect you from doing something stupid like loading
    them in the wrong order)
   
```

The remaining fields can be filled in as you wish.
    
4. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.
