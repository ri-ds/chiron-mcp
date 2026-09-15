
(understanding-processors)=
# Understanding Processors and Handlers

The **processor classes** control how data is loaded into the research database from data sources and how it is
displayed and queried. Chiron has a variety of {ref}`built-in-processors` that you can use
without writing any code. However, if you need customized behavior beyond what's already provided,
you can create your own processors.

(processor-def)=
## Processor Classes

Various behavior in Chiron is controlled by processor classes. Processor classes are a powerful way to get custom behavior without modifying Chiron code directly. There are built-in processor classes for common needs, or you can write your own.

The processors to use are specified in the data dictionary. There are 3 types of processors for Concepts and 1 type of processor for Sources.

```{eval-rst}
:Source Processor:
   *(associated with a source)* During the ETL, the source
   collection processor class provides a standardized interface for retrieving records from a data source.

:ETL Processor:
   *(associated with a concept)* During the ETL, the ETL processor will take a whole record provided
   by the source processor and return a specific value to store in the research database for that
   concept.

:CohortDef Processor:
   *(associated with a concept)* The cohort def processor controls how a concept gets applied to
   queries. It also helps with getting summary statistics for the concept.

:Display Processor:
   *(associated with a concept)* The display processor controls how stored values for a concept
   are aggregated, displayed and sorted in reports.
```

(concept-handler-def)=
## Concept Handler Classes

There are three types of processors associated with a concept - ELT, CohortDef, and Display. There can
also be alternative CohortDef and Display processors for a concept that provide deidentifed access
to the data. And processors take various arguments to allow customization as well. 

Because of all the complexity around processors for concepts, we create logical bundles of processors in a 
single class called a ConceptHandler. The Concept handler is a light wrapper around the different
processors for a concept. It provides an abstraction layer that makes it simpler to change the
behavior or data type of a concept in the data dictionary.

## The ETL Process

The ETL process is managed by Chiron and will be based on your data dictionary. The work of fetching source records is carried out by the Source processor, and the work of fetching individual concept values out of a source record is carried out by the ETL Processors.

Here is a simplified overview of the ETL process showing what Source processors and ETL processors do:

```{mermaid}
    sequenceDiagram
        participant Chiron
        participant Med Source
        participant Med Name ETLProcessor
        participant Med Type ETLProcessor
        participant Med Collection
        Chiron->>Med Source: Request first medication record
        Med Source->>Chiron: Return medication record
        Chiron->>Med Name ETLProcessor: Pass first medication record
        Med Name ETLProcessor->>Chiron: Return medication name
        Chiron->>Med Type ETLProcessor: Pass first medication record
        Med Type ETLProcessor->>Chiron: Return medication type
        Chiron->>Med Collection: Write first medication doc {name: "Tylenol", type: "fever reducer"}
        Chiron->>Med Source: Request second medication record
```

