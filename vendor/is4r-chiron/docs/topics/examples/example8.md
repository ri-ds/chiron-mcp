(example8)=
# create a subcollection ID



EXAMPLE: We have a subcollection `procedures` that has doesn't have a unique ID for each record. 
We would like to create an artificial procedure ID that's deidentified, unique for
each procedure event, and doesn't change every time the ETL runs.

<hr>

The concept handler we will use for this is `GeneratedSubcollectionIdHandler`. We must provide it
with an input concept or set of concepts that uniquely identifies a procedure. Concepts can come from
both the procedure collection and the subject collection. In this example, we will assume that
the subject ID, the procedure name, and the procedure date are enough to uniquely identify a
procedure event.



1. Set up the data dictionary to load the sources that create concepts for our three input IDs
   (subject_id, procedure_name, procedure_date).
   
2. In the data dictionary, we're going to add a new source for iterating the procedure collection in the Chiron database:
   
```{eval-rst}
:name:
   give any name you want, ex. "chiron_procedure_collection"

:collection:
   select the procedure collection

:processor:
   SourceSelfSubdoc

:execution_order:
   must be run after all our input data (subject_id, procedure_name, procedure_date) is loaded
```


3. In the data dictionary, create a concept for our procedure ID
     
```{eval-rst}
:permanent_id:
   give any name you want, ex. "procedure_id"

:name:
   "procedure ID"

:source:
   select the source you created in step 2
   
:concept_handler:
   GeneratedSubcollectionIdHandler

:collection:
   select the collection the calculated field will go in, i.e. the procedure collection
   
:Concept handler args:
    Provide a comma separated list of procedure concepts (and optionally a comma separated list of 
    subject concepts) to use as inputs for generating the procedure ID
    (name="subcol_fields", value="proc_name_dycdfyckfp, proc_date_xrvwavsftu"); 
    (name="subject_fields", value="subject_id_xctwybwqxh")
   
:Concept-concept dependencies:
    include `proc_name_dycdfyckfp`, `proc_date_xrvwavsftu`, `subject_id_xctwybwqxh` (if Chiron knows this concept
    depends on these concepts, it will help protect you from doing something stupid like loading
    them in the wrong order)
   
```

The remaining fields can be filled in as you wish.
    
4. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.
