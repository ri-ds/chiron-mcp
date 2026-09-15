
/*
Posgres uses user-defined functions for many aggregation steps. All these functions should
be listed here.
*/





/* GENERIC FUNCTIONS */

create or replace function combine_json_arrays (json, json)
returns json language sql
as $$
	select case when $2 is not null then $1::jsonb || $2::jsonb else $1::jsonb end
$$;

create or replace function get_array_position(anyarray, int)
--fetch a single value out of an array at the specified position, base 1
returns anyelement language sql
as $$
	select ($1)[$2]
$$;

create or replace function get_array_position_reverse(anyarray, int)
returns anyelement language sql
as $$
	select ($1)[array_upper($1, 1) + 1 - $2]
$$;

create or replace function count_array_position(anyarray, int)
-- how many times does the value at specified array position appear in the array
returns bigint language sql
as $$
    select count(*)
	from unnest ($1) as element
	where element = (select ($1)[$2])
$$;

create or replace function count_array_position_reverse(anyarray, int)
-- how many times does the value at specified array position appear in the array
returns bigint language sql
as $$
    select count(*)
	from unnest ($1) as element
	where element = (select ($1)[array_upper($1, 1) + 1 - $2])
$$;

create or replace function json_arr_remove_duplicates (json)
--removes all duplicate values from the provided array
returns json language sql
as $$
	select jsonb_agg(distinct n)
	from jsonb_array_elements($1::jsonb) as t(n)
$$;

create or replace aggregate json_arr_set_to_json_arr (json) (
    sfunc = combine_json_arrays,
    stype = json,
	finalfunc = json_arr_remove_duplicates,
    initcond = '[]'
);

/* LIST DISTINCT AGGREGATION */

create or replace function json_arr_to_list_distinct (json)
returns text[] language sql
as $$
	select array(
		select distinct n->>'f1'
		from json_array_elements($1) as n
	    where n->>'f1' is not null
		order by n->>'f1'
	);
$$;

create or replace aggregate json_arr_set_to_list_distinct (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_distinct,
    stype = json,
    initcond = '[]'
);


/* LIST DISTINCT AGGREGATION FOR INTEGERS */

create or replace function json_arr_to_list_distinct_int (json)
-- takes query result 1 column integer of interest, returns bigint array of
-- distinct non-null values sorted asc by value
returns bigint[] language sql
as $$
	select array(
		select distinct (n->>'f1')::integer as "outval"
		from json_array_elements($1) as n
	    where n->>'f1' is not null
		order by "outval"
	);
$$;

create or replace aggregate json_arr_set_to_list_distinct_int (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_distinct_int,
    stype = json,
    initcond = '[]'
);

/* LIST DISTINCT AGGREGATION FOR FLOAT VALUES */

create or replace function json_arr_to_list_distinct_float (json)
-- takes query result 1 column double precision of interest, returns double precision array of
-- distinct non-null values sorted asc by value
returns double precision[] language sql
as $$
	select array(
		select distinct (n->>'f1')::double precision as "outval"
		from json_array_elements($1) as n
	    where n->>'f1' is not null
		order by "outval"
	);
$$;

create or replace aggregate json_arr_set_to_list_distinct_float (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_distinct_float,
    stype = json,
    initcond = '[]'
);

/* LIST DISTINCT AGGREGATION FOR BOOLEAN VALUES */

create or replace function json_arr_to_list_distinct_bool (json)
-- takes query result 1 column boolean of interest, returns boolean array of
-- distinct non-null values sorted asc by value
returns boolean[] language sql
as $$
	select array(
		select distinct (n->>'f1')::boolean as "outval"
		from json_array_elements($1) as n
	    where n->>'f1' is not null
		order by "outval"
	);
$$;

create or replace aggregate json_arr_set_to_list_distinct_bool (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_distinct_bool,
    stype = json,
    initcond = '[]'
);

/* LIST DISTINCT AGGREGATION FOR DATES */

create or replace function json_arr_to_list_distinct_date (json)
-- takes query result 1 column date of interest, returns date array of
-- distinct non-null values sorted asc by value
returns date[] language sql
as $$
	select array(
		select distinct (n->>'f1')::date as "outval"
		from json_array_elements($1) as n
	    where n->>'f1' is not null
		order by "outval"
	);
$$;

