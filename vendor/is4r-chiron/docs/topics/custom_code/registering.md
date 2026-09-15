(registering-custom-processors)=
# Registering Custom Code

{ref}`Source processors<processor-def>` are registered with Chiron directly. The other three types of {ref}`processors<processor-def>` (ETL,
cohort def, and display) need to first be added to a {ref}`concept handler<concept-handler-def>`. Then the concept handler
is registered with Chiron.

Registration is done in pairs. Each entry will include a source processor and concept handler that are allowed to be used together. For example, it you have a custom concept handler that can be used with the built-in SourceDjangoModel processor, you would register them together like this:

```python
from chiron.processors.registration import ProcessorRegistry
from chiron.processors import SourceDjangoModel

ProcessorRegistry.register(SourceDjangoModel, MyCustomHandler)
```

As a shorthand, you can register multiple source processors and multiple concept handlers at the same time. In this case, every source processor will be associated with every concept handler.

For example, if you have a custom source processor that returns records as Python dictionaries, you could do this:

```python
from chiron.processors.registration import ProcessorRegistry
from chiron.processors import CategoryHandler, TextHandler, DateHandler, FloatHandler, IntegerHandler

ProcessorRegistry.register(MySourceProcessor, [
   CategoryHandler,
   TextHandler,
   DateHandler,
   FloatHandler,
   IntegerHandler,
])
```

Tell Chiron in which modules your processors are registered. This can be done using the
{ref}`CHIRON_PROCESSOR_MODULES<chiron-settings-file-location>` setting. The default is to load the built-in Chiron processors. So you
will need to add the path to the package/module where your custom processors are:

```python
CHIRON_PROCESSOR_MODULES = ["chiron.processors", "chiron_config.processors"]
```

Note: If you include a module path, that module will be checked. If you include a package path,
looks in the `__init__.py` file for the package.

## Using Registered Classes in Your Data Dictionary

After a custom source processor is registered, it can be associated with any source
collection using the field {ref}`Source.processor<source-model>`. Custom concept handlers can be
associated with any concept using the field {ref}`Concept.concept_handler<concept-model>`.