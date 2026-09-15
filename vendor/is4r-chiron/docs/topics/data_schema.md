
# Understanding the Data Schema

(data-model-explainer)=
## The Research Data Model

Your research database has a simple data model with a single subject (root) collection at the core and any number of 1:many or many:many subcollections linked to it. Here's an example where subjects have a 1:many relationship with biospecimen, encounters, and procedures, and they have a many:many relationship with provider.

```{mermaid}

    erDiagram
        Subject }|--o{ Provider : ""
        Subject ||--o{ Biospecimen : ""
        Subject ||--o{ Encounter : ""
        Subject ||--o{ Procedure : ""
```

With the many:many relationship, each subject can have multiple providers, and each provider can have multiple subjects. Note however, that while a subject can have zero providers, a provider can't have zero subjects. This will always be true for all subcollections - each subcollection record **must** be associated with at least one subject.

<hr>

## Datasets

Starting in Chiron Version 4.0, you can have multiple unrelated datasets loaded into a single chiron instance. This is useful if you have a lot of datasets and don't want to maintain a separate chiron instance for each one. User permissions for each dataset are distinct, and a user can only interact with one dataset at a time. There's no way to do queries across multiple datasets.

```{mermaid}

    erDiagram
        Dataset1_Subject }|--o{ Provider : ""
        Dataset1_Subject ||--o{ Biospecimen : ""
        Dataset1_Subject ||--o{ Encounter : ""
        Dataset2_Subject ||--o{ Survey : ""
        Dataset2_Subject ||--o{ Sample : ""
```

<hr>

## Subcollection Relationships

Starting in Chiron version 3.1, you can also associate subcollection records with each other using the CollectionRelationship model. This will help when Chiron is generating a dataset from multiple subcollections and should be used when it makes sense.

Here is the above example again with Procedures and Biospecimen linked to their associated encounters.

```{mermaid}

    erDiagram
        Subject ||--o{ Medication : ""
        Subject ||--o{ Biospecimen : ""
        Subject ||--o{ Encounter : ""
        Subject ||--o{ Procedure : ""
        Encounter ||--o{ Biospecimen : "collected during"
        Encounter ||--o{ Procedure : "performed during"
```