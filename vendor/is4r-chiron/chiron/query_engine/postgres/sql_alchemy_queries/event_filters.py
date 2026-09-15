import datetime

from sqlalchemy import and_


def get_where_clause_for_event_filter(criteria_set, start_column, end_column):
    """Turn the event filter on the criteria set into a SQL Alchemy where clause.

    Returns None if there is no event filter. Also returns None if the event filter type
    is "relative_to_other_event", that is handled specially as a longitudinal combo.
    """
    event_rule = criteria_set.get("event_rule", {}).get("type", "no_restriction")
    if event_rule == "date_range":
        return get_clause_for_date_range(criteria_set, start_column, end_column)
    elif event_rule == "age_in_days_range":
        return get_clause_for_age_in_days_range(criteria_set, start_column, end_column)
    elif event_rule == "interval_date_range":
        return get_clause_for_interval_date_range(criteria_set, start_column, end_column)
    elif event_rule == "interval_age_in_days_range":
        return get_clause_for_interval_age_in_days_range(criteria_set, start_column, end_column)
    elif event_rule == "relative_to_today":
        return get_clause_for_relative_to_today(criteria_set, start_column, end_column)
    elif event_rule == "interval_relative_to_today":
        return get_clause_for_interval_relative_to_today(criteria_set, start_column, end_column)
    return None


def get_clause_for_date_range(criteria_set, start_column, end_column):
    date_min = criteria_set.get("event_rule", {}).get("date_min")
    date_max = criteria_set.get("event_rule", {}).get("date_max")
    if date_min is not None and date_max is not None:
        return and_(start_column >= date_min, start_column <= date_max)
    elif date_min is not None:
        return start_column >= date_min
    elif date_max is not None:
        return start_column <= date_max
    return None


def get_clause_for_age_in_days_range(criteria_set, start_column, end_column):
    age_min = criteria_set.get("event_rule", {}).get("age_min")
    age_max = criteria_set.get("event_rule", {}).get("age_max")
    if age_min is not None and age_max is not None:
        return and_(start_column >= age_min, start_column <= age_max)
    elif age_min is not None:
        return start_column >= age_min
    elif age_max is not None:
        return start_column <= age_max
    return None


def get_clause_for_interval_date_range(criteria_set, start_column, end_column):
    date_start_min = criteria_set.get("event_rule", {}).get("date_start_min")
    date_start_max = criteria_set.get("event_rule", {}).get("date_start_max")
    date_end_min = criteria_set.get("event_rule", {}).get("date_end_min")
    date_end_max = criteria_set.get("event_rule", {}).get("date_end_max")
    rules = []
    if date_start_min is not None:
        rules.append(start_column >= date_start_min)
    if date_start_max is not None:
        rules.append(start_column <= date_start_max)
    if date_end_min is not None:
        rules.append(end_column >= date_end_min)
    if date_end_max is not None:
        rules.append(end_column <= date_end_max)
    if len(rules) == 0:
        return None
    if len(rules) == 1:
        return rules[0]
    return and_(*rules)


def get_clause_for_interval_age_in_days_range(criteria_set, start_column, end_column):
    age_start_min = criteria_set.get("event_rule", {}).get("age_start_min")
    age_start_max = criteria_set.get("event_rule", {}).get("age_start_max")
    age_end_min = criteria_set.get("event_rule", {}).get("age_end_min")
    age_end_max = criteria_set.get("event_rule", {}).get("age_end_max")
    rules = []
    if age_start_min is not None:
        rules.append(start_column >= age_start_min)
    if age_start_max is not None:
        rules.append(start_column <= age_start_max)
    if age_end_min is not None:
        rules.append(end_column >= age_end_min)
    if age_end_max is not None:
        rules.append(end_column <= age_end_max)
    if len(rules) == 0:
        return None
    if len(rules) == 1:
        return rules[0]
    return and_(*rules)


def get_clause_for_relative_to_today(criteria_set, start_column, end_column):
    days_ago = criteria_set.get("event_rule", {}).get("days_ago")
    start_date = datetime.date.today() - datetime.timedelta(days=days_ago)
    return start_column >= start_date


def get_clause_for_interval_relative_to_today(criteria_set, start_column, end_column):
    rules = []
    start_date_days_ago = criteria_set.get("event_rule", {}).get("start_date_days_ago")
    end_date_days_ago = criteria_set.get("event_rule", {}).get("end_date_days_ago")
    if start_date_days_ago is not None:
        start_date = datetime.date.today() - datetime.timedelta(days=start_date_days_ago)
        rules.append(start_column >= start_date)
    if end_date_days_ago is not None:
        end_date = datetime.date.today() - datetime.timedelta(days=end_date_days_ago)
        rules.append(end_column >= end_date)
    if len(rules) == 0:
        return None
    if len(rules) == 1:
        return rules[0]
    return and_(*rules)
