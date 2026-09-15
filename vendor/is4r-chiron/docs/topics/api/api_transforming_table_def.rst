
.. _transforming-table-defs:

Transforming Table Definitions
==============================

You can define how to change a table def using a transformation dict. Chiron takes an existing
table definition and a transformation dict, applies the transformation, and returns a new 
table definition. In the API, this is done using endpoint :ref:`api-table-def-post`.

.. _table-def-transformations-add-entry:
   
add_entry (table def)
---------------------

.. automodule:: chiron.api.utils.table_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_add_entry
   :undoc-members:


delete_entry (table def)
------------------------

.. automodule:: chiron.api.utils.table_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_delete_entry
   :undoc-members:
   
resort_columns
--------------

.. automodule:: chiron.api.utils.table_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_resort_columns
   :undoc-members:
   
add_sort_entry
--------------

.. automodule:: chiron.api.utils.table_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_add_sort_entry
   :undoc-members:

clear_sort_entries
------------------

.. automodule:: chiron.api.utils.table_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_clear_sort_entries
   :undoc-members:

bulk_add_entries
----------------

.. automodule:: chiron.api.utils.table_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_bulk_add_entries
   :undoc-members:

add_category
------------

.. automodule:: chiron.api.utils.table_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_add_category
   :undoc-members:
   


























