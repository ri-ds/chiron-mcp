(example2)=
# calculated concept - multiple sources, subject data



EXAMPLE: We want a boolean field that shows `patient_eligibility` for our study. Patients are eligible if
they are under 30 and haven't opted out of participation. The `age` concept comes from source `demographics`
our of their EMR, and the `opt_out` concept comes from source `initial_consult` out of a REDCap instrument.

<hr>

Since there's more than one source, we have to load both input concepts into Chiron database first, and
then iterate the Chiron subject collection itself as a source in order to calculate patient eligibility.

1. Set up the data dictionary to load sources `demographics` and `opt_out`. This will get both
input concepts for our calculated field into Chiron.
   
2. In the data dictionary, we're going to add a new source for iterating the subject collection in the Chiron database:
   
```{eval-rst}
:name:
   give any name you want, ex. "chiron_subject_iterator"

:collection:
   select the collection the calculated field will go in, i.e. the subject collection

:processor:
   SourceSelf

:execution_order:
   must be run after sources `demographics` and `opt_out` so that the input fields are already loaded
```

3. Create an ETL processor and associated ConceptHandler

```python
from chiron.processors.abstract import EtlProcessor
from chiron import processors

class EtlEligibilityFlag(EtlProcessor):
    def pull_concept_value_from_record(self, record):
        """
        Used with SourceSelf, so each record will be a doc from our Chiron research database
        subject collection.
        """
        # get the input concept values
        age = record.get("age_xilvrwgfyn")
        opt_out = record.get("opt_out_aqfqqblpvq")
        
        if age is None or opt_out is None:
           return False
        
        if age < 30 and not opt_out:
           return True
        
        return False


class EligibilityFlagHandler(processors.BooleanHandler):
    def set_etl_processor(self, concept):
        self.etl_processor = EtlEligibilityFlag(concept)
```

4. Register the processor with Chiron in `chiron_config/processors/__init__.py`

```python
from chiron.processors.registration import ProcessorRegistry
from chiron import processors
from chiron_config.processors.my_etl_processors import EligibilityFlagHandler

ProcessorRegistry.register(processors.SourceSelf, EligibilityFlagHandler)
```

5. In the data dictionary, create a concept for our eligibility_flag
     
```{eval-rst}
:permanent_id:
   give any name you want, ex. "eligibility_flag"

:name:
   "patient eligibility"

:description:
   "Is the patient eligible for our study?"

:source:
   select the source you created in step 2
   
:concept_handler:
   EligibilityFlagHandler

:collection:
   select the collection the calculated field will go in, i.e. the subject collection
   
:Concept-concept dependencies:
    include `age_xilvrwgfyn` and `opt_out_aqfqqblpvq` (if Chiron knows this concept
    depends on those concepts, it will help protect you from doing something stupid like loading
    them in the wrong order)
   
```

The remaining fields can be filled in as you wish. There are no ConceptHandlerArgs for
our custom concept handler.

    
6. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.
