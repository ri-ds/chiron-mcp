from django.db import models

# these models will be used to test joining over django relationships during the ETL

# to make data changes:
# these models are available in the django admin for test_project
# python manage.py dumpdata patient_models --indent=4
# put it in chiron/test_project/patient_model_data.json


class Subject(models.Model):
    subject_field = models.CharField(max_length=10, blank=True, null=True)
    # alterative subject IDs are used to test more complex subject matching situations
    current_age = models.FloatField(blank=True, null=True)
    alt_subject_id1 = models.CharField(max_length=30, blank=True, null=True)
    alt_subject_id2 = models.IntegerField(blank=True, null=True)
    one_to_one = models.OneToOneField(
        "ReverseOneToOneCollection", on_delete=models.SET_NULL, blank=True, null=True
    )
    many_to_many = models.ManyToManyField("ReverseManyToManyCollection", blank=True)

    def __str__(self):
        return self.subject_field


class Sample(models.Model):
    """
    Used to test subcollection relationships in combination with m2m subcollection. This is a
    1:m with subject and a m:m with files.
    """

    subject = models.ForeignKey("Subject", on_delete=models.SET_NULL, blank=True, null=True)
    sample_id = models.CharField(max_length=20)

    def __str__(self):
        return self.sample_id


class File(models.Model):
    """
    Used to test subcollection relationships in combination with m2m subcollection. This is a
    m:m with Subject and a m:m with Sample.
    """

    subjects = models.ManyToManyField("Subject")
    samples = models.ManyToManyField("Sample")
    file_id = models.CharField(max_length=20)

    def __str__(self):
        return self.file_id


class OneToManyCollection(models.Model):
    subject = models.ForeignKey("Subject", on_delete=models.SET_NULL, blank=True, null=True)
    one_to_many_field = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.one_to_many_field


class SecondOneToManyCollection(models.Model):
    parent = models.ForeignKey(
        "OneToManyCollection", on_delete=models.SET_NULL, blank=True, null=True
    )
    second_one_to_many_field = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.second_one_to_many_field


class OneToOneCollection(models.Model):
    subject = models.OneToOneField("Subject", on_delete=models.SET_NULL, blank=True, null=True)
    one_to_one_field = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.one_to_one_field


class ReverseOneToOneCollection(models.Model):
    reverse_one_to_one_field = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.reverse_one_to_one_field


class ManyToManyCollection(models.Model):
    subject = models.ManyToManyField("Subject", blank=True)
    many_to_many_field = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.many_to_many_field


class ReverseManyToManyCollection(models.Model):
    reverse_many_to_many_field = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.reverse_many_to_many_field


# this model will test loading a subcollection
class SubCollection(models.Model):
    subject = models.ForeignKey("Subject", on_delete=models.SET_NULL, blank=True, null=True)
    category_field = models.CharField(max_length=10, blank=True, null=True)
    text_field = models.TextField(blank=True, null=True)
    date_field = models.DateField(blank=True, null=True)
    integer_field = models.IntegerField(blank=True, null=True)
    float_field = models.FloatField(blank=True, null=True)
    boolean_field = models.BooleanField(null=True, default=False)

    def __str__(self):
        return self.category_field


class ManyToManySubCollection(models.Model):
    """
    Use to build a Chiron subcollection that will have a M2M relationship with subjects.
    """

    m2m_subjects = models.ManyToManyField("Subject", blank=True)
    # field is always unique, never null
    m2m_id_field = models.CharField(max_length=10, blank=True, null=True)
    # field is a category, never null
    m2m_category_field = models.CharField(max_length=10, blank=True, null=True)
    # mix of null and not null
    m2m_sometimes_field = models.CharField(max_length=10, blank=True, null=True)

    # for testing different chiron datatype options
    m2m_text_field = models.TextField(blank=True, null=True)
    m2m_date_field = models.DateField(blank=True, null=True)
    m2m_integer_field = models.IntegerField(blank=True, null=True)
    m2m_float_field = models.FloatField(blank=True, null=True)
    m2m_boolean_field = models.BooleanField(null=True, default=False)
    m2m_integer_category_field = models.CharField(max_length=10, blank=True, null=True)
    m2m_float_category_field = models.CharField(max_length=10, blank=True, null=True)


class SubColComplexSubjectMatching(models.Model):
    """
    Uses an alternative subject ID to link to subject
    """

    alt_subject_id = models.CharField(max_length=30, blank=True, null=True)
    submatch_text_field = models.TextField(blank=True, null=True)


class AltSubject(models.Model):
    """Subject IDs for testing many to many complex subject matching"""

    alt_subject_id2 = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.alt_subject_id2)


class M2MSubColComplexSubjectMatching(models.Model):
    """
    for testing many to many complex subject matching
    """

    m2m_alt_subjects = models.ManyToManyField("AltSubject", blank=True)
    m2m_alt_text_field = models.TextField(blank=True, null=True)
