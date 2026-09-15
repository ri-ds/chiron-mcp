from django.core.management.base import BaseCommand

from chiron.models import ConceptHandler, Concept


class Command(BaseCommand):
    """
    Globally move all references from one concept handler to another.

    Rename a concept hander:

    - Modify the concept handler class name in code.
    - When you run `python manage.py`, you should get a warning that it's missing (unless there
      are no references to it, then it will be deleted automatically and you're finished).
    - Run this script to update from the old name to the new name.

    Delete a concept handler and move all it's references to another concept handler:

    - If not done already, create and register the new concept handler.
    - Run this script to redirect all references from the old concept handler to the new.
    - You should now be able to unregister/delete the old concept handler. Since there are no
      references to the old concept handler, it should be automatically deleted.

    .. code-block:: bash

        python manage.py chiron_merge_handlers [old_handler_name] [new_handler_name]
    """

    help = "Globally move all references from one concept handler to another."

    def print_out(self, *args):
        """A wrapper for self.stdout.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        self.stdout.write(",".join(strings))

    def print_err(self, *args):
        """A wrapper for self.stderr.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        self.stderr.write(",".join(strings))

    def add_arguments(self, parser):
        parser.add_argument("old_handler_name")
        parser.add_argument("new_handler_name")

    def handle(self, *args, **options):
        old_name = options["old_handler_name"]
        new_name = options["new_handler_name"]

        # check that new_name doesn't exist yet
        oOld = ConceptHandler.objects.filter(name=old_name).first()
        oNew = ConceptHandler.objects.filter(name=new_name).first()
        if not oOld:
            msg = (
                f"The concept handler '{old_name}' doesn't exist in the database."
                f" Either you misspelled the handler class name, or there are no remaining"
                f" references to that handler that need to be merged."
            )
            return
        if not oNew:
            msg = (
                f"Unable to find any concept handler named "
                f"'{new_name}'. Is that concept handler registered in code?"
            )
            raise Exception(msg)

        qConcept = Concept.objects.filter(concept_handler=oOld)
        count_updated = qConcept.count()
        for oConcept in qConcept:
            oConcept.concept_handler = oNew
            oConcept.save()

        print(f"{count_updated} references to '{old_name}' have been copied to '{new_name}'.")
        print(
            f"If you have not already unregistered/deleted '{old_name}' from your code,"
            f" you may safely do so."
        )
