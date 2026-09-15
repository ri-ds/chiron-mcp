import importlib

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.apps import apps

# from django.core.exceptions import ValidationError

from chiron import chiron_settings


# def _raise_validation_error(msg, exclude=None, field_name=None):
#     """
#     Handles associating error with field that may not be present on form.
#     Or just pass message for error at form level.
#     """
#     if not field_name:
#         raise ValidationError(msg)
#     if exclude and field_name in exclude:
#         raise ValidationError(msg)
#     raise ValidationError({field_name: msg})


#  ABSTRACT MODELS ###################################################################


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ######################################################################################


class Dataset(models.Model):
    """
    A related group of data collections all sharing the same subject (root) collection.
    """

    class AccessLevel(models.TextChoices):
        PHI = "phi", "phi - view all subject details including PHI"
        DEID = "deid", "deid - view subject details excluding PHI"
        AGG = "agg", "agg - only aggregated data like subject count"

    class InfobarType(models.TextChoices):
        INFO = "info", "info"
        WARNING = "warning", "warning"
        DANGER = "danger", "danger"

    unique_id = models.SlugField(max_length=60, unique=True)
    """ A unique ID to identify this dataset; alphanumeric, dashes and hyphens """
    display_name = models.CharField(max_length=120, unique=True)
    """ A display name for this dataset. """
    database_name = models.SlugField(
        max_length=30,
        unique=True,
        help_text="The name of the database or data schema to store this dataset. "
        "If settings.CHIRON_POSTGRES_SCHEMA_NAME_PREPEND, there will be a prefix.",
    )
    """ Each dataset is stored in its own separate database or schema. """
    description = models.TextField(blank=True, null=True)
    """ An optional description for users """
    root_collection = models.ForeignKey(
        "Collection",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="is_root_for_datasets",
    )
    """ The root collection (also called subject collection) represents the core thing you're
    collecting data about - typically a patient or study subject.
    Each dataset should have one and only one subject (root) collection """

    subject_id_fields_to_index = models.TextField(
        default="id",
        blank=True,
        null=True,
        help_text="enter as a comma separated list, don't need quotes",
    )
    """ The main collection has an _ids object field that can be used to match source records to
    existing subjects. This is the list of field names you are using inside _ids, and will be
    used to create indexes to speed up the ETL.

    Enter as a comma-separated list like "id,mrn,blinded_id"
    """

    autocreate_chiron_user = models.BooleanField(
        default=False,
        help_text="Automatically create a new chiron user when a Django users tries to access "
        "this dataset.",
    )
    """ If a new Django user tries to access this dataset, should they be allowed to with
        default permissions?
    """
    auto_access_level = models.CharField(
        max_length=4,
        choices=AccessLevel.choices,
        default=AccessLevel.DEID,
        help_text="The 'access_level' to set for autocreated chiron users",
    )
    """ The access level that will be set for an autocreated chironuser """
    auto_can_view_workspace = models.BooleanField(
        default=True,
        help_text="The 'can_view_workspace' value to set for autocreated chiron users",
    )
    """ The 'can_view_workspace' value that will be set for an autocreated chironuser """
    auto_can_view_subject_details = models.BooleanField(
        default=True,
        help_text="The 'can_view_subject_details' to set for autocreated chiron users",
    )
    """ The 'can_view_subject_details' value that will be set for an autocreated chironuser """
    list_visible = models.BooleanField(
        default=True,
        help_text="""Whether dataset is visible in the api v2 dataset list view for logged
                     in chironuser
                """,
    )
    """ If a chiron user doesnt exist and autocreate is false, do we include it in 
        the dataset list view
    """
    contact_email = models.EmailField(
        blank=True,
        help_text="the email to reach out to for requesting access to this dataset",
    )
    """ If this is not set, then the react ui shows a disabled button with
        'you do not have access'
    """
    override_site_title = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text="overrides chiron_settings.CHIRON_SITE_TITLE for this dataset",
    )
    """ overrides chiron_settings.CHIRON_SITE_TITLE for this dataset """
    override_footer_template = models.TextField(
        blank=True,
        null=True,
        help_text="overrides chiron_settings.CHIRON_FOOTER_TEMPLATE for this dataset",
    )
    """ overrides chiron_settings.CHIRON_FOOTER_TEMPLATE for this dataset """
    override_data_summary_function_path = models.TextField(
        blank=True,
        null=True,
        help_text="overrides chiron_settings.CHIRON_DATA_SUMMARY_FUNCTION_PATH for this dataset",
    )
    """ overrides chiron_settings.CHIRON_DATA_SUMMARY_FUNCTION_PATH for this dataset """
    override_infobar = models.TextField(
        blank=True,
        null=True,
        help_text="overrides chiron_settings.CHIRON_INFOBAR for this dataset",
    )
    """ overrides chiron_settings.CHIRON_INFOBAR for this dataset """
    override_infobar_type = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        choices=InfobarType.choices,
        help_text="overrides chiron_settings.CHIRON_INFOBAR_TYPE for this dataset",
    )
    """ overrides chiron_settings.CHIRON_INFOBAR_TYPE for this dataset """
    logo_url = models.URLField(
        blank=True,
        null=True,
        help_text="optional image url to use as the logo for this dataset",
    )
    """ optional image url to use as the logo for this dataset """
    extra_header_links = models.JSONField(
        blank=True,
        null=True,
        help_text="extra links to show in the header for this dataset. format is a json object with header text as key and url as value",
    )
    """ extra links to show in the header for this dataset """

    def __str__(self):
        return self.unique_id

    def subcollections(self):
        """
        Returns all collections in this dataset that are not the root collection
        """
        qCollection = self.collection_set.all().exclude(id=self.root_collection_id)
        return qCollection

    def get_actual_database_name(self):
        """
        Returns the actual name of the database or schema for this dataset.
        """
        prefix = chiron_settings.CHIRON_POSTGRES_SCHEMA_NAME_PREPEND
        if prefix:
            return f"{prefix}_{self.database_name}"
        return self.database_name


