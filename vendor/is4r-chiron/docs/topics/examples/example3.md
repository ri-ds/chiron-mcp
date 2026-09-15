(example3)=
# calculated concept - multiple sources, subcollection data

EXAMPLE: Calculate age at time of visit using `DOB` in the subject collection and `visit_date`
in the visit subcollection. The `DOB` concept comes from source `demographics`
our of their EMR, and the `visit_date` concept comes from source `visit` out of a REDCap instrument.

<hr>

Since there's more than one source, we have to load both input concepts into Chiron database first, and
then iterate the visit subcollection itself as a source in order to calculate `age_at_visit`.

1. Set up the data dictionary to load sources `demographics` and `visit`. This will get both
input concepts for our calculated field into Chiron.

2. In the data dictionary, we're going to add a new source for iterating the visit subcollection in the Chiron database:
   
```{eval-rst}
:name:
   give any name you want, ex. "chiron_visit_iterator"

:collection:
   visit

:processor:
   SourceSelfSubdoc

:execution_order:
   must be run after sources `demographics` and `visit` so that the input fields are already loaded
```

3. Create an ETL processor and associated ConceptHandler

```python
from chiron.processors.abstract import EtlProcessor
from chiron import processors

class EtlAgeAtVisit(EtlProcessor):
    """ calculates age at time of visit """
    
    def pull_concept_value_from_record(self, record):
        """
        Used with SourceSelfSubdoc. Each record will be a dict with values:
        - subdoc: a document from the visit subcollection
        - doc: the document from the subject collection for the associated subject
        """
        # get the input concept values
        dob = record["doc"].get("dob_xilvrwgfyn")
        visit_date = record["subdoc"].get("visit_date_aqfqqblpvq")
        
        # set to None if input values are missing
        if dob is None or visit_date is None:
           return None
        
        # calculate age at time of visit
        return visit_date.year - dob.year - ((visit_date.month, visit_date.day) < (dob.month, dob.day))


class AgeAtVisitHandler(processors.IntegerHandler):
    def set_etl_processor(self, concept):
        self.etl_processor = EtlAgeAtVisit(concept)
```

4. Register the processor with Chiron in `chiron_config/processors/__init__.py`

```python
from chiron.processors.registration import ProcessorRegistry
from chiron import processors
from chiron_config.processors.my_etl_processors import AgeAtVisitHandler

ProcessorRegistry.register(processors.SourceSelfSubdoc, AgeAtVisitHandler)
```

5. In the data dictionary, create a concept for our age_at_visit
     
```{eval-rst}
:permanent_id:
   give any name you want, ex. "age_at_visit"

:name:
   "age at visit"

:source:
   select the source you created in step 2
   
:concept_handler:
   AgeAtVisitHandler

:collection:
   select the collection the calculated field will go in, i.e. the visit collection
   
:Concept-concept dependencies:
    include `dob_xilvrwgfyn` and `visit_date_aqfqqblpvq` (if Chiron knows this concept
    depends on those concepts, it will help protect you from doing something stupid like loading
    them in the wrong order)
```

The remaining fields can be filled in as you wish, and there are no ConceptHandlerArgs for
our custom concept handler.
     
6. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.