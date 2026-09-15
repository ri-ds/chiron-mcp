from django.contrib import admin

from chiron import models
from chiron.forms import django_admin_forms


class EtlLogAdmin(admin.ModelAdmin):
    list_display = ("dataset", "status", "start_date", "end_date")
    list_filter = ("dataset",)


admin.site.register(models.EtlLog, EtlLogAdmin)


class SourceEtlLogAdmin(admin.ModelAdmin):
    list_display = (
        "etl_log",
        "source",
        "destination_collection",
        "load_start_date",
        "load_end_date",
    )


admin.site.register(models.SourceEtlLog, SourceEtlLogAdmin)


class SourceRecordEtlLogAdmin(admin.ModelAdmin):
    list_display = (
        "source_log",
        "subject_id",
        "subject_created",
    )


admin.site.register(models.SourceRecordEtlLog, SourceRecordEtlLogAdmin)


class ConceptIssueEtlLogAdmin(admin.ModelAdmin):
    list_display = (
        "source_log",
        "concept_id",
        "issue",
        "count",
    )


admin.site.register(models.ConceptIssueEtlLog, ConceptIssueEtlLogAdmin)


class ConceptIssueExampleEtlLogAdmin(admin.ModelAdmin):
    list_display = (
        "concept_issue",
        "input_datatype",
        "input_value",
        "stored_datatype",
        "stored_value",
    )


admin.site.register(models.ConceptIssueExampleEtlLog, ConceptIssueExampleEtlLogAdmin)


class DefaultTableDefConceptAdmin(admin.StackedInline):  # can also use TabularInline
    model = models.DefaultTableDefConcept
    autocomplete_fields = ("concept",)
    extra = 1


class DefaultPermissionGroupAdmin(admin.StackedInline):  # can also use TabularInline
    model = models.DefaultPermissionGroup
    extra = 1


class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "unique_id",
        "display_name",
        "database_name",
        "get_actual_database_name",
        "root_collection",
        "autocreate_chiron_user",
    )
    autocomplete_fields = ("root_collection",)
    inlines = [DefaultTableDefConceptAdmin, DefaultPermissionGroupAdmin]


admin.site.register(models.Dataset, DatasetAdmin)


class ProjectAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.Project, ProjectAdmin)


class ContentSharingAdmin(admin.TabularInline):
    model = models.ContentSharing
    autocomplete_fields = ("chironuser",)
    extra = 3


class UserCreatedContentAdmin(admin.ModelAdmin):
    list_display = ("name", "dataset", "created", "creator", "type", "get_sharing_description")
    list_filter = ("dataset",)
    autocomplete_fields = ("creator",)
    inlines = [ContentSharingAdmin]


admin.site.register(models.UserCreatedContent, UserCreatedContentAdmin)


class CohortDefSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "chironuser",
        "created",
    )
    autocomplete_fields = ("chironuser",)


admin.site.register(models.CohortDefSnapshot, CohortDefSnapshotAdmin)


class AnalysisDefSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "chironuser",
        "created",
    )
    autocomplete_fields = ("chironuser",)


admin.site.register(models.AnalysisDefSnapshot, AnalysisDefSnapshotAdmin)


class TableDefSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "chironuser",
        "created",
    )
    autocomplete_fields = ("chironuser",)


admin.site.register(models.TableDefSnapshot, TableDefSnapshotAdmin)


class ProcessorAdmin(admin.ModelAdmin):
    save_as = True
    list_display = (
        "name",
        "python_path",
        "required_args",
        "optional_args",
        "is_custom",
        "is_source_processor",
        "is_etl_processor",
        "is_cohort_def_processor",
        "is_display_processor",
        "is_permission_processor",
        "is_source_processor",
    )
    list_filter = (
        "is_source_processor",
        "is_etl_processor",
        "is_cohort_def_processor",
        "is_display_processor",
        "is_permission_processor",
        "is_source_processor",
    )


admin.site.register(models.Processor, ProcessorAdmin)


class ConceptHandlerAdmin(admin.ModelAdmin):
    search_fields = ("name",)


admin.site.register(models.ConceptHandler, ConceptHandlerAdmin)


class ProcessorHandlerComboAdmin(admin.ModelAdmin):
    list_display = ("id", "processor", "handler")


admin.site.register(models.ProcessorHandlerCombo, ProcessorHandlerComboAdmin)


class ChironUserAdmin(admin.ModelAdmin):
    form = django_admin_forms.ChironUserForm
    list_display = (
        "user",
        "dataset",
        "access_level",
        "list_permission_groups",
    )
    list_filter = ("dataset",)
    autocomplete_fields = ("user",)
    search_fields = (
        "user__first_name",
        "user__last_name",
    )


admin.site.register(models.ChironUser, ChironUserAdmin)


class PermissionGroupAdmin(admin.ModelAdmin):
    form = django_admin_forms.PermissionGroupForm
    list_display = (
        "name",
        "allow_all_subjects_override",
        "concept_for_allowed_subjects",
        "list_allowed_concepts",
        "list_allowed_data_categories",
    )
    autocomplete_fields = ("concept_for_allowed_subjects",)


