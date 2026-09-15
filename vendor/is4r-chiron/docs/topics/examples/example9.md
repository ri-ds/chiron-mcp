(example9)=
# create current age field from birth/death dates



EXAMPLE: We have concepts for DOB and DOD in the Chiron subject collection. We want to use these to generate
a deidentified age concept.

<hr>

The concept handler we will use for this is `CurrentAgeFromDobHandler`. We must provide it
with an input date of birth and optionally a date of death. We will load the DOB and DOD as concepts first, and then
create a new source at the end that iterates the Chiron subject collection to generate our calculated fields.


1. Set up the data dictionary to load the sources that create concepts for our DOB and DOD.
   
2. In the data dictionary, we're going to add a new source for iterating the subject collection in the Chiron database:
   
```{eval-rst}
:name:
   give any name you want, ex. "chiron_subject_collection"

:collection:
   select the subject collection

:processor:
   SourceSelf

:execution_order:
   must be run after all our input data (DOB, DOD) is loaded
```


3. In the data dictionary, create a concept for our procedure ID
     
```{eval-rst}
:permanent_id:
   give any name you want, ex. "current_age"

:name:
   "subject age"

:source:
   select the source you created in step 2
   
:concept_handler:
   CurrentAgeFromDobHandler

:collection:
   select the collection the calculated field will go in, i.e. the subject collection
   
:Concept handler args:
   Give the concept permanent IDs for the input fields
   field_name = "dob_xrvwavsftu"
   death_date_field_name = "dod_xctwybwqxh"
   
:Concept-concept dependencies:
    include `dob_xrvwavsftu`, `dod_xctwybwqxh` (if Chiron knows this concept
    depends on these date concepts, it will help protect you from doing something stupid like loading
    them in the wrong order)
   
```

The remaining fields can be filled in as you wish.
    
4. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.