class DefaultTableDefConcept(models.Model):
    """
    The specified concepts will show up as default fields in the results table. These fields can
    still be removed by the user.
    """

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    """ The dataset to use """
    concept = models.ForeignKey(
        "Concept",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        limit_choices_to={"published": True},
    )
    """ The concept to include in empty table defs by default """


class DefaultPermissionGroup(models.Model):
    """
    The specified PermissionGroups will be applied to new chironusers autocreated by the system.
    If Dataset.autocreate_chiron_user is False for the associated dataset, this will never be used.
    """

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    """ The dataset to use """
    permission_group = models.ForeignKey("PermissionGroup", on_delete=models.CASCADE)
    """ The permission group to apply to autocreated users """


class SourceManager(models.Manager):
    def accessible(self, dataset):
        """
        Returns source that are accessible based on the dataset and other settings
        """
        return self.filter(collection__dataset=dataset, exclude_from_etl=False)


class Source(models.Model):
    name = models.CharField(max_length=120)
    """ A display name for this source. """
    collection = models.ForeignKey("Collection", on_delete=models.PROTECT)
    """ The table this data will be loaded into. """
    processor = models.ForeignKey(
        "Processor",
        on_delete=models.PROTECT,
        limit_choices_to={"is_source_processor": True},
    )
    """ The source processor that handles fetching the dataset during the ETL """
    execution_order = models.IntegerField(default=100)
    """ Sources will be loaded during the ETL from lowest to highest execution_order.
    Sometimes a source can depend on a previous step so the load order matters."""
    exclude_from_etl = models.BooleanField(default=False)
    """ Skip loading this source during the ETL. """

    class Meta:
        ordering = ["collection__dataset__unique_id", "execution_order"]

    objects = SourceManager()

    def save(self, *args, **kwargs):
        super(Source, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.collection.dataset.unique_id}::{self.name}"

    def get_dataset(self):
        return self.collection.dataset

    def get_relevant_subject_ids(self):
        """
        When a source is loaded, the source processor matches each source record to the
        corresponding subject using a subject ID. Some projects may have multiple subject IDs
        """
        processor = self.get_processor()
        response = ""
        match_ids = processor.get_subject_id_fields_used_for_matching()
        if match_ids:
            if isinstance(match_ids, list):
                match_ids = ", ".join(match_ids)
            response += match_ids

        add_ids = processor.get_subject_id_fields_added()
        if add_ids:
            response += "\n(added: "
            if isinstance(add_ids, list):
                add_ids = ", ".join(add_ids)
            response += add_ids
            response += ")"
        return response

    def count_concepts(self):
        """How many concepts are associated with this source?"""
        return self.concept_set.all().count()

    def get_processor(self):
        args = self._get_processor_args()
        # for args, pass self (this source followed by any other args)
        processor = self.processor.instantiate(self, **args)
        return processor

    def check_source_format(self):
        """
        Wrapper for SourceProcessor.check_source_format()
        """
        processor = self.get_processor()
        if processor:
            return processor.check_source_format()
        return None

    def get_source_dependency_order(self):
        """
        Returns a list of sources that need to be loaded before this source in order for
        loading.
        """
        print("sources ", self.get_dependencies())
        # get all the names of the self and dependent sources
        dependencies = self.get_dependencies()
        dependencies += ", " + self.name

        print("dependencies", dependencies)
        sources = Source.objects.filter(name__in=dependencies).order_by("execution_order")
        return sources

    def get_dependencies(self):
        """
        What sources need to be loaded before this source? Based on SourceSource/ConceptSource/
        ConceptConceptDependency models
        """
        # any sources directly referenced by this source
        sources = self.depends_on_sources.all().values_list("depends_on_source__name", flat=True)
        sources = list(sources)
        # any sources referenced by a concept belonging to this source
        for oDep in ConceptSourceDependency.objects.filter(concept__source=self):
            sources.append(oDep.depends_on_source.name)
        # sources for any concepts referenced by a concept belonging to this source
        for oDep in ConceptConceptDependency.objects.filter(concept__source=self):
            sources.append(oDep.depends_on_concept.source.name)
        sources = list(set(sources))
        return ", ".join(sources)

    def _get_processor_args(self):
        qArgs = self.sourceprocessorarg_set.all()
        response = {}
        for oArg in qArgs:
            response[oArg.name] = oArg.value
        return response


class CollectionManager(models.Manager):
    def accessible(self, dataset):
        """
        Returns sources that are accessible based on the dataset and other settings
        """
        return self.filter(dataset=dataset)

    def subcollections(self, dataset):
        return self.filter(dataset=dataset, is_root_for_datasets__isnull=True)


