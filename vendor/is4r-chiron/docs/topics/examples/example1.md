(example1)=
# calculated concept - single source

EXAMPLE: We're importing lab results. Each record has a `value` along with a `min_value` and `max_value`, 
and we want a calculated concept that will flag the value as LOW, HIGH, or NORMAL.

<hr>

This data is coming from an external Source that has already been defined in the data dictionary.
In this example, the Source is named lab_results and comes from a Django model, so we can use the
ETL Processor class `EtlDjangoField` as a base for our custom class.

1. Create a custom ETL processor to calculate the value. 

```python
from chiron.processors import EtlDjangoField
from chiron import processors

class EtlNormalFlag(EtlDjangoField):
    def pull_concept_value_from_record(self, record):
        lab_result = record.numeric_value
        max_value = record.max_value
        min_value = record.min_value
        if not lab_result or not max_value or not min_value:
            return None
        if lab_result > max_value:
            return "HIGH"
        elif lab_result < min_value:
            return "LOW"
        return "NORMAL"


class NormalFlagHandler(processors.TextHandler):
    def set_etl_processor(self, concept):
        self.etl_processor = EtlNormalFlag(concept)
```

2. Register the processor with Chiron in `chiron_config/processors/__init__.py`

```python
from chiron.processors.registration import ProcessorRegistry
from chiron import processors
from chiron_config.processors.my_etl_processors import NormalFlagHandler

ProcessorRegistry.register(processors.SourceDjangoModel, NormalFlagHandler)
```

3. Create a Concept in your data dictionary for this new concept.
    - The input data comes from the lab_results source, so it will be associated with that source.
    - The calculated concept will be 1:1 with a lab result, so it will be associated with that collection.
    - It will use the new ETL processor we just created.
    - We hard-coded all the input values and behavior in our ETL processor, so we don't need any Concept Handler Args.