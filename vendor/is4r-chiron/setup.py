from setuptools import find_packages, setup

setup(
    name="chiron",
    version="6.5.4",
    description="Chiron source",
    url="https://github.com/cchmc-is4r-dev/chiron.git",
    author="John Meinken",
    author_email="john.meinken@cchmc.org",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "django",
        "djangorestframework",
        "django-crispy-forms",
        "psycopg2-binary",
        "SQLAlchemy",
        "requests",
        "pandas",
        "natsort",
        "python-dateutil",
        "unicodecsv",
        "numpy",
    ],
    extras_require={
        "ontologies": [
            "ontologies @ git+https://github.com/cchmc/is4r-chiron-ontology.git@v1.0.0#egg=ontologies",
        ],
    },
)
