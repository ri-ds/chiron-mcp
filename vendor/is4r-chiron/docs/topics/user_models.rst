
User & Permission Models
========================

.. _chiron-user-model:

ChironUser Model
----------------

.. autoclass:: chiron.models.ChironUser
   :noindex:
   :members:
   :exclude-members: list_allowed_concepts, list_allowed_data_categories,
      list_concepts_for_allowed_subjects, DoesNotExist, MultipleObjectsReturned

.. _permission-group-model:

PermissionGroup Model
-----------------------

.. autoclass:: chiron.models.PermissionGroup
   :noindex:
   :members:
   :exclude-members: site_uses_permission_groups, DoesNotExist, MultipleObjectsReturned

.. _default-permission-group-model:

Default PermissionGroup Model
-----------------------------

.. autoclass:: chiron.models.DefaultPermissionGroup
   :noindex:
   :members:
   :exclude-members: DoesNotExist, MultipleObjectsReturned