class Collection(models.Model):
    """Defines a collection of related concepts that will go in the same database table.

    Every project has a subject collection that represents a subject and is the foundation for
    how data is stored and queried. Any concept that is 1:1 with a subject can be associated
    with the subject collection.

    Then there can be any number of other collections where each subject can have multiple
    subcollections. For example, you could have a Sample collection to store concept data
    about samples that are associated with a subject.
    """

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    """ The dataset this collection is associated with """
    permanent_id = models.SlugField(max_length=120)
    """ The unique ID that will be used to reference this collection in things like saved report
    definitions. It's important that this ID doesn't change in a production system. """
    name = models.CharField(max_length=120)
    """ The display name for this collection. """
    name_plural = models.CharField(max_length=120, null=True, blank=True)
    """ If not set, name + 's' will be used. """
    many_to_many_with_subject = models.BooleanField(default=False)
    """ One collection record can be associated with multiple subjects. """
    collection_id_is_integer = models.BooleanField(
        default=False,
        help_text="Possible values are integer (checked) or string (unchecked)",
    )
    """ DEPRECATED: Not currently being used and will likely be removed in a future version. """
    event_id_field = models.ForeignKey(
        "Concept",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="collection_event_id",
        help_text=(
            "A concept that can uniquely identify a collection record",
            "(required for root collection).",
        ),
        limit_choices_to={"published": True},
    )
    """ Specify a concept that can be used to uniquely identify a record. This is required
        for the root (subject) collection and optional for other collections.
    """
    event_name_field = models.ForeignKey(
        "Concept",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="collection_event_name",
        help_text=("A concept that can be used to label a record. It doesn't have to be unique."),
        limit_choices_to={"published": True},
    )
    """ Optionally specify a concept that can be used as a display name for a record. """
    event_date_field = models.ForeignKey(
        "Concept",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="collection_event_date",
        help_text="Turn this concept into an event by specifying the event date concept.",
        limit_choices_to={"published": True},
    )
    """ Optionally specify a start date for a record; allows for longitudinal queries. """
    event_end_date_field = models.ForeignKey(
        "Concept",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="collection_event_end_date",
        help_text="For events that last over a period of time, specify an end date concept.",
        limit_choices_to={"published": True},
    )
    """ Optionally specify an end date for a record; allows for longitudinal queries. Use for
    events that can take place over multiple days. Leave empty for events that always take place
    within a single day. """

    objects = CollectionManager()

    class Meta:
        unique_together = (
            ("dataset", "permanent_id"),
            ("dataset", "name"),
        )
        ordering = ["dataset__unique_id", "permanent_id"]

    def __str__(self):
        return "{}::{}".format(self.dataset.unique_id, self.permanent_id)

    # def clean_fields(self, exclude=None):
    #     concept_fields = [
    #         "event_id_field",
    #         "event_name_field",
    #         "event_date_field",
    #         "event_end_date_field",
    #     ]
    #     for field in concept_fields:
    #         # must be associated with same dataset as parent
    #         if getattr(self, field) and getattr(self, field).collection != self:
    #             msg = "The concept must belong to this collection."
    #             _raise_validation_error(msg, exclude, field)

    @property
    def is_root_collection(self):
        return self == self.dataset.root_collection

    def get_name_plural(self):
        return self.name_plural if self.name_plural else "{}s".format(self.name)

    def instantiate(self, oConcept, extra_args):
        # instantiate the object in self.processor with args
        mod_name, klass_name = self.python_path.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        Klass = getattr(mod, klass_name)
        processor = Klass(oConcept, **extra_args)
        return processor

    def get_event_type(self):
        if not self.event_date_field:
            return None
        return "interval" if self.event_end_date_field else "point"

    def check_event_permission_group(self, chironuser):
        """
        returns True if can view both start and end date for event, else false
        (also need to check PHI)
        """
        if self.get_event_type() == "point":
            return self.event_date_field.check_permission_group(chironuser)
        elif self.get_event_type() == "interval":
            e1 = self.event_date_field.check_permission_group(chironuser)
            e2 = self.event_end_date_field.check_permission_group(chironuser)
            result = True if e1 and e2 else False
            return result
        return False

    def check_event_user_access_level(self, chironuser):
        """
        What access permissions does the user have to the underlying date concept(s)?
        None - user is not allowed to access the concepts and so cannot perform event queries
        "deid" - user can perform event queries but must be rounded to year
        "normal" - user can access full dates for queries
        """
        if self.get_event_type() == "point":
            can_view, reason = self.event_date_field.user_can_view_concept_stats(chironuser)
            if not can_view:
                return None
            if (
                self.event_date_field.has_phi
                and not chironuser.access_level == chironuser.AccessLevel.PHI
            ):
                return "deid"
            return "normal"
        elif self.get_event_type() == "interval":
            can_view1, reason1 = self.event_date_field.user_can_view_concept_stats(chironuser)
            can_view2, reason2 = self.event_end_date_field.user_can_view_concept_stats(chironuser)
            if not can_view1 or not can_view2:
                return None
            if (
                self.event_date_field.has_phi
                and not chironuser.access_level == chironuser.AccessLevel.PHI
            ):
                return "deid"
            if (
                self.event_end_date_field.has_phi
                and not chironuser.access_level == chironuser.AccessLevel.PHI
            ):
                return "deid"
            return "normal"

    def user_can_view_collection(self, chironuser):
        """
        Returns True if user has access to at least one concept in this collection
        """
        collections = Collection.get_viewable_collections(chironuser)
        if self in collections:
            return True
        return False

    def get_relationships_as_pk(self):
        """
        Returns list of subcollection to subcollection relationships where this collection is
        playing the role of primary key side.
        """
        qRel = CollectionRelationship.objects.all()
        rel_ids = []
        for oRel in qRel:
            if self == oRel.get_pk_collection():
                rel_ids.append(oRel.id)
        return CollectionRelationship.objects.filter(id__in=rel_ids)

    def get_relationships_as_fk(self):
        """
        Returns list of subcollection to subcollection relationships where this collection is
        playing the role of foreign key side.
        """
        qRel = CollectionRelationship.objects.all()
        rel_ids = []
        for oRel in qRel:
            if self == oRel.get_fk_collection():
                rel_ids.append(oRel.id)
        return CollectionRelationship.objects.filter(id__in=rel_ids)

    @staticmethod
    def get_viewable_collections(chironuser):
        """
        Returns a queryset of collections that the user is allowed to view
        """
        collection_ids = []
        qPerm = chironuser.permission_groups.all()
        if not qPerm:
            return Collection.objects.accessible(chironuser.dataset)
        for oPerm in qPerm:
            for oCollection in oPerm.allowed_collections.all():
                if oCollection.id not in collection_ids:
                    collection_ids.append(oCollection.id)
        oRootCollection = chironuser.dataset.root_collection
        collection_ids.append(oRootCollection.id)
        unique_collection_ids = list(set(collection_ids))
        return Collection.objects.accessible(chironuser.dataset).filter(
            id__in=unique_collection_ids
        )


