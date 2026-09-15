
.. _built-in-processors:

Built-In Source Processors
==========================

You can change many behaviors in Chiron with just the data dictionary. Sources in the data dictionary
will define the source processor used to read data from a source during the ETL. Concepts in the data dictionary will define
the concept handler used to import, query, and display concept values.

Source Processors for Importing
-------------------------------

Use the Source and SourceProcessorArg models to set and customize the source processor for each source.


SourceDjangoModel
^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.SourceDjangoModel
   :show-inheritance:
   
SourceCsv
^^^^^^^^^

.. autoclass:: chiron.processors.SourceCsv
   :show-inheritance:

Source Processors for Calculated Fields
---------------------------------------

.. _source-self-processor:

SourceSelf
^^^^^^^^^^

.. autoclass:: chiron.processors.SourceSelf
   :show-inheritance:
   
.. _source-self-subdoc-processor:

SourceSelfSubdoc
^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.SourceSelfSubdoc
   :show-inheritance:
