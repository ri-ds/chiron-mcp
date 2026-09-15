# Write Code for Calculated Concepts

Follow this guideline to choose how to implement a calculated concept.

## 1. Single source

**Is all of the input data you need for your calculated concept coming from the same source in the same record?**

Use a custom {ref}`ETL processor<ref-etl-processor>` associated with the same source collection as your input data.

*EXAMPLE:* {ref}`example1`


## 2. Mutiple sources

If the input data for your calculated concept is coming from multiple sources, the approach in
step 1 won't work because no source will have all the data you need.

Instead, we load all the sources containing our input data first, then we will create a new source
that iterates a Chiron collection itself and loads the calculated value back into the collection.
This new source has to run after our input data sources so that the data is already loaded.

**Are all of the input concepts in the subject collection?**

After the sources for the input concepts are loaded, we can use the {ref}`SourceSelf<source-self-processor>` processor to iterate the subject
colection.

*EXAMPLE:* {ref}`example2`

**Are all of the input concepts going into a subcollection (and associated subject)?**

We can use the {ref}`SourceSelfSubdoc<source-self-subdoc-processor>` processor to iterate the subcollection. For each subcollection
record, it will also grab the related subject document from the subject collection.

*EXAMPLE:* {ref}`example3`

In some situations, the calculated concept might actually be comparing data longitudinally. For example,
you might want to calculate whether a patient's condition has improved or worsened by comparing each
visit to the previous visit. Again we can use the {ref}`SourceSelfSubdoc<source-self-subdoc-processor>` processor, but we need to
provide the additional argument `include_related_subdocs=True`.

*EXAMPLE:* {ref}`example4`



