import importlib
import copy
import sys

from django.core.management.base import BaseCommand

from chiron import chiron_settings


def autocreate_command_line_selection(source_list_names, allow_all=False):
    """
    Source lists are stored in a dictionary. This will take a list of dictionary keys and prompt
    the user to make a selection.

    :param source_list_names: The full dict of source lists
    :type source_list_names: list of strings
    :param allow_all: Will allow the user to select "all" as an option
    :type allow_all: boolean
    :return: list of selected source list names
    """
    if len(source_list_names) == 1:
        return source_list_names
    allowed_ids = []
    print_lines = ["SELECT A SOURCE LIST TO USE"]
    if allow_all:
        allowed_ids.append("all")
        print_lines.append("all : Run this command for all source lists")
    for idx, source_list_name in enumerate(source_list_names):
        allowed_ids.append(str(idx))
        print_lines.append(f"{idx} : {source_list_name}")
    for line in print_lines:
        print(line)
    selection = input("Enter the dataset id or 'exit' to quit: ")
    if selection == "exit":
        sys.exit()
    if selection not in allowed_ids:
        selection = autocreate_command_line_selection(source_list_names, allow_all)
    if allow_all and selection == "all":
        return source_list_names
    return [source_list_names[int(selection)]]


class Command(BaseCommand):
    """
    Reads a dict of user-defined source lists to autocreate entries in the data dictionary. On
    rerun, it will update with new fields but ignore previously autocreated fields.

    :--test-run: Don't make changes to the database

    """

    help = "Autocreates the data dictionary using autocreate lists"

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
        parser.add_argument(
            "source_list",
            nargs="*",
            help="Only run the specified source list. Leave blank to be prompted to select.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Don't prompt to select a source list and run all instead.",
        )
        # will be run as a test until --finalize argument is passed
        parser.add_argument(
            "--test-run",
            action="store_true",
            help="Don't make changes to the database",
        )

    def handle(self, *args, **options):
        # get the source lists
        source_lists_path = chiron_settings.CHIRON_AUTOCREATE_SOURCE_LISTS
        mod_path, attr_name = source_lists_path.rsplit(".", 1)
        mod = importlib.import_module(mod_path)
        source_lists = getattr(mod, attr_name)

        # filter which source list(s) to run based on user selection
        if options["all"] and options["source_list"]:
            print("Either specify the source lists you want or set --all, don't do both.")
            print("Autocreation was not run.")
            return
        elif options["source_list"]:
            new_source_lists = {}
            for source_list_name in options["source_list"]:
                if source_list_name not in source_lists:
                    print(f"The source list '{source_list_name}' was not found.")
                    print("Run the command with no args to be prompted to select a source list")
                    print("Autocreation was not run.")
                    return
                new_source_lists[source_list_name] = source_lists[source_list_name]
            source_lists = new_source_lists
        elif not options["all"]:
            source_list_names = list(source_lists.keys())
            selected_source_list_names = autocreate_command_line_selection(
                source_list_names, allow_all=True
            )
            new_source_lists = {}
            for source_list_name in selected_source_list_names:
                new_source_lists[source_list_name] = source_lists[source_list_name]
            source_lists = new_source_lists

        # run through the whole setup once to test for any errors
        new_field_count = 0
        new_field_count_by_source = {}
        for list_id in source_lists.keys():
            new_field_count_by_source[list_id] = 0
        for list_id, source_list_entry in source_lists.items():
            autocreate_tool = source_list_entry["autocreate_tool"]
            defaults = source_list_entry.get("defaults", {})
            for i, source_entry in enumerate(source_list_entry["list"]):
                complete_entry = copy.copy(defaults)
                # this will merge the entry with default values, giving higher priority to what's
                # defined in the entry
                complete_entry.update(source_entry)
                tool = autocreate_tool(complete_entry)
                field_names = tool.get_field_names()
                concepts = tool.get_concepts(field_names)
                new_field_count += tool.count_concepts(concepts)
                new_field_count_by_source[list_id] += tool.count_concepts(concepts)

        for source_name, count in new_field_count_by_source.items():
            print(f"found {count} new fields to autocreate in '{source_name}'")

        # repeat same process but save at the end
        if new_field_count > 0 and not options.get("test_run"):
            for list_id, source_list_entry in source_lists.items():
                autocreate_tool = source_list_entry["autocreate_tool"]
                defaults = source_list_entry.get("defaults", {})
                for i, source_entry in enumerate(source_list_entry["list"]):
                    complete_entry = copy.copy(defaults)
                    complete_entry.update(source_entry)
                    tool = autocreate_tool(complete_entry)
                    field_names = tool.get_field_names()
                    concepts = tool.get_concepts(field_names)
                    tool.save_concepts(concepts)
            print("data dictionary autocreation complete")
        else:
            print("No new fields were discovered. Autocreation was not run.")
