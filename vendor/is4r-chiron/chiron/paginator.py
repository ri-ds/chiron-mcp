import math


class ReportPaginator:
    def __init__(self, limit, page=1):
        self.limit = int(limit)
        self.page = int(page)

    def set_collection_count(self, collection_count):
        """Should be set as soon as possible, but doesn't need to be set on init."""
        self.collection_count = int(collection_count)

    #         if self.get_skip_value() > self.collection_count:
    #             raise IndexError("Page number does not exist.")

    def get_skip_value(self):
        skip = (self.page - 1) * self.limit
        return skip

    def get_max_page_number(self):
        return math.ceil(self.collection_count / self.limit)

    def get_first_index_of_page(self):
        return self.get_skip_value() + 1

    def get_last_index_of_page(self):
        calculated_index = self.get_skip_value() + self.limit
        if self.collection_count < calculated_index:
            return self.collection_count
        return calculated_index

    def has_previous(self):
        return True if self.page > 1 else False

    def has_next(self):
        return True if self.page < self.get_max_page_number() else False

    def get_previous_page_number(self):
        if not self.has_previous():
            return None
        return self.page - 1

    def get_next_page_number(self):
        if not self.has_next():
            return None
        return self.page + 1

    def go_to_previous_page(self):
        if not self.has_previous():
            raise IndexError("Paginator already on first page")
        self.page -= 1

    def go_to_next_page(self):
        if not self.has_next():
            raise IndexError("Paginator already on last page")
        self.page += 1

    def go_to_first_page(self):
        self.page = 1

    def go_to_last_page(self):
        self.page = self.get_max_page_number()

    def json(self):
        return {
            "first_index": self.get_first_index_of_page(),
            "last_index": self.get_last_index_of_page(),
            "current_page": self.page,
            "previous_page": self.get_previous_page_number(),
            "next_page": self.get_next_page_number(),
            "last_page": self.get_max_page_number(),
            "total_records": self.collection_count,
        }
