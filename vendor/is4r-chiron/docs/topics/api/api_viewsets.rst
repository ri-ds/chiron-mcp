

API Endpoints
=============



ChironUsers
-----------

/chiron_users/ (GET)
^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ChironUserViewSet.list

/chiron_users/[chiron_user_id] (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.api.serializers.ChironUserSerializer




Me
--

/me/ (GET)
^^^^^^^^^^

.. automethod:: chiron.api.viewsets.MeViewSet.list


Collections
-----------

/collections/ (GET)
^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.CollectionViewSet.list

/collections/[permanent_id]/ (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.CollectionViewSet.retrieve

Additional data returned if include_criteria_set_options is True
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. automethod:: chiron.api.viewsets.CollectionViewSet._get_criteria_set_options

Additional data returned if include_criteria_set_event_options is True
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. automethod:: chiron.api.viewsets.CollectionViewSet._get_criteria_set_event_options


Concepts
--------

/concepts/ (GET)
^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ConceptViewSet.list

.. _api-concepts-detail-get:

/concepts/[permanent_id]/ (GET, PUT)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ConceptViewSet.retrieve

.. automethod:: chiron.api.viewsets.ConceptViewSet.update

Statistics returned for built-in cohort def processors
""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. automethod:: chiron.processors.CohortDefBoolean.get_statistics

.. automethod:: chiron.processors.CohortDefCategory.get_statistics

.. automethod:: chiron.processors.CohortDefDate.get_statistics

.. automethod:: chiron.processors.CohortDefNumber.get_statistics

.. automethod:: chiron.processors.CohortDefText.get_statistics


Form options returned for built-in cohort def processors
""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. automethod:: chiron.processors.CohortDefBoolean.get_form_options

.. automethod:: chiron.processors.CohortDefCategory.get_form_options

.. automethod:: chiron.processors.CohortDefDate.get_form_options

.. automethod:: chiron.processors.CohortDefNumber.get_form_options

.. automethod:: chiron.processors.CohortDefText.get_form_options







ConceptCategories
-----------------

/concept_categories/ (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ConceptCategoryViewSet.list

/concept_categories/[category_id]/ (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ConceptCategoryViewSet.retrieve






CohortDefinitions
-----------------

/cohort_def/ (GET)
^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.CohortDefViewSet.list

/cohort_def/[snapshot_id]/ (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.CohortDefViewSet.retrieve

.. _api-cohort-def-post:

/cohort_def/ (POST)
^^^^^^^^^^^^^^^^^^^

For an overview of how to build a transformation dict, see section :ref:`transforming-cohort-defs`.

.. automethod:: chiron.api.viewsets.CohortDefViewSet.create






TableDefinitions
----------------

/table_def/ (GET)
^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.TableDefViewSet.list

/table_def/[snapshot_id]/ (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.TableDefViewSet.retrieve

.. _api-table-def-post:

/table_def/ (POST)
^^^^^^^^^^^^^^^^^^

For an overview of how to build a transformation dict, see section :ref:`transforming-table-defs`.

.. automethod:: chiron.api.viewsets.TableDefViewSet.create







QueryTools
----------

/query_tools/count/ (GET, POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.QueryToolsViewSet.count

/query_tools/preview/ (GET, POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.QueryToolsViewSet.preview

/query_tools/export_csv/ (GET, POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.QueryToolsViewSet.export_csv



AnalysisDefinitions
-------------------

/analysis_def/ (GET)
^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.AnalysisDefViewSet.list

/analysis_def/[snapshot_id]/ (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.AnalysisDefViewSet.retrieve

.. _api-analysis-def-post:

/analysis_def/ (POST)
^^^^^^^^^^^^^^^^^^^^^

For an overview of how to build a transformation dict, see section :ref:`transforming-analysis-defs`.

.. automethod:: chiron.api.viewsets.AnalysisDefViewSet.create




AnalysisTools
-------------


/analysis_tools/run_analysis/ (GET, POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.AnalysisToolsViewSet.run_analysis

/analysis_tools/export_csv/ (GET, POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.AnalysisToolsViewSet.export_csv



.. _api-endpoints-projects:

Projects
--------

/projects/ (GET)
^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ProjectViewSet.list

/projects/[project_id] (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ProjectViewSet.retrieve

/projects/[project_id] (POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ProjectViewSet.create

/projects/[project_id] (PUT)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ProjectViewSet.update

/projects/[project_id] (DELETE)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ProjectViewSet.delete


Reports
-------

/reports/ (GET)
^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ReportViewSet.list

.. _api-endpoints-reports-flag:

/reports/[report_id]/flag/ (POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ReportViewSet.flag

Version
-------

/version/ (GET)
^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.VersionViewSet.list





ReportTools
-----------

/report_tools/[report_id]/share/ (POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ReportToolsViewSet.share

/report_tools/[report_id]/load_as_active (POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ReportToolsViewSet.load_as_active

/report_tools/[report_id]/preview/ (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ReportToolsViewSet.preview

/report_tools/[report_id]/export_csv/ (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: chiron.api.viewsets.ReportToolsViewSet.export_csv







   