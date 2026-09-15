from chiron.helpers import age_in_days_to_years_days


def get_histogram_bins(min_val, max_val):
    hist_bins = get_histogram_bin_limits(min_val, max_val)
    histogram_data = []
    is_first_iteration = True
    for index, hist_bin in enumerate(hist_bins):
        if is_first_iteration:
            bin_min = hist_bin
            is_first_iteration = False
            continue
        bin_max = hist_bin
        if max_val - min_val > 3650:
            bin_label = age_in_days_to_label(bin_min)
        if max_val - min_val <= 100:
            bin_label = age_in_days_to_label(bin_min)
        else:
            bin_min_label = age_in_days_to_label(bin_min)
            bin_max_label = age_in_days_to_label(bin_max)
            bin_label = "{} - {}".format(bin_min_label, bin_max_label)
        histogram_data.append([bin_label, index])
        bin_min = hist_bin
    return histogram_data


def age_in_days_to_label(age_in_days):
    years, days = age_in_days_to_years_days(age_in_days)
    if years == 0 and days == 0:
        return "0"
    if years == 0:
        return f"{days}d"
    if days == 0:
        return f"{years}y"
    if days == 91 or days == 92:
        return f"{years}.25y"
    if days == 182 or days == 183:
        return f"{years}.5y"
    if days == 273 or days == 274:
        return f"{years}.75y"
    return f"{years}y,{days}d"


def get_bin_size(range):
    if range > 3650:
        return 365.25
    if range > 1000:
        return 365.25 / 4
    if range > 100:
        return 10
    return 1


def get_histogram_bin_limits(min, max, is_integer=False):
    # if min < 0:
    #    min = 0
    range = max - min
    bin_size = get_bin_size(range)
    bins = []
    cutoff = float(int(min / bin_size) * bin_size)
    while cutoff <= max:
        bins.append(cutoff)
        cutoff = cutoff + bin_size
    bins.append(cutoff)
    return bins
