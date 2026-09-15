from chiron import query_definition as qdef
from chiron.chiron_settings import CHIRON_DATABASE


def get_display_values(report, chironuser, cohort, table, output_type="html"):
    """Convert a raw query result into a final report with correct data types."""
    display_class = Display(cohort, table)
    new_report = []
    for record in report:
        values = display_class.get_display_values3(record, output_type)
        # new_record = []
        # for field in record:
        #     new_record.append(str(field))
        new_report.append(values)
    return new_report


class Display:
    """
    Contains tools to modify values in a dataset for displaying
    """

    def __init__(self, cohort, table):
        self.cohort = cohort
        self.table = table
        # self.extended_table_def = extended_table_def
        self.display_processors = {}
        self.preprocess()

    def preprocess(self):
        """
        Do some calculations here to save time when processing records
        """
        field_data = {}
        for entry in self.table.internal_table_def["fields"]:
            data_for_field = {}
            oConcept = entry["concept"]
            aggregation_criteria_set = entry.get("aggregation_criteria_set")
            available_criteria_sets = qdef.get_all_criteria_set_ids_for_collection_id(
                self.cohort.cohort_def, oConcept.collection.permanent_id
            )
            if aggregation_criteria_set not in available_criteria_sets:
                aggregation_criteria_set = None
            data_for_field["aggregation_criteria_set"] = aggregation_criteria_set
            field_data[entry["entry_id"]] = data_for_field
        self.field_data = field_data

        self.map_value_functions = {}
        if CHIRON_DATABASE == "postgres":
            for entry in self.table.internal_table_def["fields"]:
                if entry.get("categorize"):
                    display_processor = entry["processor"]
                    map_func = display_processor.sql_alchemy_map_after_query
                    self.map_value_functions[entry["entry_id"]] = map_func

        display_value_functions = {}
        for entry in self.table.internal_table_def["fields"]:
            display_processor = entry["processor"]
            display_func = display_processor.get_display_value3
            display_value_functions[entry["entry_id"]] = display_func
        self.display_value_functions = display_value_functions

    def get_display_values3(self, record, output_type="html"):
        values = []
        for idx, entry in enumerate(self.table.internal_table_def["fields"]):
            val = record[idx]
            if entry["entry_id"] in self.map_value_functions:
                map_func = self.map_value_functions[entry["entry_id"]]
                val = map_func(val)
            display_func = self.display_value_functions[entry["entry_id"]]
            val = display_func(val, output_type)
            values.append(val)
        return values

    def get_aggregated_report(self, chironuser, record):
        values = []
        for entry in self.table.internal_table_def["fields"]:
            concept_id = entry["concept_id"]
            entry_id = entry["entry_id"]
            collection_id = entry["collection"]["collection_id"]
            if concept_id is None:
                values.append("[error]")
                continue
            field_name = collection_id + "_agg" if entry.get("aggregate", False) else concept_id
            if field_name not in record:
                values.append(None)
                continue
            if not entry.get("aggregate", False):
                values.append(record[field_name])
                continue
            # aggregate field
            display_processor = entry["processor"]
            data_to_aggregate = record[field_name]
            aggregation_criteria_set = self.field_data[entry_id].get("aggregation_criteria_set")
            if aggregation_criteria_set:
                data_to_aggregate = [
                    x
                    for x in data_to_aggregate
                    if aggregation_criteria_set in x.get("_criteria_sets", [])
                ]
            val = display_processor.calculate_aggregate_value(data_to_aggregate)
            values.append(val)
        return values
