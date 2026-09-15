


Data Dictionary Models
======================

.. _dataset-model:

Dataset Model
-------------

.. autoclass:: chiron.models.Dataset
   :noindex:
   :members:
   :exclude-members: subcollections, DoesNotExist,MultipleObjectsReturned

DefaultTableDefConcept Model
----------------------------

.. autoclass:: chiron.models.DefaultTableDefConcept
   :noindex:
   :members:
   :exclude-members: DoesNotExist,MultipleObjectsReturned

.. _collection-model:

Collection Model
----------------

.. autoclass:: chiron.models.Collection
   :noindex:
   :members:
   :exclude-members: get_name_plural,
      instantiate, get_event_type, check_event_permission_group,
      check_event_user_access_level, user_can_view_collection,
      get_viewable_collections, DoesNotExist, MultipleObjectsReturned

.. _collection-relationship-model:

CollectionRelationship Model
----------------------------

.. autoclass:: chiron.models.CollectionRelationship
   :noindex:
   :members:
   :exclude-members: get_pk_collection, get_fk_collection,
      get_pk_concept_name, get_fk_concept_name, get_pk_collection_name,
      get_fk_collection_name

.. _source-model:

Source Model
----------------------

.. autoclass:: chiron.models.Source
   :noindex:
   :members:
   :exclude-members: get_processor, DoesNotExist, MultipleObjectsReturned

.. _processor-model:

Processor Model
---------------

.. autoclass:: chiron.models.Processor
   :noindex:
   :members:
   :exclude-members: instantiate, is_custom, DoesNotExist,MultipleObjectsReturned

SourceProcessorArg Model
---------------------------------------

.. autoclass:: chiron.models.SourceProcessorArg
   :noindex:
   :members:
   :exclude-members: DoesNotExist,MultipleObjectsReturned

.. _concept-model:

Concept Model
-------------

.. autoclass:: chiron.models.Concept
   :noindex:
   :members:
   :exclude-members: get_category_hierarchy, get_name_plural,
     get_full_database_field_name, check_permission_group, check_user_access_level,
     user_can_query_concept, get_etl_processor, get_cohort_def_processor_without_user,
     get_cohort_def_processor, get_collection_prefilters, prefilter_required,
     get_display_processor, get_summary_statistics, get_data_type, DoesNotExist,
     MultipleObjectsReturned

ConceptHandler Model
--------------------

.. autoclass:: chiron.models.ConceptHandler
   :noindex:
   :members:
   :exclude-members: get_processor_class, instantiate, DoesNotExist,MultipleObjectsReturned

ConceptHandlerArg Model
-----------------------

.. autoclass:: chiron.models.ConceptHandlerArg
   :noindex:
   :members:
   :exclude-members: get_value, DoesNotExist,MultipleObjectsReturned

.. _category-model:

Category Model
--------------

.. autoclass:: chiron.models.Category
   :noindex:
   :members:
   :exclude-members: get_ancestors, get_ancestor_names, get_level, get_top_level_parent,
     get_level_indent_string, check_permission_group, DoesNotExist, MultipleObjectsReturned



.. _autocreated-field-model:

AutocreatedField Model
-----------------------

.. autoclass:: chiron.models.AutocreatedField
   :noindex:
   :members:
   :exclude-members: get_name, get_created_cohorts, get_created_tables, get_viewable_reports, list_permission_groups, list_concepts_for_allowed_subjects, DoesNotExist, MultipleObjectsReturned
   