class CollectionRelationshipManager(models.Manager):
    def accessible(self, dataset):
        """
        Returns sources that are accessible based on the dataset and other settings
        """
        return self.filter(pk_concept__collection__dataset=dataset)


class CollectionRelationship(models.Model):
    """
    All subcollections automatically have a many:1 relationship with the root collection.
    You can also define a relationship between subcollections, for example
    a diagnosis that's associated with an encounter.
    """

    pk_concept = models.ForeignKey(
        "Concept",
        on_delete=models.PROTECT,
        related_name="relationships_as_pk",
        limit_choices_to={"published": True},
    )
    """ The concept that will play the primary key role. This should be a unique ID to
     represent a record in the associated collection. """
    fk_concept = models.ForeignKey(
        "Concept",
        on_delete=models.PROTECT,
        related_name="relationships_as_fk",
        limit_choices_to={"published": True},
    )
    """ The concept that will play the foreign key role, referencing the values in your
     pk_concept. For many:many relationships, the value can be an array of pk_concept values. """

    objects = CollectionRelationshipManager()

    def get_pk_collection(self):
        return self.pk_concept.collection

    def get_fk_collection(self):
        return self.fk_concept.collection

    def get_pk_concept_name(self):
        return self.pk_concept.permanent_id

    def get_fk_concept_name(self):
        return self.fk_concept.permanent_id

    def get_pk_collection_name(self):
        return self.pk_concept.collection.permanent_id

    def get_fk_collection_name(self):
        return self.fk_concept.collection.permanent_id


class PermissionGroup(models.Model):
    """
    You can give different users access to different groups of subjects and different groups
    of concepts using permission groups.

    If no permission groups are set, all users have unrestricted access to the data. Once a
    permission group exists, users access to subjects and concepts is restricted by default and
    activated based on their permission groups.
    """

    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    """ A display name for this permission group """
    description = models.TextField(blank=True, null=True)
    """ Optionally provide more info about this permission group """
    concept_for_allowed_subjects = models.ForeignKey(
        "Concept",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text=("subject included if their value for specified concept is truthy "),
        limit_choices_to={"published": True},
    )
    """ This permission group grants access to a subject if the subject's value in this concept is
    true or truthy. """
    allow_all_subjects_override = models.BooleanField(
        default=False,
        help_text=(
            "If True, people in this permission group can see all subject in system "
            + "(concept_for_allowed_subjects will be ignored)"
        ),
    )
    """ If True, this permission group grants access to all subjects. """
    allowed_concepts = models.ManyToManyField(
        "Concept",
        limit_choices_to={"category__isnull": True, "published": True},
        blank=True,
        related_name="permissiongroup_allowedconcept_set",
        help_text=(
            "Only applies to top-level concepts (ones with no category). "
            + "Any other concepts will be ignored."
        ),
    )
    """ Only applies to top-level concepts (ones with no category).
        Any other concepts will be ignored. """
    allowed_data_categories = models.ManyToManyField(
        "Category",
        limit_choices_to={"parent__isnull": True},
        blank=True,
        help_text=(
            "Only applies to top-level categories (ones with no category parent). "
            + "Any other categories will be ignored."
        ),
    )
    """ Only applies to top-level categories (ones with no category parent).
            Any other categories will be ignored. """
    allowed_collections = models.ManyToManyField(
        "Collection",
        # limit_choices_to={"dataset__root_collection": False},
        blank=True,
        help_text=(
            "Allows users to create criteria sets using this Collection. "
            + "Also may have effects on what user can see in single-subject views. "
            + "(Note that if users have access to at least one concept associated with this "
            + "Collection, they will have various indirect access to collection info regardless "
            + "of this setting.)"
        ),
    )
    """ Allows users to create criteria sets using this Collection.
        Also may have effects on what user can see in single-subject views.
        (Note that if users have access to at least one concept associated with this
        Collection, they will have various indirect access to collection info regardless
        of this setting.) """

    class Meta:
        ordering = ["dataset__unique_id", "name"]
        unique_together = (("dataset", "name"),)

    def __str__(self):
        return f"{self.dataset.unique_id}::{self.name}"

    def list_allowed_concepts(self):
        mylist = []
        for cat in self.allowed_concepts.all():
            mylist.append(str(cat))
        return ", ".join(mylist)

    def list_allowed_data_categories(self):
        mylist = []
        for cat in self.allowed_data_categories.all():
            mylist.append(str(cat))
        return ", ".join(mylist)

    @staticmethod
    def dataset_uses_permission_groups(dataset):
        """
        If any permission group records are set for this dataset, returns True.
        Sites that don't use permission groups will show all subjects and
        concept categories to all users (except PHI filters can still be applied).
        """
        if PermissionGroup.objects.filter(dataset=dataset):
            return True
        return False


