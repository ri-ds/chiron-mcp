from chiron.processors.abstract import EtlProcessor


class EtlName(EtlProcessor):
    """
    display full name but sort by last name
    """

    def pull_record_data_from_source(self, record):
        val = str(record.get("NAME", ""))
        last = val.split(" ")[-1]
        response = {
            "value": val,
            "sort": last,
        }
        return response


class EtlEncCostAsString(EtlProcessor):
    """
    Store as text but sort as string
    """

    def pull_record_data_from_source(self, record):
        val = record.get("BASE_ENCOUNTER_COST", "")
        if val is None or val == "":
            return None
        response = {
            "value": str(val),
            "sort": round(float(val)),
        }
        return response


class EtlLabCodeCustomSort(EtlProcessor):
    """
    Sorting by code length
    """

    def pull_record_data_from_source(self, record):
        val = record.get("VALUE", "")
        if val is None or val == "":
            return None
        response = {
            "value": str(val),
            "sort": len(str(val)),
        }
        return response
