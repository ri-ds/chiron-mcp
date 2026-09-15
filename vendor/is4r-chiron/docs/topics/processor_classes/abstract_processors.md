# Abstract Processors


(ref-source-processor)=
## SourceProcessor (abstract)

```{eval-rst}
.. autoclass:: chiron.processors.abstract.SourceProcessor
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
```

(ref-standard-load-mixin)=
### StandardLoadMixin

```{eval-rst}
.. autoclass:: chiron.processors.abstract.StandardLoadMixin
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
```

(ref-etl-processor)=
## EtlProcessor (abstract)

```{eval-rst}
.. autoclass:: chiron.processors.abstract.EtlProcessor
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. _cohort-def-processor-abstract:
```
   
(ref-cohort-def-processor)=
## CohortDefProcessor (abstract)

```{eval-rst}
.. autoclass:: chiron.processors.abstract.CohortDefProcessor
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
```

## CohortDefProcessorBuiltInUiMixin

```{eval-rst}
.. autoclass:: chiron.processors.abstract.CohortDefProcessorBuiltInUiMixin
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. _display-processor-abstract:
```

(ref-display-processor)=
## DisplayProcessor (abstract)

```{eval-rst}
.. autoclass:: chiron.processors.abstract.DisplayProcessor
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
```


## AggregationMethod Classes for Display Processors

Display processors store custom lists of aggregation methods that they allow. For example,
a numeric display processor will usually include the Average aggregation method, but a text
processor would not. You can use any of the built-in aggregation methods in your custom display
processor or create your own by extending the AggregationMethod abstract class.

### AggregationMethod (abstract base class)

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation._base.AggregationMethod
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
```


### Average

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.Average
   :show-inheritance:
```

### CountAll

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.CountAll
   :show-inheritance:
```

### CountDistinct

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.CountDistinct
   :show-inheritance:
```

### Earliest

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.Earliest
   :show-inheritance:
```

### HasValue

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.HasValue
   :show-inheritance:
```

### HasValueText

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.HasValueText
   :show-inheritance:
```

### Latest

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.Latest
   :show-inheritance:
```

### ListAll

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.ListAll
   :show-inheritance:
```

### ListDistinct

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.ListDistinct
   :show-inheritance:
```

### Max

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.Max
   :show-inheritance:
```

### MaxDate

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.MaxDate
   :show-inheritance:
```

### Median

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.Median
   :show-inheritance:
```

### Min

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.Min
   :show-inheritance:
```

### MinDate

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.MinDate
   :show-inheritance:
```

### MostFrequent

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.MostFrequent
   :show-inheritance:
```

### StdDev

```{eval-rst}
.. autoclass:: chiron.processors.display.aggregation.StdDev
   :show-inheritance:
```