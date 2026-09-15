from abc import ABCMeta, abstractmethod


class CleanValue:
    """
    Used to manipulate an input value into the desired output value.
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        self._warnings = []
        """
        A list of tuples with structure (input_value, warning_message)

        The clean method generally should avoid raising errors when it encounters data issues.
        Instead, it should handle the issue (for example, by returning None instead) and store
        info about data issues in self._warnings.
        """

    def _add_warning(self, value, warning):
        """
        Pass the relevant input value and the warning about it
        """
        self._warnings.append((value, warning))

    def get_warnings(self):
        """
        Returns list of warning messages and resets the list
        """
        response = self._warnings
        self._warnings = []
        return response

    def describe_clean_process(self):
        """
        Describe in non-technical terms how the input value is modified.
        """
        raise NotImplementedError(
            "abstract method CleanValue.describe_clean_process() is not defined"
        )

    @abstractmethod
    def clean(self, input):
        """
        Takes a raw input value and returns a cleaned/modified value.
        """
        raise NotImplementedError("abstract method CleanValue.clean() is not defined")