admin.site.register(models.PermissionGroup, PermissionGroupAdmin)


class CollectionAdmin(admin.ModelAdmin):
    form = django_admin_forms.CollectionForm
    save_on_top = True
    save_as = True
    list_display = (
        "permanent_id",
        "dataset",
        "name",
        "is_root_collection",
        "many_to_many_with_subject",
        "event_id_field",
        "event_name_field",
        "event_date_field",
        "event_end_date_field",
    )
    list_filter = ("dataset",)
    autocomplete_fields = (
        "event_id_field",
        "event_name_field",
        "event_date_field",
        "event_end_date_field",
    )
    search_fields = (
        "permanent_id",
        "name",
    )


admin.site.register(models.Collection, CollectionAdmin)


class CollectionRelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "pk_concept",
        "fk_concept",
    )
    list_filter = ("pk_concept__collection__dataset",)

    autocomplete_fields = (
        "pk_concept",
        "fk_concept",
    )


admin.site.register(models.CollectionRelationship, CollectionRelationshipAdmin)


class SourceProcessorArgAdmin(admin.TabularInline):
    model = models.SourceProcessorArg
    extra = 0


class SourceSourceDependencyAdmin(admin.TabularInline):
    form = django_admin_forms.SourceSourceDependencyForm
    model = models.SourceSourceDependency
    extra = 0
    fk_name = "source"
    autocomplete_fields = ("depends_on_source",)


class SourceAdmin(admin.ModelAdmin):
    save_on_top = True
    save_as = True
    list_display = (
        "name",
        "collection",
        "count_concepts",
        "exclude_from_etl",
        "execution_order",
        "get_dependencies",
        "processor",
        "get_relevant_subject_ids",
    )
    list_filter = ("collection__dataset",)
    list_editable = (
        "exclude_from_etl",
        "execution_order",
    )
    search_fields = ("name",)
    inlines = [SourceProcessorArgAdmin, SourceSourceDependencyAdmin]


admin.site.register(models.Source, SourceAdmin)


class CategoryAdmin(admin.ModelAdmin):
    form = django_admin_forms.CategoryForm
    list_display = (
        "unique_id",
        "dataset",
        "name",
        "parent",
        "order",
        "get_top_level_parent",
    )
    list_filter = ("dataset",)
    list_editable = ("name", "parent", "order")
    search_fields = (
        "unique_id",
        "name",
    )
    autocomplete_fields = ("parent",)


admin.site.register(models.Category, CategoryAdmin)


class ConceptHandlerArgAdmin(admin.TabularInline):
    model = models.ConceptHandlerArg
    extra = 0


class ConceptConceptDependencyAdmin(admin.TabularInline):
    form = django_admin_forms.ConceptConceptDependencyForm
    model = models.ConceptConceptDependency
    extra = 0
    fk_name = "concept"
    autocomplete_fields = ("depends_on_concept",)


class ConceptSourceDependencyAdmin(admin.TabularInline):
    form = django_admin_forms.ConceptSourceDependencyForm
    model = models.ConceptSourceDependency
    extra = 0
    fk_name = "concept"
    autocomplete_fields = ("depends_on_source",)


class ConceptAdmin(admin.ModelAdmin):
    form = django_admin_forms.ConceptForm
    save_on_top = True
    save_as = True
    list_display = (
        "permanent_id",
        "published",
        "has_phi",
        "name",
        "order",
        "collection",
        "source",
    )
    list_filter = (
        "collection__dataset",
        "published",
        "has_phi",
        "collection",
        "source",
        "category",
        "concept_handler",
    )
    list_editable = (
        "published",
        "has_phi",
        "name",
        "order",
    )
    search_fields = (
        "permanent_id",
        "name",
    )
    autocomplete_fields = (
        "source",
        "collection",
        "concept_handler",
        "category",
        "concept_for_prefilter",
    )
    inlines = [ConceptHandlerArgAdmin, ConceptConceptDependencyAdmin, ConceptSourceDependencyAdmin]


admin.site.register(models.Concept, ConceptAdmin)


class AutocreatedFieldAdmin(admin.ModelAdmin):
    list_display = (
        "dataset",
        "app",
        "model",
        "unique_source_id",
        "field",
        "associated_concept",
        "created",
    )
    list_filter = (
        "dataset",
        "app",
        "model",
        "unique_source_id",
    )
    autocomplete_fields = ["associated_concept"]


admin.site.register(models.AutocreatedField, AutocreatedFieldAdmin)


class CachedCohortAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "subject_permission_hash", "cohort_def_hash", "count")
    list_filter = ("dataset",)


admin.site.register(models.CachedCohort, CachedCohortAdmin)


class CachedConceptStatsAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "subject_permission_hash", "cohort_def_hash", "concept_id")
    list_filter = ("dataset",)


admin.site.register(models.CachedConceptStats, CachedConceptStatsAdmin)