create or replace aggregate json_arr_set_to_list_distinct_date (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_distinct_date,
    stype = json,
    initcond = '[]'
);


/* COUNT DISTINCT AGGREGATION */

create or replace function json_arr_to_count_distinct (json)
-- takes query result 1 column of interest (any datatype), returns bigint count
-- of distinct, non-null values
returns bigint language sql
as $$
	select count(distinct n->>'f1')
		from json_array_elements($1) as n
        where n->>'f1' is not null
	;
$$;

create or replace aggregate json_arr_set_to_count_distinct (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_count_distinct,
    stype = json,
    initcond = '[]'
);


/* LIST ALL AGGREGATION */

-- takes a json array of id/value pairs as input
-- removes any dup id/value pairs and returns a sorted array of all values
-- ex: json_arr_to_list_all(json_agg(row(subject._id, subject."Id_ggqjjsyyws"))) AS "mylist"

create or replace function json_arr_to_list_all (json)
-- takes 2 column query result (collection ID, text value of interest)
-- for all distinct ID/value pairs (including nulls), sorts by text value and
-- returns array of just the text values
returns text[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", n->>'f2' as "concept_val"
			from json_array_elements($1) as n
			order by n->>'f2'
		) as mytable
	);
$$;

-- aggregate functions can perform same analysis on a set of json arrays
create or replace aggregate json_arr_set_to_list_all (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION FOR INTEGERS */

create or replace function json_arr_to_list_all_int (json)
-- takes 2 column query result (collection ID, integer value of interest)
-- for all distinct ID/value pairs (including nulls), sorts by integer value and
-- returns array of just the integer values
returns bigint[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::bigint as "concept_val"
			from json_array_elements($1) as n
			order by "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_int (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_int,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION FOR FLOAT VALUES */

create or replace function json_arr_to_list_all_float (json)
-- takes 2 column query result (collection ID, double precision value of interest)
-- for all distinct ID/value pairs (including nulls), sorts by double precision value and
-- returns array of just the double precision values
returns double precision[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::double precision as "concept_val"
			from json_array_elements($1) as n
			order by "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_float (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_float,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION FOR BOOLEAN VALUES */

create or replace function json_arr_to_list_all_bool (json)
-- takes 2 column query result (collection ID, boolean value of interest)
-- for all distinct ID/value pairs (including nulls), sorts by boolean value and
-- returns array of just the boolean values
returns boolean[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::boolean as "concept_val"
			from json_array_elements($1) as n
			order by "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_bool (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_bool,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION FOR DATES */

create or replace function json_arr_to_list_all_date (json)
-- takes 2 column query result (collection ID, date value of interest)
-- for all distinct ID/value pairs (including nulls), sorts by date value and
-- returns array of just the date values
returns date[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "concept_val"
			from json_array_elements($1) as n
			order by "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_date (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_date,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION CHRONOLOGICAL */

-- can also sort chronologically, in which case the age/date is also used
-- ex: json_agg(row(encounters_1._id, encounters_1.encounter_age, "lkp_ENCOUNTERCLASS_iwvghtjrwz_1"."ENCOUNTERCLASS_iwvghtjrwz"))

create or replace function json_arr_to_list_all_chron (json)
-- takes 3 column query result (collection ID, collection event date, text value of interest)
-- for all distinct ID/date/value groups, removes if event date is null; sorts by event date, text value;
-- returns array of just the text values of interest
returns text[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", n->>'f3' as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_chron (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_chron,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_by_age (json)
-- exactly like json_arr_to_list_all_chron except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns text[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", n->>'f3' as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_by_age (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_by_age,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION CHRONOLOGICAL FOR INTEGERS */

create or replace function json_arr_to_list_all_chron_int (json)
-- takes 3 column query result (collection ID, collection event date, integer value of interest)
-- for all distinct ID/date/value groups, removes if event date is null; sorts by event date, integer value;
-- returns array of just the integer values of interest
returns bigint[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", (n->>'f3')::bigint as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_chron_int (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_chron_int,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_by_age_int (json)
-- exactly like json_arr_to_list_all_chron_int except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns bigint[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", (n->>'f3')::bigint as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_by_age_int (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_by_age_int,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION CHRONOLOGICAL FOR FLOAT VALUES */

create or replace function json_arr_to_list_all_chron_float (json)
-- takes 3 column query result (collection ID, collection event date, double precision value of interest)
-- for all distinct ID/date/value groups, removes if event date is null; sorts by event date, double precision value;
-- returns array of just the double precision values of interest
returns double precision[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", (n->>'f3')::double precision as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_chron_float (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_chron_float,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_by_age_float (json)
-- exactly like json_arr_to_list_all_chron_float except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns double precision[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", (n->>'f3')::double precision as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_by_age_float (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_by_age_float,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION CHRONOLOGICAL FOR BOOLEAN VALUES */

create or replace function json_arr_to_list_all_chron_bool (json)
-- takes 3 column query result (collection ID, collection event date, boolean value of interest)
-- for all distinct ID/date/value groups, removes if event date is null; sorts by event date, boolean value;
-- returns array of just the boolean values of interest
returns boolean[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", (n->>'f3')::boolean as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_chron_bool (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_chron_bool,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_by_age_bool (json)
-- exactly like json_arr_to_list_all_chron_bool except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns boolean[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", (n->>'f3')::boolean as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_by_age_bool (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_by_age_bool,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION CHRONOLOGICAL FOR DATES */

create or replace function json_arr_to_list_all_chron_date (json)
-- takes 3 column query result (collection ID, collection event date, date value of interest)
-- for all distinct ID/date/value groups, removes if event date is null; sorts by event date, date value;
-- returns array of just the date values of interest
returns date[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", (n->>'f3')::date as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_chron_date (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_chron_date,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_by_age_date (json)
-- exactly like json_arr_to_list_all_chron_date except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns date[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", (n->>'f3')::date as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age", "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_by_age_date (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_by_age_date,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION REVERSE CHRONOLOGICAL */

-- can also sort chronologically, in which case the age/date is also used
-- ex: json_agg(row(encounters_1._id, encounters_1.encounter_age, "lkp_ENCOUNTERCLASS_iwvghtjrwz_1"."ENCOUNTERCLASS_iwvghtjrwz"))

create or replace function json_arr_to_list_all_rev_chron (json)
-- works exactly like json_arr_to_list_all_chron except sorts reverse chonological
returns text[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", n->>'f3' as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_chron (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_chron,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_rev_by_age (json)
-- exactly like json_arr_to_list_all_rev_chron except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns text[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", n->>'f3' as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_by_age (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_by_age,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION REVERSE CHRONOLOGICAL FOR INTEGERS */

create or replace function json_arr_to_list_all_rev_chron_int (json)
-- works exactly like json_arr_to_list_all_chron_int except sorts reverse chonological
returns bigint[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", (n->>'f3')::bigint as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_chron_int (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_chron_int,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_rev_by_age_int (json)
-- exactly like json_arr_to_list_all_rev_chron_int except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns bigint[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", (n->>'f3')::bigint as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_by_age_int (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_by_age_int,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION REVERSE CHRONOLOGICAL FOR FLOAT VALUES */

create or replace function json_arr_to_list_all_rev_chron_float (json)
-- works exactly like json_arr_to_list_all_chron_float except sorts reverse chonological
returns double precision[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", (n->>'f3')::double precision as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_chron_float (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_chron_float,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_rev_by_age_float (json)
-- exactly like json_arr_to_list_all_rev_chron_float except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns double precision[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", (n->>'f3')::double precision as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_by_age_float (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_by_age_float,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION REVERSE CHRONOLOGICAL FOR BOOLEAN VALUES */

create or replace function json_arr_to_list_all_rev_chron_bool (json)
-- works exactly like json_arr_to_list_all_chron_bool except sorts reverse chonological
returns boolean[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", (n->>'f3')::boolean as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_chron_bool (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_chron_bool,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_rev_by_age_bool (json)
-- exactly like json_arr_to_list_all_rev_chron_bool except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns boolean[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", (n->>'f3')::boolean as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_by_age_bool (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_by_age_bool,
    stype = json,
    initcond = '[]'
);

/* LIST ALL AGGREGATION REVERSE CHRONOLOGICAL FOR DATES */

create or replace function json_arr_to_list_all_rev_chron_date (json)
-- works exactly like json_arr_to_list_all_chron_date except sorts reverse chonological
returns date[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::date as "event_date", (n->>'f3')::date as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_date" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_chron_date (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_chron_date,
    stype = json,
    initcond = '[]'
);

create or replace function json_arr_to_list_all_rev_by_age_date (json)
-- exactly like json_arr_to_list_all_rev_chron_date except it expects an integer (age in days)
-- instead of a date for the collection event concept
returns date[] language sql
as $$
	select array(
		select mytable.concept_val
		from (
			select distinct n->>'f1' as "id_val", (n->>'f2')::integer as "event_age", (n->>'f3')::date as "concept_val"
			from json_array_elements($1) as n
	        where n->>'f2' is not null
			order by "event_age" DESC, "concept_val"
		) as mytable
	);
$$;

create or replace aggregate json_arr_set_to_list_all_rev_by_age_date (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_list_all_rev_by_age_date,
    stype = json,
    initcond = '[]'
);



/* COUNT ALL AGGREGATION */

create or replace function json_arr_to_count_all (json)
-- takes 2 column query result (collection ID, value of interest)
-- count distinct ID/value pairs, including nulls and returns as bigint
-- value of interest can be any datatype
returns bigint language sql
as $$
		select count(mytable.concept_val)
		from (
			select distinct n->>'f1' as "id_val", n->>'f2' as "concept_val"
			from json_array_elements($1) as n
		) as mytable;
$$;

create or replace aggregate json_arr_set_to_count_all (json) (
    sfunc = combine_json_arrays,
    finalfunc = json_arr_to_count_all,
    stype = json,
    initcond = '[]'
);

/* AVERAGE AGGREGATION */

create or replace function array_avg(anyarray)
returns numeric language sql
as
$$
    select avg(a)
    from unnest($1) as a
$$;

/* SUM AGGREGATION */

create or replace function array_sum(anyarray)
returns numeric language sql
as
$$
    select sum(a)
    from unnest($1) as a
$$;

/* STDDEV AGGREGATION */

create or replace function array_stddev(anyarray)
returns numeric language sql
as
$$
    select stddev(a)
    from unnest($1) as a
$$;

/*  MEDIAN AGGREGATION */

-- https://wiki.postgresql.org/wiki/Aggregate_Median
CREATE OR REPLACE FUNCTION _final_median(numeric[])
   RETURNS numeric AS
$$
   SELECT AVG(val)
   FROM (
     SELECT val
     FROM unnest($1) val
     ORDER BY 1
     LIMIT  2 - MOD(array_upper($1, 1), 2)
     OFFSET CEIL(array_upper($1, 1) / 2.0) - 1
   ) sub;
$$
LANGUAGE 'sql' IMMUTABLE;

-- https://wiki.postgresql.org/wiki/Aggregate_Median
CREATE OR REPLACE AGGREGATE median(numeric) (
  SFUNC=array_append,
  STYPE=numeric[],
  FINALFUNC=_final_median,
  INITCOND='{}'
);

create or replace function array_median(anyarray)
returns numeric language sql
as
$$
    select median(a::numeric)
    from unnest($1) as a
$$;

/* MIN AND MAX AGGREGATION */

create or replace function get_all_dates_for_value_at_position(json, int)
-- looks up a value in json array of id/date/value objects based on provided index
-- then finds all dates associated with that value and returns as a date array
returns date[] language sql
as $$
	select (array(
		select "occurence_date"::date
		from (
			select n->>'f2' as "occurence_date", n->>'f3' as "value"
			from json_array_elements($1) as n
			where n->>'f3' = get_array_position(
				array(
					SELECT n2->>'f3' as "value2"
					from json_array_elements($1) as n2
	                where n2->>'f3' is not null
					order by (n2->>'f3')::double precision
				), $2
			)
			and n->>'f2' is not null and n->>'f3' is not null
			order by n->>'f2'
		) as mytable
	))
$$;

create or replace function get_all_dates_for_value_at_position_reverse(json, int)
-- looks up a value in json array of id/date/value objects based on provided index
-- then finds all dates associated with that value and returns as a date array
returns date[] language sql
as $$
	select (array(
		select "occurence_date"::date
		from (
			select n->>'f2' as "occurence_date", n->>'f3' as "value"
			from json_array_elements($1) as n
			where n->>'f3' = get_array_position_reverse(
				array(
					SELECT n2->>'f3' as "value2"
					from json_array_elements($1) as n2
					where n2->>'f3' is not null
					order by (n2->>'f3')::double precision
				), $2
			)
			and n->>'f2' is not null and n->>'f3' is not null
			order by n->>'f2'
		) as mytable
	))
$$;

/* MOST FREQUENT VALUE AGGREGATION */

CREATE OR REPLACE FUNCTION array_frequency_values_and_counts(anyarray)
RETURNS text[] LANGUAGE SQL
AS $$
	select array(
		select concat('(', c, ') ', i::text)
		from (
			select i, count(*) c
			FROM (select unnest($1) i) i
			group by i
			order by c desc, i
		) foo
	);
$$;

CREATE OR REPLACE FUNCTION array_frequency_values(anyarray)
RETURNS anyarray LANGUAGE SQL
AS $$
	select array(
		select i
		from (
			select i, count(*) c
			FROM (select unnest($1) i) i
			group by i
			order by c desc, i
		) foo
	);
$$;

CREATE OR REPLACE FUNCTION array_frequency_counts(anyarray)
RETURNS bigint[] LANGUAGE SQL
AS $$
	select array(
		select c
		from (
			select i, count(*) c
			FROM (select unnest($1) i) i
			group by i
			order by c desc, i
		) foo
	);
$$;

/* HAS VALUE AGGREGATION */

create or replace function values_exist_in_array(text[], text[])
returns boolean language sql
as $$
	select exists(
		select element
		from unnest ($1) as element
		where element = ANY($2)
	);
$$;

create or replace function count_values_in_array(text[], text[])
returns bigint language sql
as $$
	select count(*)
	from unnest ($1) as element
	where element = ANY($2);
$$;

create or replace function get_dates_for_values_in_json_arr(json, text[])
-- takes 3 column query result (collection ID, collection event date, text value of interest)
-- and takes an array of strings
-- for all records, removes if text value doesn't match one of the strings or if event date is null
-- returns array of distinct event date values sorted by event date
returns date[] language sql
as $$
	select array(
		select distinct (n->>'f2')::date as "event_date"
		from json_array_elements($1) as n
		where n->>'f3' = ANY($2)
		and n->>'f2' is not null
		order by "event_date"
	);
$$;

create or replace function get_ages_for_values_in_json_arr(json, text[])
-- exact same as get_dates_for_values_in_json_arr, except expecting detailed age
-- for the collection event (i.e. integer representing age in days) instead of a date
returns integer[] language sql
as $$
	select array(
		select distinct (n->>'f2')::integer as "event_age"
		from json_array_elements($1) as n
		where n->>'f3' = ANY($2)
		and n->>'f2' is not null
		order by "event_age"
	);
$$;

create or replace function get_matching_values_in_json_arr_chron(json, text[])
-- takes 3 column query result (collection ID, collection event date, text value of interest)
-- and takes an array of strings
-- for all records, removes if text value doesn't match one of the strings or if event date is null
-- returns array of just the text values sorted by event date
returns text[] language sql
as $$
	select array(
		select n2."concept_value"
		from (
			select (n->>'f2')::date as "event_date", (n->>'f3')::text as "concept_value"
			from json_array_elements($1) as n
			where n->>'f3' = ANY($2)
			and n->>'f2' is not null
			order by "event_date"
		) n2
	);
$$;

create or replace function get_matching_values_in_json_arr_by_age(json, text[])
-- exact same as get_matching_values_in_json_arr_chron, except expecting detailed age
-- for the collection event (i.e. integer representing age in days) instead of a date
returns text[] language sql
as $$
	select array(
		select n2."concept_value"
		from (
			select (n->>'f2')::integer as "event_age", (n->>'f3')::text as "concept_value"
			from json_array_elements($1) as n
			where n->>'f3' = ANY($2)
			and n->>'f2' is not null
			order by "event_age"
		) n2
	);
$$;

create or replace function get_matching_values_in_json_arr_alphabetical(json, text[])
-- takes 3 column query result (collection ID, collection event date, text value of interest)
-- and takes an array of strings
-- for all records, removes if text value doesn't match one of the strings
-- returns array of distinct text values sorted by value
returns text[] language sql
as $$
	select array(
        select distinct (n->>'f3')::text as "concept_value"
        from json_array_elements($1) as n
        where n->>'f3' = ANY($2)
        order by "concept_value"
	);
$$;

create or replace function all_array_to_distinct(anyarray)
returns anyarray language sql
as $$
    select array(
        select distinct n
	    from unnest ($1) as n
	    order by n
    );
$$;





