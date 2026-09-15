
.. _transforming-analysis-defs:

Transforming Analysis Definitions
=================================

You can define how to change an analysis def using a transformation dict. Chiron takes an existing
analysis definition and a transformation dict, applies the transformation, and returns a new
analysis definition. In the API, this is done using endpoint :ref:`api-analysis-def-post`.

.. _analysis-def-transformations-add-entry:
   
add_entry (analysis def)
------------------------

.. automodule:: chiron.api.utils.analysis_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_add_entry
   :undoc-members:


delete_entry (analysis def)
---------------------------

.. automodule:: chiron.api.utils.analysis_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_delete_entry
   :undoc-members:
   
move_entry (analysis def)
-------------------------

.. automodule:: chiron.api.utils.analysis_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_move_entry
   :undoc-members:
   
swap_rows_and_cols
------------------

.. automodule:: chiron.api.utils.analysis_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_swap_rows_and_cols
   :undoc-members:

clear_all
---------

.. automodule:: chiron.api.utils.analysis_def
   :noindex:
   :show-inheritance:
   :members: apply_transformation_clear_all
   :undoc-members:

   


























