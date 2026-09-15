(example4)=
# calculated concept - multiple sources, subcollection data, longitudinal

EXAMPLE: calculate condition_change (IMPROVED, WORSENED, UNCHANGED) for a visit by comparing to the previous visit.
The input value will be `condition_severity` which has a value of 1 to 10, with 10 being the worst.

<hr>

The tricky thing about this one is that we can't look at a single visit record. We need to get the
previous visit record as well and compare `condition_severity` to see if it increased, decreased, or stayed the same.

We will load visit data into Chiron database first, and
then iterate the visit subcollection itself as a source in order to calculate `condition_change`.

1. Set up the data dictionary to load source `visit`. This will get the `condition_severity` concept into Chiron.

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
   
:Source processor args:
    With SourceSelfSubdoc, we always get a 'subdoc' dict with data for the current subcollection
    record and a 'doc' dict with data for the associated subject. In this case, we also need
    a 'subdocs' list of dicts that will have all subcollection records for this subject. We get
    this by specifying include_related_subdocs (name="include_related_subdocs",
    data_type="boolean", value="True").
```

By default, SourceSelfSubdoc will only return data for a single visit with each iteration. But we also need to see other visits
for the patient to make our comparison. We can tell Chiron we want this with a SourceProcessorArg:

```{eval-rst}
:name:
   "include_related_subdocs"

:data_type:
   "boolean/null"

:value:
   True
```

3. Create an ETL processor and associated ConceptHandler

```python
import datetime

from chiron.processors.abstract import EtlProcessor
from chiron import processors

class EtlConditionChange(EtlProcessor):
    """ calculate condition_change (IMPROVED, WORSENED, UNCHANGED) for a visit by comparing condition_severity to the previous visit """
    
    def pull_concept_value_from_record(self, record):
        """
        Used with SourceSelfSubdoc. Each record will be a dict with values:
        - subdoc: a document from the visit subcollection
        - doc: the document from the subject collection for the associated subject
        - subdocs: a list of all the other visits for this subject
        """
        # get the input concept values
        visit_date = record["subdoc"].get("visit_date_xilvrwgfyn")
        severity = record["subdoc"].get("condition_severity_aqfqqblpvq")
        previous_severity = self._find_previous_condition_severity(visit_date, record["subdocs"])
        
        if severity is None or previous_severity is None:
            return None
        
        if severity > previous_severity:
            severity_change = "WORSENED"
        elif severity < previous_severity:
            severity_change = "IMPROVED"
        else:
            severity_change = "UNCHANGED"
        return severity_change
    
    def _find_previous_condition_severity(self, visit_date, subdocs):
        """ find the previous visit_date and get the condition_severity """
        if visit_date is None or len(subdocs) < 2:
            return None
        
        # find the previous visit closest in time to visit_date
        previous_doc = None
        previous_doc_date = datetime.date(1900, 1, 1)
        for doc in subdocs:
            doc_date = doc.get("visit_date_xilvrwgfyn")
            if doc_date and doc_date < visit_date and doc_date > previous_doc_date:
                previous_doc = doc
                previous_doc_date = doc_date
                
        # return none if no previous visits were found
        if previous_doc is None:
            return None
        
        return previous_doc.get("condition_severity")

class ConditionChangeHandler(processors.CategoryHandler):
    def set_etl_processor(self, concept):
        self.etl_processor = EtlConditionChange(concept)
```

4. Register the processor with Chiron in `chiron_config/processors/__init__.py`

```python
from chiron.processors.registration import ProcessorRegistry
from chiron import processors
from chiron_config.processors.my_etl_processors import ConditionChangeHandler

ProcessorRegistry.register(processors.SourceSelfSubdoc, ConditionChangeHandler)
```

5. In the data dictionary, create a concept for our condition_change
     
```{eval-rst}
:permanent_id:
   give any name you want, ex. "condition_change"

:name:
   "condition change from previous visit"

:source:
   select the source you created in step 2
   
:concept_handler:
   ConditionChangeHandler

:collection:
   select the collection the calculated field will go in, i.e. the visit collection
   
:Concept-concept dependencies:
    include `visit_date_xilvrwgfyn` and `condition_severity_aqfqqblpvq` (if Chiron knows this
    concept depends on those concepts, it will help protect you from doing something stupid like
    loading them in the wrong order)
```

The remaining fields can be filled in as you wish, and there are no ConceptHandlerArgs for
our custom concept handler.
     
6. That should be it. The next time you run the ETL, your new self-referential source should run
at the end and populate your new calculated concept.