class CategoryManager(models.Manager):
    def accessible(self, dataset):
        """
        Returns categories that are accessible based on the dataset and other settings
        """
        return self.filter(dataset=dataset)


class Category(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    """ The dataset this category is associated with """
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="child_set",
        help_text="Parent and child must belong to the same dataset",
    )
    """ The parent category or null if this is a top-level category """
    unique_id = models.SlugField(max_length=255)
    """ Any unique ID to identify this category (alphanumeric, underscores, dashes) """
    name = models.CharField(max_length=120)
    """ The display name for the category. """
    order = models.FloatField(default=100.0)
    """ When multiple categories have the same parent, sort from lowest to highest. """

    objects = CategoryManager()

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["dataset__unique_id", "name"]
        unique_together = (("dataset", "unique_id"),)

    def __str__(self):
        ancestor_names = self.get_ancestor_names()
        if ancestor_names:
            return f"{self.dataset.unique_id}::{ancestor_names} -> {self.name}"
        return f"{self.dataset.unique_id}::{self.name}"

    def get_ancestors(self):
        ancestors = []
        current_category = self
        while current_category.parent:
            ancestors.append(current_category.parent)
            current_category = current_category.parent
        return ancestors

    def get_ancestor_names(self):
        ancestor_names = []
        current_category = self
        while current_category.parent:
            ancestor_names.append(current_category.parent.name)
            current_category = current_category.parent
        return " -> ".join(ancestor_names)

    def get_level(self):
        level = 0
        oCategory = self
        while True:
            if oCategory.parent:
                level += 1
                oCategory = oCategory.parent
            else:
                break
        return level

    def get_top_level_parent(self):
        oCategory = self
        while True:
            if oCategory.parent:
                oCategory = oCategory.parent
            else:
                break
        return oCategory

    def get_level_indent_string(self):
        level = self.get_level()
        response = ""
        for i in range(level):
            response += '<i class="fas fa-chevron-right"></i>'
        return response

    def check_permission_group(self, chironuser):
        """
        returns True if user can view category, else false
        """
        # permission group filtering is only applied to top-level categories
        qPerm = PermissionGroup.objects.filter(dataset=chironuser.dataset).count()
        if qPerm == 0:
            return True
        oTop = self.get_top_level_parent()
        top_perm_groups = oTop.permissiongroup_set.all()
        user_perm_groups = chironuser.permission_groups.all()
        for perm_group in user_perm_groups:
            if perm_group in top_perm_groups:
                return True
        return False


class AutocreatedField(TimeStampedModel):
    """
    Keep track of which Django fields have already been autocreated, so that they are not
    created again when `python manage.py chiron_autocreate_dd` is rerun. This table has
    absolutely no effect on anything besides autocreate.
    """

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    app = models.CharField(max_length=1000, blank=True, null=True)
    """ The app name for the autocreated field """
    model = models.CharField(max_length=1000, blank=True, null=True)
    """ The model name for the autocreated field """
    field = models.CharField(max_length=1000, blank=True, null=True)
    """ The field name for the autocreated field """
    unique_source_id = models.CharField(max_length=1000, blank=True, null=True)
    """ Autocreates coming from a source other than the Django ORM will have a unique_source_id """
    associated_concept = models.ForeignKey(
        "Concept", on_delete=models.SET_NULL, blank=True, null=True
    )
    """ The existing concept related to this field. Can be null if the concept has been
    deleted. """

    class Meta:
        unique_together = (("dataset", "app", "model", "field", "unique_source_id"),)


class ConceptManager(models.Manager):
    def accessible(self, dataset):
        """
        Returns concepts that are accessible based on the dataset and other settings
        """
        return self.filter(collection__dataset=dataset, published=True)


