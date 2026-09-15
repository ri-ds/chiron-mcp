from chiron.query_definition import analysis_def_functions as adfuncs


class Analysis:
    """
    Represents a table of aggregated data in the analysis view.
    """

    def __init__(self, chironuser, analysis_def=None):
        if analysis_def is None:
            ad_info = adfuncs.clean_active_analysis_def(chironuser, include_metadata=True)
        else:
            ad_info = adfuncs.clean_analysis_def(analysis_def, chironuser, include_metadata=True)
        self.analysis_def = ad_info["analysis_def"]
        self.extended_analysis_def = ad_info["extended_analysis_def"]
        self.errors = ad_info["errors"]
        self.warnings = ad_info["warnings"]
