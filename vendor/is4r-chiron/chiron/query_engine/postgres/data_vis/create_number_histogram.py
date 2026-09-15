import math

from chiron.helpers import round_sig_3


def get_histogram_bins(value_count, min_val, max_val, is_integer=False, number_is_year=False):
    """
    Returns an array of bin_label and bin_index (starting from 1) pairs

    :param min_val:
    :param max_val:
    :param number_is_year:
    :return:
    """
    if number_is_year:
        is_integer = True
    bin_count = get_bin_count(value_count)
    # for integers bin size should never go below 1
    if is_integer and bin_count > (max_val - min_val):
        bin_count = max_val - min_val
    bin_limits = get_histogram_bin_limits(bin_count, min_val, max_val)
    use_scientific_notation = determine_use_scientific_notation(min_val, max_val)
    histogram_data = []
    is_first_iteration = True
    for index, hist_bin in enumerate(bin_limits):
        if is_first_iteration:
            bin_min = hist_bin
            is_first_iteration = False
            continue
        bin_max = hist_bin
        bin_min_label = number_to_string(bin_min, number_is_year, use_scientific_notation)
        bin_max_label = number_to_string(bin_max, number_is_year, use_scientific_notation)
        bin_label = "[{} - {})".format(bin_min_label, bin_max_label)
        histogram_data.append([bin_label, index])
        bin_min = hist_bin
    histogram_data[-1][0] = histogram_data[-1][0].replace(")", "]")
    return bin_limits, histogram_data


def number_to_string(value, number_is_year, use_scientific_notation=False):
    if number_is_year:
        return str(int(value))
    if use_scientific_notation:
        string_value = "{:.2e}".format(value)
    else:
        string_value = format(round_sig_3(value), ",")
    return string_value


def determine_use_scientific_notation(min_val, max_val):
    """
    Determine if scientific notation should be used for the histogram.
    """
    if min_val != 0:
        if abs(min_val) < 0.0001:
            return True
    if max_val != 0:
        if abs(max_val) < 0.0001:
            return True
    if abs(min_val) > 9_999_999 or abs(max_val) > 9_999_999:
        return True
    return False


def get_bin_count(value_count):
    return math.ceil(math.sqrt(value_count))


def get_histogram_bin_limits(bin_count, min_val, max_val):
    """
    Returns an array with all bin limits. Will contain one more value than the number of bins.

    :param min:
    :param max:
    :param is_integer:
    :return:
    """
    if min_val == max_val:
        return [min_val, min_val + 0.00001]
    min_val = round_sig_3(min_val, rounding_method=math.floor)
    max_val = round_sig_3(max_val, rounding_method=math.ceil)
    value_range = max_val - min_val
    bin_size = value_range / bin_count
    bins = []
    cutoff = min_val
    for i in range(bin_count):
        bins.append(round_sig_3(cutoff))
        cutoff = cutoff + bin_size
    bins.append(max_val + 0.00001)  # make sure the last value gets included
    return bins


def get_histogram_bins_old(value_count, min_val, max_val, is_integer=False, number_is_year=False):
    """
    Returns an array of bin_label and bin_index (starting from 1) pairs

    :param min_val:
    :param max_val:
    :param number_is_year:
    :return:
    """
    if number_is_year:
        is_integer = True
    bin_limits = get_histogram_bin_limits_old(min_val, max_val, is_integer=is_integer)
    histogram_data = []
    is_first_iteration = True
    for index, hist_bin in enumerate(bin_limits):
        if is_first_iteration:
            bin_min = hist_bin
            is_first_iteration = False
            continue
        bin_max = hist_bin
        bin_min_label = str(bin_min)
        if bin_min_label.endswith(".0"):
            bin_min_label = bin_min_label[:-2]
        bin_max_label = str(bin_max)
        if bin_max_label.endswith(".0"):
            bin_max_label = bin_max_label[:-2]
        if number_is_year:
            bin_label = bin_min_label
        else:
            bin_label = "[{},{})".format(bin_min_label, bin_max_label)
        histogram_data.append([bin_label, index])
        bin_min = hist_bin
    return bin_limits, histogram_data


def get_histogram_bin_limits_old(min, max, is_integer=False):
    """
    Returns an array with all bin limits. Will contain one more value than the number of bins.

    :param min:
    :param max:
    :param is_integer:
    :return:
    """
    range = max - min
    bin_size, rounding_position = get_bin_size_old(range)
    if is_integer and bin_size < 1:
        bin_size = 1
        rounding_position = 1
    bins = []
    cutoff = float(int(min / bin_size) * bin_size)  # round bin cutoffs to appropriate number
    while cutoff <= max:
        bins.append(cutoff)
        cutoff = round(cutoff + bin_size, rounding_position)
    bins.append(cutoff)
    return bins


def get_bin_size_old(range):
    """
    Returns the bin size and number of digits to use in the python round() function based on the
    provided range (difference between min and max values). Will generate a bin size that gives
    11 to 100 total bins.
    """
    if range > 10000000:
        return (1000000, 1)
    if range > 1000000:
        return (100000, 1)
    if range > 100000:
        return (10000, 1)
    if range > 10000:
        return (1000, 1)
    if range > 1000:
        return (100, 1)
    if range > 100:
        return (10, 1)
    if range > 10:
        return (1, 1)
    if range > 1:
        return (0.1, 2)
    if range > 0.1:
        return (0.01, 3)
    if range > 0.01:
        return (0.001, 4)
    if range > 0.001:
        return (0.0001, 5)
    return (1, 1)
