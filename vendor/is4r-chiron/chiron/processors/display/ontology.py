from chiron.processors.display.text import DisplayText


class DisplayOntology(DisplayText):
    """
    Used for ontology datatype. This is a complex datatype that integrates with the ontology
    django app.
    """

    def use_subvalue(self, td_entry):
        """Should a subvalue be used for this table def entry.

        Currently just using the label. Eventually want to give users the option to select
        what display value they want to see - especially people should be able to see the
        ontology code or a concatenation of the code and label.
        """
        return "label"
