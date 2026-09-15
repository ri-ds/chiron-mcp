from django.contrib import admin
from . import models


class SubjectAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.Subject, SubjectAdmin)


class OneToManyCollectionAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.OneToManyCollection, OneToManyCollectionAdmin)


class SecondOneToManyCollectionAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.SecondOneToManyCollection, SecondOneToManyCollectionAdmin)


class OneToOneCollectionAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.OneToOneCollection, OneToOneCollectionAdmin)


class ReverseOneToOneCollectionAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.ReverseOneToOneCollection, ReverseOneToOneCollectionAdmin)


class ManyToManyCollectionAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.ManyToManyCollection, ManyToManyCollectionAdmin)


class ReverseManyToManyCollectionAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.ReverseManyToManyCollection, ReverseManyToManyCollectionAdmin)


class SubCollectionAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.SubCollection, SubCollectionAdmin)


class ManyToManySubCollectionAdmin(admin.ModelAdmin):
    list_display = [
        "m2m_id_field",
        "m2m_category_field",
        "m2m_sometimes_field",
        "m2m_text_field",
        "m2m_date_field",
        "m2m_integer_field",
        "m2m_float_field",
        "m2m_boolean_field",
        "m2m_integer_category_field",
        "m2m_float_category_field",
    ]


admin.site.register(models.ManyToManySubCollection, ManyToManySubCollectionAdmin)


class SampleAdmin(admin.ModelAdmin):
    list_display = ["sample_id", "subject_id"]


admin.site.register(models.Sample, SampleAdmin)


class FileAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.File, FileAdmin)


class SubColComplexSubjectMatchingAdmin(admin.ModelAdmin):
    list_display = ["alt_subject_id", "submatch_text_field"]


admin.site.register(models.SubColComplexSubjectMatching, SubColComplexSubjectMatchingAdmin)


class AltSubjectAdmin(admin.ModelAdmin):
    list_display = ["alt_subject_id2"]


admin.site.register(models.AltSubject, AltSubjectAdmin)


class M2MSubColComplexSubjectMatchingAdmin(admin.ModelAdmin):
    list_display = ["m2m_alt_text_field"]


admin.site.register(models.M2MSubColComplexSubjectMatching, M2MSubColComplexSubjectMatchingAdmin)
