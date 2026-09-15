
(how-to-manage-users)=
# Manage Users and Permissions

There are two systems for managing a user's access to data: access levels and permission groups.

Access Levels
-------------

Access levels control the type of data a user is allowed to see. Each {ref}`Chiron user<chiron-user-model>` has one of three access levels:

- **phi** - Users will be able to see patient-level data, including concepts that are flagged as PHI.
- **deid** - Users will be able to see patient-level data, but will not have access to PHI.
- **agg** - Users can only see aggregated data. They do not have access to PHI and do not have access to patient-level values.

**Settings relevant to PHI access**

- Concepts containing PHI should have the has_phi flag set to True.
- Additionally, flagged concepts can set values for cohort_def_processor_deid_alt and display_processor_deid_alt. These can be set to special processor classes that allow the user to interact with the concept without seeing PHI. If these flags aren't set, the concept will be hidden from the user.

**Settings relevant to aggregated access**

- Concepts that shouldn't be shown in aggregated view should have the exclude_from_aggregated flag set to True. For example, you might want to hide a text field containing detailed comments specific to a patient.
- django setting CHIRON_AGG_SUBJECT_COUNT_MIN_LIMIT gives the minimum patient count that should be given. For example, if set to the default of 5, any patient counts less than 5 will show as "<5" rather than the actual number.


Permission Groups
-----------------

{ref}`Permission groups<permission-group-model>` limit users' access to specific groups of subjects or specific groups of concepts. This is useful, for example, if you have data coming from multiple different studies and want to limit some users' access to only data from specific studies.

If you don't need permission groups on your project, simply leave the PermissionGroups table empty.

Once you have any {ref}`permission group<permission-group-model>` records defined, every user must belong to at least one permission group or they won't be able to see any data. If a user belongs to multiple permission groups, their access level will be the union of all the groups. In other words, they will be able to see a subject or concept if at least one of their permission groups grants them access.

How do access levels work with permission groups?
-------------------------------------------------

Both access levels and permission groups restrict access to concepts. If a concept is blocked by either system, the user will not be able to see it.

Default Permissions for AutoCreated Users
-----------------------------------------

A {ref}`Chiron user<chiron-user-model>` will be autocreated if `Dataset.autocreate_chiron_user=True` (see {ref}`the Dataset model<dataset-model>`). The permission levels for autocreated users will be controlled by these fields:

- Dataset.auto_access_level
- Dataset.auto_can_view_workspace
- Dataset.auto_can_view_subject_details
- In the {ref}`DefaultPermissionGroup model<default-permission-group-model>`, any permission groups associated with this Dataset.

User Permissions With Multiple Datasets
---------------------------------------

A Django User will have a separate {ref}`ChironUser<chiron-user-model>` entry for each dataset they need to access. So their permissions can be different for each dataset.