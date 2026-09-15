

Chiron API
==========

Chiron has a built-in web interface you can use. However, all of the functionality of Chiron is available
as a web API if you want to integrate it into your own site.

.. _djangorestframework: https://www.django-rest-framework.org/

Chiron uses `djangorestframework`_ for the API. This tool allows you to browse the API of your
site directly using a web browser:

1. Start your Django server using ``python manage.py runserver``

2. Navigate to the API root in a web browser. Depending on how your URLs are set up, this will probably either be
   ``http://localhost:8000/api`` or ``http://localhost:8000/chiron/api``.




.. toctree::
   :maxdepth: 1
   :caption: Contents:

   api/api_viewsets.rst
   api/api_transforming_cohort_def.rst
   api/api_transforming_table_def.rst
   api/api_transforming_analysis_def.rst
