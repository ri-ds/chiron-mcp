from datetime import datetime, timedelta


def get_histogram_bins(min_date, max_date):
    """
    Returns an array with all bin limits as date strings. Will contain one more value than the
    number of bins.

    :param min_date:
    :param max_date:
    :return:
    """
    hist_type = get_date_histogram_type(min_date, max_date)
    hist_bins = get_histogram_bin_limits(min_date, max_date)
    histogram_data = []
    for index, hist_bin in enumerate(hist_bins[:-1], 1):
        if hist_type == "yearly":
            bin_label = hist_bin.strftime("%Y")
        else:
            bin_label = hist_bin.strftime("%b %Y")
        histogram_data.append([bin_label, index])
    return histogram_data


def get_histogram_bin_limits(min, max):
    histogram_type = get_date_histogram_type(min, max)
    if histogram_type == "yearly":
        return get_histogram_bins_yearly(min, max)
    else:
        return get_histogram_bins_monthly(min, max)


def get_date_histogram_type(min_date, max_date):
    """
    yearly or monthly
    """
    diff = max_date - min_date
    if diff > timedelta(days=1461):  # about 4 years
        return "yearly"
    return "monthly"


def get_histogram_bins_monthly(min, max):
    min_bin = datetime(min.year, min.month, 1)
    if max.month == 12:
        max_bin = datetime(max.year + 1, 1, 1)
    else:
        max_bin = datetime(max.year, max.month + 1, 1)
    bins = []
    while min_bin <= max_bin:
        bins.append(min_bin)
        if min_bin.month == 12:
            min_bin = datetime(min_bin.year + 1, 1, 1)
        else:
            min_bin = datetime(min_bin.year, min_bin.month + 1, 1)
    return bins


def get_histogram_bins_yearly(min, max):
    min_bin = datetime(min.year, 1, 1)
    max_bin = datetime(max.year + 1, 1, 1)
    bins = []
    while min_bin <= max_bin:
        bins.append(min_bin)
        min_bin = datetime(min_bin.year + 1, 1, 1)
    return bins
