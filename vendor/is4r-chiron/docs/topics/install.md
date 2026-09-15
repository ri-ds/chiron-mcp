# Install Django and Chiron

Chiron is built as a Django app. You must have a basic familiarity with Python and the Django
framework. Chiron stores patient data in a research database separate from where the Django tables
are stored. Currently, the only supported RDBMS for the research database is PostgreSQL 15 or higher.

## Requirements


- You must have Python 3.
- You must have pip (and recommend using a virtual environment).
- You must have a relational database that Django can use (or use built-in sqlite3 database).
- You must have a PostgreSQL database for the research data.

## Step 1: Create or use an existing Django project

To create a new Django project:

```
pip install django
django-admin startproject myproject
```
    
## Step 2: Install the chiron app into your Django project

Install Chiron and its dependencies using pip:
```
pip install git+https://github.com/cchmc-bmi-os/chiron.git@develop#egg=chiron
```
    
In your settings.py file:
```
# add humanize, crispy_forms, and chiron to installed apps:

INSTALLED_APPS = [
   ...
   'django.contrib.humanize',
   'crispy_forms',
   'chiron',
   ...
]

# add chiron context processors
TEMPLATES[0]['OPTIONS']['context_processors'].append('chiron.context_processors.chiron_globals')

# for unsecured install on localhost:
CHIRON_SQL_ALCHEMY_CONNECTION_STRING = "postgresql://myuser:mypw@localhost:5432/mydatabase"

# (optional) Add chiron site title and Subject ID label
CHIRON_SITE_TITLE = 'Chiron Development'
```
	
	
In your urls.py:

```
# make sure you're importing 'include'
from django.urls import path, include

# add chiron to path list.
# example 1: put the chiron views inside a subdirectory 'chiron'
path('chiron/', include(('chiron.urls', 'chiron'), namespace='chiron')),

# example 2: put the chiron views directly at the root URL
path('', include(('chiron.urls', 'chiron'), namespace='chiron')),
...
```
	
(installing-ontology-app)=
## Step 2b: (optional) Install the ontology app

Starting with Chiron version 6.5.0, there is support for an ontology datatype for concepts. This datatype has special features that take advantage of the additional structure - such as hierarchical browsing.

The ontology datatype is optional, and by default Chiron will typically use a generic Text datatype for such fields. If you do wish to use it for your instance, here are the additional configuration requirements.

*WARNING 1:* You must already be using the new (React) Chiron UI. We will not be supporting ontology concepts in the old UI, and soon support for the old UI will go away altogether.

*WARNING 2:* The ontology-app uses the model field type Django ArrayField which requires Postgres. Postgres is already a requirement for Chiron, but up to now it has only been required for your research datasets, not the Django system tables. You must also use Postgres for the ontology-app tables - which you can do globally for your one Django database, or use a router to setup different databases for different Django apps.


**2b1. Install the ontology app in your Python environment.**

Follow the `README` instructions in the ontology-app repo:
[https://github.com/cchmc/is4r-chiron-ontology](https://github.com/cchmc/is4r-chiron-ontology)

**2b2. Configure your Django settings**

- Add to your INSTALLED APPS
```python

INSTALLED_APPS = [
    ...
    "ontologies",
    "chiron",
    ...
]
```

There is currently 1 new related Chiron setting. Review the {ref}`Chiron settings<chiron-settings-ontology>` and configure value as desired.

```python
CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT = False
```

**2b3. For any ontologies you plan to use, you will need to follow instructions in the ontology app documentation for loading ontologies.**

**2b4. Setup ontology concepts in the data dictionary.**

- By default, the Chiron autocreate tool usees generic Text fields for ontology values. You will need to manually edit concepts in the data dictionary.
- Change the Concept Handler to `OntologyHandler`.
- In your concept handler args
  - add `ontology_id` value as the ontology name (defined in your ontology app), such as "snomed".
  - You can also set `include_counts` to True or False. If True, there are more statistics provided in the query view, but this is slower. Turn it off if you have a large dataset or experience performance issues.



## Step 3: Add the Chiron & Django tables to the database

Although Chiron uses PostgreSQL to store your patient/research data, all other data related to 
Chiron configuration go into whichever relational database you're using for Django.

create Chiron database tables:
```
python manage.py migrate
```
	
## Step 4: Set up authentication

All Chiron views require the user to be logged into Django. Django comes with a wide variety of
authentication tools. However, a login view is not set up by default.

You should consider how you want to manage user login (local, LDAP, federated login, etc.) and
set up a custom login system for your specific needs. However, I will provide instructions here
for a quick, basic local login system for those who just want to get started.

First you need to make a login view template. Templates go inside apps, so we will create an app,
set up a template directory, and create our template as registration/login.html (the Django default)

```
python manage.py startapp main
cd main
mkdir templates
cd templates
mkdir registration
```

inside the registration folder, add a file ``login.html``:

```
{% extends 'chiron/core/base.html' %}

{% block title %}Login{% endblock %}

{% block content %}
<h2>Login</h2>
<form method="post">
{% csrf_token %}
{{ form.as_p }}
<button type="submit">Login</button>
</form>
{% endblock %}
```
	
Edit your urls.py file again to include the built-in Django authentication views:
```
...
path('accounts/', include('django.contrib.auth.urls')),
...
```
    
Create a superuser account:
```
python manage.py createsuperuser
```
    
Now you should be able to log in:

- Start the Django dev server:
```
python manage.py runserver
```

- Go to the URL you set up for chiron in step 2 (ex: ``http://localhost:8000/chiron``)

- Enter your user credentials

- You should now see a working version of Chiron with no data.
