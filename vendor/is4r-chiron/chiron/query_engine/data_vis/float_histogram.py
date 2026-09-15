import math

from chiron import chiron_settings
from chiron.helpers import round_sig_3


# TODO: Build an abstract histogram class based on this class that can be used for
#  any type of histogram, then use that class to build an AgeHistogram and DateHistogram.
#  These classes will replace all the code in `chiron.query_engine.postgres.data_vis`.
class FloatHistogram:
    """Object to help build a histogram on a numeric concept."""

    def __init__(self, value_count, min_val, max_val):
        self.value_count = value_count
        self.bin_count = self.get_bin_count()
        self.data_min_val = min_val
        self.data_max_val = max_val
        # The histogram uses rounded values when reasonable. We need to first estimate the
        # size of our bins to make sure we don't round too aggressively.
        estimated_bin_size = (max_val - min_val) / self.bin_count
        try:
            min_num_decimals = 1 - math.floor(math.log10(estimated_bin_size))
        except ValueError:
            # log10 of zero is undefined
            min_num_decimals = None
        # The histogram min/max values come from the actual min/max values of the data, but may
        # be rounded to make the histogram more readable.
        self.histogram_min_val = round_sig_3(
            min_val, rounding_method=math.floor, min_num_decimals=min_num_decimals
        )
        self.histogram_max_val = round_sig_3(
            max_val, rounding_method=math.ceil, min_num_decimals=min_num_decimals
        )
        self.bin_cutoffs = self.get_bin_cutoffs()
        self.use_k = self.determine_use_k()
        self.use_scientific_notation = self.determine_use_scientific_notation()

    def get_bin_cutoffs(self):
        """The bin cutoffs are a flat list of values that designate all bin min/max values
        There will be one more bin cutoff than there are bins.
        """
        # special case: if only one unique data value, return a single bin
        if self.data_min_val == self.data_max_val:
            return [self.histogram_min_val, self.histogram_max_val]
        # normal case
        value_range = self.histogram_max_val - self.histogram_min_val
        bin_size = value_range / self.bin_count
        min_num_decimals = 1 - math.floor(math.log10(bin_size))
        bin_cutoffs = []
        cutoff = self.histogram_min_val
        for i in range(self.bin_count):
            bin_cutoffs.append(round_sig_3(cutoff, min_num_decimals=min_num_decimals))
            cutoff = cutoff + bin_size
        bin_cutoffs.append(self.histogram_max_val)
        return bin_cutoffs

    def get_bins(self):
        """Return a list of dicts with information about each histogram bin. Each dict contains:

        * min_cutoff (float) - the minimum cutoff value
        * min_inclusive (bool) - whether the minimum cutoff is included in the bin
        * max_cutoff (float) - the maximum cutoff value
        * max_inclusive (bool) - whether the maximum cutoff is included in the bin
        * label (str) - a suggested label for the bin
        """
        histogram_bins = []
        is_first_iteration = True
        for cutoff in self.bin_cutoffs:
            if is_first_iteration:
                bin_min = cutoff
                is_first_iteration = False
                continue
            bin_max = cutoff
            histogram_bin = {
                "min_cutoff": bin_min,
                "min_inclusive": True,
                "max_cutoff": bin_max,
                "max_inclusive": False,
            }
            histogram_bin["label"] = self.make_bin_label(**histogram_bin)
            histogram_bins.append(histogram_bin)
            bin_min = cutoff
        # redo the last bin to make it inclusive of the max value
        del histogram_bins[-1]["label"]
        histogram_bins[-1]["max_inclusive"] = True
        histogram_bins[-1]["label"] = self.make_bin_label(**histogram_bin)
        return histogram_bins

    def get_bin_count(self):
        """This is the square-root choice algorithm."""
        bin_count = math.ceil(math.sqrt(self.value_count))
        return (
            bin_count
            if bin_count < chiron_settings.CHIRON_MAX_HISTOGRAM_BINS
            else chiron_settings.CHIRON_MAX_HISTOGRAM_BINS
        )

    def make_bin_label(self, min_cutoff, min_inclusive, max_cutoff, max_inclusive):
        min_label = self.number_to_string(min_cutoff)
        max_label = self.number_to_string(max_cutoff)
        if min_inclusive:
            min_label = "[" + min_label
        else:
            min_label = "(" + min_label
        if max_inclusive:
            max_label = max_label + "]"
        else:
            max_label = max_label + ")"
        return min_label + " - " + max_label

    def make_bin_label_for_years(self, min_cutoff, min_inclusive, max_cutoff, max_inclusive):
        if not min_inclusive:
            min_cutoff += 1
        if not max_inclusive:
            max_cutoff -= 1
        min_label = self.number_to_string(min_cutoff)
        max_label = self.number_to_string(max_cutoff)
        return min_label + " - " + max_label

    def number_to_string(self, value):
        if self.use_k:
            if value == 0:
                return "0"
            if value >= 100_000:
                return "{:.0f}k".format(value / 1000)
            if value >= 10_000:
                return "{:.1f}k".format(value / 1000)
            else:
                return "{:.2f}k".format(value / 1000)
        elif self.use_scientific_notation:
            return "{:.2e}".format(value)
        # default to regular number formatting
        if isinstance(value, float) and value.is_integer():
            return format(int(value), ",")
        return format(value, ",")

    def determine_use_k(self):
        """Determine if the histogram should be displayed in thousands."""
        if abs(self.histogram_min_val) < 1000 or abs(self.histogram_min_val) > 999_999:
            return False
        if abs(self.histogram_min_val) < 1000 or abs(self.histogram_min_val) > 999_999:
            return False
        return True

    def determine_use_scientific_notation(self):
        """
        Determine if scientific notation should be used for the histogram.
        """
        if self.histogram_min_val != 0:
            if abs(self.histogram_min_val) < 0.01:
                return True
        if self.histogram_max_val != 0:
            if abs(self.histogram_max_val) < 0.01:
                return True
        if abs(self.histogram_min_val) >= 1_000_000 or abs(self.histogram_max_val) >= 1_000_000:
            return True
        return False
