import json

from .simple_clean import SimpleClean


class CleanStringWithWorkflow(SimpleClean):
    """
    Allows you to specify a series of steps for cleaning/manipulating the input value. The input
    doesn't have to be a string, but the output will always be a string (or None, or a list
    of strings).
    String values are always trimmed first regardless.
    """

    def __init__(self, workflow, convert_list_to_set=True):
        super().__init__("string", convert_list_to_set)
        self.workflow = workflow

    def describe_clean_process(self):
        return json.dumps(self.workflow)

    def clean_single_field(self, val):
        """
        Uses self.workflow as a guide to manipulate the input value.
        """
        val = super().clean_single_field(val)
        if val is None:
            return val
        # TODO: more scalable implementation, and what are other workflow steps?
        for step in self.workflow:
            if step == "upper":
                val = val.upper()
            if step == "lower":
                val = val.lower()
            if step == "remove_leading_zeros":
                val = val.lstrip("0")
        return val
