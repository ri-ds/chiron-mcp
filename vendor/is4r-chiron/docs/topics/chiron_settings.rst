
.. _chiron-settings:

Chiron Global Settings
======================

All of these settings can be defined in your django settings file.

Website and API Settings
------------------------

.. automodule:: chiron.chiron_settings
   :members: CHIRON_SITE_TITLE, CHIRON_FOOTER_TEMPLATE, CHIRON_EXTRA_NAVBAR_ITEMS, CHIRON_INFOBAR, CHIRON_INFOBAR_TYPE, CHIRON_LOGOUT_URL, CHIRON_SHOW_ANALYSIS_VIEW, CHIRON_AGG_DELIMITER

.. _chiron-settings-dd:

Data Dictionary Settings
------------------------

.. automodule:: chiron.chiron_settings
   :noindex:
   :members: CHIRON_EVENT_CONCEPT_TYPE

.. _chiron-settings-database:

Database Settings
-----------------

.. automodule:: chiron.chiron_settings
   :noindex:
   :members: CHIRON_DATABASE, CHIRON_USE_STAGING_DURING_ETL, CHIRON_KEEP_DATABASE_BACKUP, CHIRON_SQL_ALCHEMY_CONNECTION_STRING, CHIRON_POSTGRES_SCHEMA_NAME_PREPEND, CHIRON_REQUIRE_SUCCESSFUL_CONCEPT_SEARCH_UPDATE, CHIRON_PG_CONN_OPTIONS_SITE, CHIRON_PG_CONN_OPTIONS_MGMT

.. _chiron-settings-file-location:

File Location Settings
----------------------

.. automodule:: chiron.chiron_settings
   :noindex:
   :members: CHIRON_DATA_DICT_BACKUP_DIR, CHIRON_AUTOCREATE_SOURCE_LISTS, CHIRON_DATA_SUMMARY_FUNCTION_PATH, CHIRON_PROCESSOR_MODULES, CHIRON_SOURCE_DATA_DIRECTORY

User and Permission Settings
----------------------------

.. automodule:: chiron.chiron_settings
   :noindex:
   :members: CHIRON_AGG_SUBJECT_COUNT_MIN_LIMIT

.. _chiron-settings-performance:

Performance and Cache Settings
------------------------------

.. automodule:: chiron.chiron_settings
   :noindex:
   :members: CHIRON_USE_CACHES, CHIRON_GET_QUERY_PERFORMANCE, CHIRON_ABBREVIATED_ETL_DEFAULT_RECORD_COUNT, CHIRON_ABBREVIATED_ETL_RECORD_COUNTS, CHIRON_BULK_INSERT_BATCH_SIZE

Email Notification Settings
---------------------------

.. automodule:: chiron.chiron_settings
   :noindex:
   :members: CHIRON_EMAIL_NOTIFICATIONS, CHIRON_EMAIL_FROM


.. _chiron-settings-ontology:

Ontology Settings
-----------------

.. automodule:: chiron.chiron_settings
   :noindex:
   :members: CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT