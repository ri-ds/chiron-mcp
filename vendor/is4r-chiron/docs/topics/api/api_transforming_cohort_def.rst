
.. _transforming-cohort-defs:

Transforming Cohort Definitions
===============================

You can define how to change a cohort def using a transformation dict. Chiron takes an existing
cohort definition and a transformation dict, applies the transformation, and returns a new 
cohort definition. In the API, this is done using endpoint :ref:`api-cohort-def-post`.


   
add_entry
---------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_add_entry
   :undoc-members:
   
Additional transformation arguments for specific processors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.processors.CohortDefBoolean.validate_form
.. automethod:: chiron.processors.CohortDefCategory.validate_form
.. automethod:: chiron.processors.CohortDefDateDeid.validate_form
.. automethod:: chiron.processors.CohortDefDate.validate_form
.. automethod:: chiron.processors.CohortDefNumber.validate_form
.. automethod:: chiron.processors.CohortDefText.validate_form
.. automethod:: chiron.processors.CohortDefNumberWithCategories.validate_form


delete_entry
------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_delete_entry
   :undoc-members:
   
add_criteria_set
----------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_add_criteria_set
   :undoc-members:
   
delete_criteria_set
-------------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_delete_criteria_set
   :undoc-members:
   
change_to_boolean_or
--------------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_change_to_boolean_or
   :undoc-members:
   
change_to_boolean_and
---------------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_change_to_boolean_and
   :undoc-members:
   
sort_cd_entries
---------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_sort_cd_entries
   :undoc-members:

clear_all
---------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_clear_all
   :undoc-members:

add_criteria_set_count_rule
---------------------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_add_criteria_set_count_rule
   :undoc-members:

create_event_rule
-----------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_create_event_rule
   :undoc-members:

modify_event_rule
-----------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_modify_event_rule
   :undoc-members:


delete_event_rule
-----------------

.. automodule:: chiron.api.utils.cohort_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_delete_event_rule
   :undoc-members:

























