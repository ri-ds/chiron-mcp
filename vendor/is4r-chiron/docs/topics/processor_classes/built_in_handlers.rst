
.. _built-in-handlers:

Built-In Concept Handlers
=========================


Use the Concept and ConceptHandlerArg models to set and customize the concept handler for each concept.

Concept handlers must be used with an appropriate source. For example, a concept handler that
expects an array of dicts won't work with SourceDjangoModel, which returns a Django queryset. Each
concept here lists which sources it can be used with.

Standard Concept Handlers
-------------------------

CategoryHandler
^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.CategoryHandler
   :show-inheritance:

TextHandler
^^^^^^^^^^^

.. autoclass:: chiron.processors.TextHandler
   :show-inheritance:

.. _date-handler:

DateHandler
^^^^^^^^^^^

.. autoclass:: chiron.processors.DateHandler
   :show-inheritance:

BooleanHandler
^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.BooleanHandler
   :show-inheritance:

IntegerHandler
^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.IntegerHandler
   :show-inheritance:

FloatHandler
^^^^^^^^^^^^

.. autoclass:: chiron.processors.FloatHandler
   :show-inheritance:

IntegerWithCategoriesHandler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.IntegerWithCategoriesHandler
   :show-inheritance:

FloatWithCategoriesHandler
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.FloatWithCategoriesHandler
   :show-inheritance:

SubjectHyperlinkHandler
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.SubjectHyperlinkHandler
   :show-inheritance:

.. _detailed-age-handler:

DetailedAgeHandler
^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.DetailedAgeHandler
   :show-inheritance:

.. _current-age-handler:

CurrentAgeHandler
^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.CurrentAgeHandler
   :show-inheritance:

Special Concept Handlers
------------------------

.. _subject-matching-to-text-handler:

SubjectMatchingToTextHandler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.SubjectMatchingToTextHandler
   :show-inheritance:

SubjectMatchingToSubjectHyperlinkHandler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.SubjectMatchingToSubjectHyperlinkHandler
   :show-inheritance:

.. _auto-subject-id-handler:

AutoSubjectIdHandler
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.AutoSubjectIdHandler
   :show-inheritance:

.. _auto-subcollection-id-handler:

AutoSubcollectionIdHandler
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.AutoSubcollectionIdHandler
   :show-inheritance:

DetailedAgeFromDatesHandler
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.DetailedAgeFromDatesHandler
   :show-inheritance:

CurrentAgeFromDobHandler
^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: chiron.processors.CurrentAgeFromDobHandler
   :show-inheritance:
