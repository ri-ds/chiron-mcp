from chiron.processors.abstract import DisplayProcessor


class DisplaySubjectHyperlink(DisplayProcessor):
    """
    Shows the Subject ID with a link to the Subject Details tab.
    """

    def _custom_display_value_method(self, value, output_type):
        """returns a value to be used in an output file
        output type could be 'html', 'csv', etc.
        available output types will likely expand over time
        """
        if value is None:
            return ""
        if output_type == "html":
            link = ""
            # if settings.FORCE_SCRIPT_NAME:
            #     link += settings.FORCE_SCRIPT_NAME[1:]

            link += "single_subject_timeline?concept={}&value={}".format(
                self.concept.get_full_database_field_name(), value
            )
            return {
                "link": link,
                "value": str(value),
            }
            # return '<a href="{}">{}</a>'.format(link, str(value))
        return str(value)

    def set_display_function(self):
        self.display_function = self._custom_display_value_method

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "ID"
