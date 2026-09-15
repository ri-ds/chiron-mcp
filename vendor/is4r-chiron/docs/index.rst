.. Chiron documentation master file, created by
   sphinx-quickstart on Wed Oct 14 13:49:02 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Chiron's documentation!
==================================

Chiron is a data exploration/reporting tool for research data with a strong focus on
human-subject/patient data and longitudinal data. It has a built-in web interface that can be used directly, or an API for integrating Chiron features into existing applications.

Things Chiron can do:
^^^^^^^^^^^^^^^^^^^^^

- import and merge data from multiple sources
- during import, reorganize and modify data or create calculated fields
- users can browse merged data as a single, integrated dataset
- users can define cohorts and get cohort counts
- users can build a report of data that can be saved, shared, or exported to a file
- detailed access control over which patients and data each user is allowed to view


Things Chiron CANNOT do:
^^^^^^^^^^^^^^^^^^^^^^^^

- Chiron does not work on live data. It takes periodic (nightly, weekly, etc.) snapshots from the data source(s).
- Chiron is not a data collection tool. All data is read-only after being imported.

See Chiron in action:
^^^^^^^^^^^^^^^^^^^^^
View the `Chiron demo <https://chi.uc.edu/chiron_demo/>`_, which uses the Synthea artificial
EHR dataset.

.. toctree::
   :maxdepth: 1
   :caption: Versions:

   topics/version_changelog.rst

.. toctree::
   :maxdepth: 1
   :caption: Explanation:

   topics/system_overview.rst
   topics/data_dict.md
   topics/data_schema.md
   topics/event_collections.md
   topics/processors.md


.. toctree::
   :maxdepth: 1
   :caption: How To:

   topics/install.md
   topics/dd_configure.rst
   topics/custom_code.rst
   topics/etl.md
   topics/deploy.md
   topics/manage_users.md
   topics/examples
   topics/tests.md

.. toctree::
   :maxdepth: 1
   :caption: Reference:

   topics/utilities.rst
   topics/chiron_settings.rst
   topics/user_models.rst
   topics/data_dict_models.rst
   topics/processor_classes.rst
   topics/api.rst

   

   
   

   
   
   



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