class Concept(models.Model):
    """Defines a single menu item on the cohort def view."""

    class PrefilterMode(models.TextChoices):
        REQUIRED = "required", "required"
        OPTIONAL = "optional", "optional"

    permanent_id = models.SlugField(max_length=120, unique=True)
    """ The unique ID that will be used to reference this concept in things like saved report
    definitions. It’s important that this ID doesn’t change in a production system. """
    name = models.CharField(max_length=120)
    """ The display name for this collection. """
    name_plural = models.CharField(max_length=120, null=True, blank=True)
    """ If not set, name + 's' will be used. """
    description = models.TextField(blank=True, null=True)
    """ A description that will give more info about this concept to the user. """
    source = models.ForeignKey("Source", on_delete=models.PROTECT, null=True, blank=True)
    """ The source this concept is loaded from during the ETL. """
    concept_handler = models.ForeignKey(
        "ConceptHandler", on_delete=models.PROTECT, blank=True, null=True
    )
    """ The concept handler is a class that wraps a logical combination of etl, cohort def, and
     display processors along with appropriate settings. It will be a required field once
     fully implemented. """
    collection = models.ForeignKey("Collection", on_delete=models.PROTECT)
    """ The collection this concept is a part of. """
    category = models.ForeignKey(
        "Category",
        related_name="concepts",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    """ The Category this concept is associated with. Categories organized how concepts are
     grouped in the UI but has no effect on how the data is stored or queried. """
    order = models.FloatField(default=100.0)
    """ For multiple concepts in the same Category, lower numbers will be displayed first. """
    multivalue = models.BooleanField(
        default=True,
        help_text="Allow a single collection record to store multiple values for this concept",
    )
    """ Allow a single collection record to store multiple values for this concept """
    published = models.BooleanField(
        default=True,
        help_text="Unpublished concepts"
        " are not accessible on the UI and are not included during the ETL.",
    )
    """ Unpublished concepts are not accessible on the UI and are not included during the ETL """

    include_in_cohort_def = models.BooleanField(
        default=True,
        help_text="If false,"
        " the concept will not show up as an option when the user is building a query."
        " However, the concept is still included during the ETL"
        " and will still be allowed as part of a cohort def in existing reports.",
    )
    """ The concept will not show up as an option when the user is building a query.
        However, the concept is still included during the ETL
        and will still be allowed as part of a cohort def in existing reports. """
    include_in_table_def = models.BooleanField(
        default=True,
        help_text="If false,"
        " the concept will not show up as an option when the user is selecting"
        " However, the concept is still included during the ETL"
        " and will still be allowed as part of a table def in existing reports.",
    )
    """ The concept will not show up as an option when the user is selecting
        However, the concept is still included during the ETL
        and will still be allowed as part of a table def in existing reports. """
    include_in_analysis_def = models.BooleanField(
        default=True,
        help_text="If false,"
        " the concept will not show up as an option when the user is selecting"
        " However, the concept is still included during the ETL"
        " and will still be allowed as part of a saved analysis def.",
    )
    """ The concept will not show up as an option when the user is selecting
        However, the concept is still included during the ETL
        and will still be allowed as part of a saved analysis def. """
    has_phi = models.BooleanField(default=False, verbose_name="contains PHI")
    """ Flag this concept if it contains PHI """
    exclude_from_aggregated = models.BooleanField(default=False, verbose_name="not aggregatable")
    """ Flag this concept if it shouldn't be accessible to people with only access to aggregated
     data. Examples would be non-PHI ID fields and detailed comments fields. """
    concept_for_prefilter = models.ForeignKey(
        "Concept",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        limit_choices_to={"published": True},
        help_text="require this concept be filtered by another concept before using",
    )
    """ Allow/require this concept to be filtered by another concept from the same collection
    before using. For example, you might want to require the user to select the lab name before
    showing lab results. """
    prefilter_mode = models.CharField(
        max_length=20,
        choices=PrefilterMode.choices,
        default=PrefilterMode.REQUIRED,
        help_text="if concept_for_prefilter is set, how prefiltering should be applied",
    )
    """ If concept_for_prefilter is set, how prefiltering should be applied. If
    concept_for_prefilter is not set then has no effect. """

    class Meta:
        ordering = [
            "collection__dataset__unique_id",
            "collection__permanent_id",
            "permanent_id",
        ]

    objects = ConceptManager()

    def __str__(self):
        collection = self.collection
        return f"{collection.dataset.unique_id}::{collection.permanent_id}::{self.permanent_id}"

    def get_category_hierarchy(self):
        """
        Returns list of parent category objects in order by hierarchy level
        """
        hierarchy = []
        if not self.category:
            return hierarchy
        oCategory = self.category
        hierarchy.append(oCategory)
        while oCategory.parent:
            oCategory = oCategory.parent
            hierarchy.append(oCategory)
        hierarchy.reverse()
        return hierarchy

    def get_name_plural(self):
        return self.name_plural if self.name_plural else "{}s".format(self.name)

    def get_additional_metadata(self):
        """
        Returns a list of strings with any other information about the concept.
        As of 2024-12-05 am only using to include the ontology label for
        ontology concepts. But we may expand the role of this list in the
        future.
        """
        metadata = []
        if self.concept_handler is None:
            return metadata
        if self.concept_handler.name != "OntologyHandler":
            return metadata
        if apps.is_installed("ontologies"):
            from ontologies.interface_class import OntologyInterface  # noqa: F401

            ontology_arg = self.concepthandlerarg_set.all().filter(name="ontology_id").first()
            if ontology_arg:
                ontology_id = ontology_arg.get_value()
                try:
                    oi = OntologyInterface(ontology_id)
                    label = oi.ontology.label
                    if label:
                        metadata.append("Ontology Version: {}".format(label))
                except ObjectDoesNotExist:
                    # if we fail to get the ontology version just skip it
                    pass
        return metadata

    def get_full_database_field_name(self, entry_id=None):
        field_name = self.permanent_id
        if self.collection.is_root_collection:
            return field_name
        if entry_id:
            return "{}_{}.{}".format(self.collection.name, entry_id, field_name)
        return "{}.{}".format(self.collection.name, field_name)

    def check_permission_group(self, chironuser):
        """
        returns True if can view concept, else false (also need to check PHI)
        """
        # if no permission groups set, always return true
        qPerm = PermissionGroup.objects.filter(dataset=chironuser.dataset).count()
        if qPerm == 0:
            return True

        # True if top level category permissions are true
        user_permission_groups = chironuser.permission_groups.all()
        categories = self.get_category_hierarchy()
        if categories:
            concept_permission_groups = categories[0].permissiongroup_set.all()
            for pg in concept_permission_groups:
                if pg in user_permission_groups:
                    return True
        else:
            # this is a top-level concept, need to check allowed_concepts
            user_perm_groups = chironuser.permission_groups.all()
            for perm_group in user_perm_groups:
                for oConcept in perm_group.allowed_concepts.all():
                    if oConcept == self:
                        return True
        return False

    def _instantiate_concept_handler(
        self, chironuser, prefilter_value=None, source_processor=None
    ):
        if (
            hasattr(self, "instantiated_handler")
            and self.instantiated_handler.chironuser == chironuser
            and self.instantiated_handler.prefilter_value == prefilter_value
        ):
            return self.instantiated_handler
        kwargs = {}
        for oArg in self.concepthandlerarg_set.all():
            kwargs[oArg.name] = oArg.get_value()
        kwargs["chironuser"] = chironuser
        kwargs["dataset"] = self.collection.dataset
        kwargs["concept"] = self
        kwargs["prefilter_value"] = prefilter_value
        kwargs["source_processor"] = source_processor
        self.instantiated_handler = self.concept_handler.instantiate(**kwargs)
        return self.instantiated_handler

    def user_can_view_concept_stats(self, chironuser):
        """
        Returns True if specified chironuser is allowed to view stats for this concept. The actual
        level of detail allowed in the stats may vary (that is managed in the cohort_def
        processor). But this just gives a binary answer of whether they are allowed to access
        stats at all.
        """
        # no access to unpublished concepts
        if not self.published:
            reason = "This concept is not published."
            return False, reason
        # no access to concepts in different dataset from active one
        if chironuser.dataset != self.collection.dataset:
            reason = "This concept is for a different dataset than the active dataset."
            return False, reason
        # access blocked by permission groups
        if not self.check_permission_group(chironuser):
            reason = "The user doesn't have permission to view this concept."
            return False, reason
        # PHI can be viewed by chironuser with "phi" access level
        if chironuser.access_level == chironuser.AccessLevel.PHI:
            return True, None
        # chironuser with "agg" access level can't view exclude_from_aggregated
        if chironuser.access_level == chironuser.AccessLevel.AGG and self.exclude_from_aggregated:
            reason = "This concept contains data that can't be aggregated."
            return False, reason
        # agg and deid users can view fields with no PHI
        if (
            chironuser.access_level in [chironuser.AccessLevel.AGG, chironuser.AccessLevel.DEID]
            and not self.has_phi
        ):
            return True, None
        # if concept is PHI, agg and deid users may still be able to view if a deid cohort_def
        # processor is available
        if (
            chironuser.access_level in [chironuser.AccessLevel.AGG, chironuser.AccessLevel.DEID]
            and self.has_phi
        ):
            handler = self._instantiate_concept_handler(chironuser)
            if handler.get_deid_cohort_def_processor():
                return True, None
        # block access in all other cases
        reason = "This concept contains PHI."
        return False, reason

    def user_can_use_concept_in_cohort_def(self, chironuser, cd_entry=None):
        """
        Returns True if the specified chironuser can use this concept to filter a patient cohort.
        Optionally pass the cd_entry to test if any exceptions exist for this specific case.
        """
        # same rules as who can view concept stats
        can_view_stats, reason = self.user_can_view_concept_stats(chironuser)
        # if access is granted based on a deidentified cohort def processor being available,
        # check if this specific cd_entry is set up in a deidentified way, if not return False
        if (
            can_view_stats
            and cd_entry
            and self.has_phi
            and chironuser.access_level != chironuser.AccessLevel.PHI
        ):
            handler = self._instantiate_concept_handler(chironuser)
            processor = handler.get_deid_cohort_def_processor()
            if processor:
                if not processor.can_run_deid_query(cd_entry):
                    reason = "This cohort def entry is set up in a way that could expose PHI."
                    return False, reason
        return can_view_stats, reason

    def user_can_use_concept_in_table_def(self, chironuser, td_entry=None):
        """
        Returns True if the specified chironuser can view this concept in results output.
        Optionally pass the td_entry to test if any exceptions exist for this specific case.
        """
        # no access to unpublished concepts
        if not self.published:
            reason = "This concept is not published."
            return False, reason
        # no access to concepts in different dataset from active one
        if chironuser.dataset != self.collection.dataset:
            reason = "This concept is for a different dataset than the active dataset."
            return False, reason
        # access blocked by permission groups
        if not self.check_permission_group(chironuser):
            reason = "The user doesn't have permission to view this concept."
            return False, reason
        # PHI can be viewed by chironuser with "phi" access level
        if chironuser.access_level == chironuser.AccessLevel.PHI:
            return True, None
        # special exception for root event ID field aggregated by count, allows analysis view
        # to get subject counts in an aggregated fashion
        if (
            td_entry
            and td_entry.get("aggregate")
            and td_entry.get("aggregation_method") in ["count_all", "count_distinct"]
            and chironuser.dataset.root_collection.event_id_field == self
        ):
            return True, None
        # chironuser with "agg" access level can't view exclude_from_aggregated
        if chironuser.access_level == chironuser.AccessLevel.AGG and self.exclude_from_aggregated:
            reason = "This concept contains data that can't be aggregated."
            return False, reason
        # agg and deid users can view fields with no PHI
        if (
            chironuser.access_level in [chironuser.AccessLevel.AGG, chironuser.AccessLevel.DEID]
            and not self.has_phi
        ):
            return True, None
        # if concept is PHI, agg and deid users may still be able to view if a deid cohort_def
        # processor is available
        if (
            chironuser.access_level in [chironuser.AccessLevel.AGG, chironuser.AccessLevel.DEID]
            and self.has_phi
        ):
            handler = self._instantiate_concept_handler(chironuser)
            if handler.get_deid_display_processor():
                return True, None
        # block access in all other cases
        reason = "This concept contains PHI."
        return False, reason

    def get_etl_processor(self, source_processor=None):
        if not self.published:
            return None
        handler = self._instantiate_concept_handler(
            chironuser=None, source_processor=source_processor
        )
        return handler.get_etl_processor()

    def get_cohort_def_processor_without_user(self):
        """
        Returns the regular (not deidentified) cohort_def processor for the concept. If the
        concept is not published, returns None.

        WARNING: This method bypasses the usual checks for whether the user has permission to
        access this concept. It should only be used during the ETL or to run methods that don't
        query subject data.
        """
        if not self.published:
            return None
        handler = self._instantiate_concept_handler(chironuser=None)
        return handler.get_cohort_def_processor()

    def get_cohort_def_processor(self, chironuser, prefilter_value=None):
        """
        Returns the appropriate cohort_def processor for this concept based on the chironuser,
        with the provided prefilter_value set if provided.
        If the chironuser doesn't have permission to use this concept to define a cohort, returns
        None.
        """
        # double check that the chironuser has permission to do this
        can_use, reason = self.user_can_use_concept_in_cohort_def(chironuser)
        if not can_use:
            return None
        handler = self._instantiate_concept_handler(chironuser, prefilter_value)
        processor = handler.get_cohort_def_processor()
        if self.has_phi and chironuser.access_level != chironuser.AccessLevel.PHI:
            processor = handler.get_deid_cohort_def_processor()
        return processor

    def get_display_processor(self, chironuser, td_entry=None):
        """
        Returns the appropriate display processor for this concept based on the chironuser, with
        the td_entry set if provided.
        If the chironuser doesn't have permission to display values from this concept, returns
        None.
        """
        # double check that the chironuser has permission to do this
        can_use, reason = self.user_can_use_concept_in_table_def(chironuser, td_entry=td_entry)
        if not can_use:
            return None
        handler = self._instantiate_concept_handler(chironuser)
        display_processor = handler.get_display_processor()
        if self.has_phi and chironuser.access_level != chironuser.AccessLevel.PHI:
            deid_display_processor = handler.get_deid_display_processor()
            # if there's no deid processor but they passed the test
            # user_can_use_concept_in_table_def, that means they're allowed to access the
            # identified display processor
            if deid_display_processor:
                display_processor = deid_display_processor
        # append the optional td_entry
        if display_processor and td_entry:
            display_processor.set_td_entry(td_entry)
        return display_processor

    def get_collection_prefilters(self, prefilter_value):
        if not prefilter_value or not self.concept_for_prefilter:
            return {}
        field_name = self.concept_for_prefilter.permanent_id
        collection_id = self.concept_for_prefilter.collection.permanent_id
        return {
            collection_id: {
                "concept_id": field_name,
                "full_database_field_name": (
                    self.concept_for_prefilter.get_full_database_field_name()
                ),
                "value": prefilter_value,
            }
        }

    def prefilter_required(self):
        if self.concept_for_prefilter and self.prefilter_mode == self.PrefilterMode.REQUIRED:
            return True
        return False

    def get_summary_statistics(self, chironuser):
        processor = self.get_cohort_def_processor_without_user()
        return processor.summarize([])

    def get_data_type(self, chironuser):
        processor = self.get_display_processor(chironuser)
        return processor.get_data_type()


class SourceSourceDependency(models.Model):
    """
    Tracks which sources cannot load properly without other source(s) being loaded first.
    """

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="depends_on_sources")
    depends_on_source = models.ForeignKey(
        Source, on_delete=models.PROTECT, related_name="dependent_sources"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="(optional) explain why there is a dependency for your own reference",
    )

    class Meta:
        verbose_name_plural = "source source dependencies"


class ConceptConceptDependency(models.Model):
    """
    Tracks which concepts cannot load properly without other concept(s) being loaded first.
    """

    concept = models.ForeignKey(
        Concept, on_delete=models.CASCADE, related_name="depends_on_concepts"
    )
    depends_on_concept = models.ForeignKey(
        Concept, on_delete=models.PROTECT, related_name="dependent_concepts"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="(optional) explain why there is a dependency for your own reference",
    )

    class Meta:
        verbose_name_plural = "concept concept dependencies"


class ConceptSourceDependency(models.Model):
    """
    Tracks which concepts cannot load properly without other source(s) being loaded first.
    """

    concept = models.ForeignKey(
        Concept, on_delete=models.CASCADE, related_name="depends_on_sources"
    )
    depends_on_source = models.ForeignKey(
        Source, on_delete=models.PROTECT, related_name="dependent_concepts"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="(optional) explain why there is a dependency for your own reference",
    )

    class Meta:
        verbose_name_plural = "concept source dependencies"
