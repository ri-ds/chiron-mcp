(admin-views)=
# Admin Views

The built-in Chiron UI has a variety of views for admin users to help with managing the 
data dictionary and troubleshooting problems.

Even if you don't use the built-in UI for your production site, it is good to have it available
for you as a site admin. Most of these utilities are only available through the UI and don't have
corresponding API endpoints.

Admin views are available for all Django Staff users (`Users.is_staff=True` or 
`Users.is_superuser=True`). From the Chiron site, click your username in the top right corner
to access these views.

<strong>NOTE: These views bypass normal data access rules and should not be made
available to standard users.</strong>

## The Django Admin

Chiron makes extensive use of Django's built-in admin views. You can view and modify most Chiron models
here. This is a much more user-friendly way to access your data than trying to access the database
directly.

## ETL Logs

```{eval-rst}
.. autofunction:: chiron.views.views_backend.etl_logs
```

## Query Troubleshooting

```{eval-rst}
.. autofunction:: chiron.views.views_backend.query_troubleshooting
```

## User Report

```{eval-rst}
.. autofunction:: chiron.views.views_backend.user_report
```




