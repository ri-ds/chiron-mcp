from django.core.management.base import BaseCommand

from chiron.models import Processor, Source


class Command(BaseCommand):
    """
    Globally move all references from one processor to another.

    Rename a source processor

    - Modify the processor class name in code.
    - When you run `python manage.py`, you should get a warning that it's missing (unless there
      are no references to it, then it will be deleted automatically and you're finished).
    - Run this script to update from the old name to the new name.

    Delete a source processor and move all it's references to another source processor:

    - If not done already, create and register the new processor.
    - Run this script to redirect all references from the old processor to the new.
    - You can now unregister/delete the old processor. Since there are no
      references to the old processor, it should be automatically deleted.

    .. code-block:: bash

        python manage.py chiron_merge_processors [old_processor_name] [new_processor_name]
    """

    help = "Globally move all references from one processor to another."

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
        parser.add_argument("old_processor_name")
        parser.add_argument("new_processor_name")

    def handle(self, *args, **options):
        old_name = options["old_processor_name"]
        new_name = options["new_processor_name"]

        # check that new_name doesn't exist yet
        oOld = Processor.objects.filter(name=old_name).first()
        oNew = Processor.objects.filter(name=new_name).first()
        if not oOld:
            msg = (
                f"The processor '{old_name}' doesn't exist in the database."
                f" Either you misspelled the processor class name, or there are no remaining"
                f" references to that processor that need to be merged."
            )
            return
        if not oNew:
            msg = (
                f"Unable to find any processor named "
                f"'{new_name}'. Is that processor registered in code?"
            )
            raise Exception(msg)

        qSource = Source.objects.filter(processor=oOld)
        count_updated = qSource.count()
        for oSource in qSource:
            oSource.processor = oNew
            oSource.save()

        print(f"{count_updated} references to '{old_name}' have been copied to '{new_name}'.")
        print(
            f"If you have not already unregistered/deleted '{old_name}' from your code,"
            f" you may safely do so."
        )
