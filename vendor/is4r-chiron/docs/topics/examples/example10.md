(example10)=
# create detailed age field from birth date and event date



EXAMPLE: We have a visit subcollection and we want to calculate the detailed age at visit using
the visit date and the DOB for the associated subject.

<hr>

The concept handler we will use for this is `DetailedAgeFromDatesHandler`. We will create a new 
source at the end that iterates the visit subcollection to generate our calculated field.The handler requires
the DOB to come from the subject collection and the event date to come from the subcollection.



1. Set up the data dictionary to load the sources that create concepts for our DOB and visit event date.
   
2. In the data dictionary, we're going to add a new source for iterating the vist subcollection in the Chiron database:
   
```{eval-rst}
:name:
   give any name you want, ex. "chiron_visit_subcollection"

:collection:
   select the visit subcollection

:processor:
   SourceSelfSubdoc

:execution_order:
   must be run after all our input data (DOB, visit_date) is loaded
```


3. In the data dictionary, create a concept for our procedure ID
     
```{eval-rst}
:permanent_id:
   give any name you want, ex. "age_at_visit"

:name:
   "age at visit"

:source:
   select the source you created in step 2
   
:concept_handler:
   DetailedAgeFromDatesHandler

:collection:
   select the collection the calculated field will go in, i.e. the visit subcollection
   
:Concept handler args:
   Give the concept permanent IDs for the input fields
   dob_concept_id = "dob_xrvwavsftu"
   event_date_concept_id = "visit_date_xctwybwqxh"
   
:Concept-concept dependencies:
    include `dob_xrvwavsftu`, `visit_date_xctwybwqxh` (if Chiron knows this concept
    depends on these date concepts, it will help protect you from doing something stupid like loading
    them in the wrong order)
   
```

The remaining fields can be filled in as you wish.
    
4. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.
