
(understanding-event-collections)=
# Understanding Event Collections

Any {ref}`subcollection<collection-def>` can be turned into an event collection by specifying the date or age concept(s) that define when that event happened. For example, if you have a visit collection, you can specify the visit date as the event date.

**Event collections allow special types of temporal queries that aren't available for normal subcollections.** For example, a user can get all subjects who started taking warfarin within 2 months after a heart procedure. Or they can get all samples that were collected during an illness event. These queries are special because they are looking at relative dates/ages instead of absolutes dates/ages. It doesn't matter when a subject started taking warfarin, just that it was within 2 months after a heart procedure.

## Dates vs Ages

Event collections can either be defined using absolute dates or as age in days. Age in days is useful in systems where you don't want to store exact dates for data privacy reasons.

If your source data doesn't store age in days, Chiron has support for calculating that. The source for a detailed age can be a float value (where the fraction represents fraction of a year), age in days, or age calculated from a birthdate and event date.

Importantly, it's not possible to compare an age with a date. **Your entire Chiron system needs to either use all dates or all ages for defining event collections.** And you will specify which you want to use in your Chiron settings.

## Point Events vs Interval Events

Point events are events that occur on a single day, like an office visit. Interval events are events that can extend over multiple days, like a medical condition. Currently, the finest level of granularity in Chiron is one day. So an event that extends over multiple hours would still be considered a point event.

If a subcollection only defines a concept for the start date, it will be treated as a point event. If it also defines a concept for the end date, it will be treated like an interval event. This will affect the types of queries that can be performed on this event.

## Missing Dates

If an entry in an event collection is missing a start date (or end date for interval events), it will be excluded from any temporal queries.

## Getting Started with Event Collections

For a how-to guide, see {ref}`how-to-event-collections`.