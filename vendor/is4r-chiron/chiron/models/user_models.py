import json

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q

# from django.core.exceptions import ValidationError
from chiron.models.data_definition_models import PermissionGroup

# TODO: Not Used? if so remove
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


# #####################################################################################


class SystemChironUser:
    """Use this when there's no chiron user.

    Many query tools require a chironuser in order to determine things like data access
    permissions and active dataset. But for system calls like management commands, there is
    no active chironuser. You can use this instead. It's intended for the system
    to use and will typically give access to EVERYTHING, so be sure to only use
    in appropriate situations.

    Note: This doesn't implement absolutely every method and property of a normal ChironUser. If
    you find there's some feature missing that you need, you can add to this class.
    """

    # this should match the AccessLevels set in ChironUser class
    class AccessLevel(models.TextChoices):
        PHI = "phi", "phi - view all subject details including PHI"
        DEID = "deid", "deid - view subject details excluding PHI"
        AGG = "agg", "agg - only aggregated data like subject count"

    def __init__(self, dataset):
        # the chironuser is often used to determine the active dataset
        self.dataset = dataset

    @property
    def permission_groups(self):
        """The null user should have all permissions"""
        qPG = PermissionGroup.objects.all()
        return qPG

    @property
    def access_level(self):
        """The null user should have the highest access level"""
        return self.AccessLevel.PHI

    def list_concepts_for_allowed_subjects(self):
        """A return value of None indicates user should have access to all subjects."""
        return None


class ChironUser(models.Model):
    """
    Defines access for a Django user to a single Chiron dataset.
    """

    class AccessLevel(models.TextChoices):
        PHI = "phi", "phi - view all subject details including PHI"
        DEID = "deid", "deid - view subject details excluding PHI"
        AGG = "agg", "agg - only aggregated data like subject count"

    dataset = models.ForeignKey("Dataset", on_delete=models.CASCADE)
    """ The associated dataset. Each ChironUser defines permissions for one Django user on one
    dataset. """
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    """ The associated Django user. This is a 1:1 relationship if there is only 1 dataset,
     otherwise a Django user can have a different ChironUser for each dataset. """
    access_level = models.CharField(
        max_length=4,
        choices=AccessLevel.choices,
        default=AccessLevel.DEID,
    )
    """ The access level granted to the user """
    can_view_workspace = models.BooleanField(default=True)
    """ If False, user cannot see query or results views and cannot define cohorts or
     reports """
    can_view_subject_details = models.BooleanField(default=True)
    """ If False, user will not be able to see the subject details section in the built-in UI """
    permission_groups = models.ManyToManyField(
        "PermissionGroup",
        blank=True,
        help_text=(
            "In order for this to have an effect, USE_PERMISSION_GROUPS must be true in settings."
        ),
    )
    """ The list of permission groups this user belongs to """

    class Meta:
        unique_together = (("dataset", "user"),)

    def get_name(self):
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username

    def __str__(self):
        return self.get_name()

    def get_created_cohorts(self):
        return self.usercreatedcontent_set.filter(type=UserCreatedContent.Type.COHORT)

    def get_created_tables(self):
        return self.usercreatedcontent_set.filter(type=UserCreatedContent.Type.TABLE)

    def get_viewable_reports(self):
        oContent = UserCreatedContent.objects.accessible(self.dataset).filter(
            type=UserCreatedContent.Type.TABLE
        )
        oContent = oContent.filter(
            Q(creator=self) | Q(share_with=self) | Q(public=True)
        ).distinct()
        return oContent

    def list_permission_groups(self, pretty=False):
        qPerm = self.permission_groups.all()
        response = []
        for oPerm in qPerm:
            if pretty:
                response.append(oPerm.name)
            else:
                response.append(str(oPerm))
        return ", ".join(response)

    def list_concepts_for_allowed_subjects(self):
        """
        Returns the concepts that are used to determine subjects the user is allowed to view.

        return None - user is allowed to view all subjects
        return [] - user is allowed to view no subjects
        return concept list - user is allowed to view subjects where at least one of the
          specified concepts is truthy
        """
        # if this dataset doesn't use permission groups, all users can see all subjects
        if not PermissionGroup.dataset_uses_permission_groups(self.dataset):
            return None
        relevant_concepts = []
        # get a list of distinct concepts we're using to filter subjects
        for oPerm in self.permission_groups.all():
            if oPerm.allow_all_subjects_override:
                # we can quit early because they're allowed to see everything
                return None
            oConcept = oPerm.concept_for_allowed_subjects
            if oConcept and oConcept not in relevant_concepts:
                relevant_concepts.append(oConcept)
        return relevant_concepts


class CohortDefSnapshot(TimeStampedModel):
    """
    Stores a history of cohort defs for a user to enable feature like restore previous session,
    undo/redo cohort def changes, etc.
    """

    # TODO: it's confusing that this field links to a chironuser but is called user
    chironuser = models.ForeignKey("ChironUser", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    cohort_def = models.TextField()

    def save(self, *args, **kwargs):
        if self.is_active:
            # want to wipe out all downstream changes
            oActiveSnapshot = CohortDefSnapshot.objects.filter(
                chironuser=self.chironuser, is_active=True
            ).first()
            if oActiveSnapshot:
                qDownstreamSnapshot = CohortDefSnapshot.objects.filter(
                    chironuser=self.chironuser, created__gt=oActiveSnapshot.created
                )
                qDownstreamSnapshot.delete()
            # only allow 1 active snapshot for a chironuser at one time
            qSnapshot = CohortDefSnapshot.objects.filter(
                chironuser=self.chironuser, is_active=True
            )
            for oSnapshot in qSnapshot:
                oSnapshot.is_active = False
                oSnapshot.save()
        super().save(*args, **kwargs)

    @staticmethod
    def clear_history(chironuser):
        """
        Run this before loading a new active cohort def
        """
        qSnapshot = CohortDefSnapshot.objects.filter(chironuser=chironuser)
        qSnapshot.delete()

    @staticmethod
    def get_active_snapshot(chironuser):
        oSnapshot = CohortDefSnapshot.objects.filter(chironuser=chironuser, is_active=True).first()
        return oSnapshot

    @staticmethod
    def get_active_cohort_def(chironuser):
        oSnapshot = CohortDefSnapshot.objects.filter(chironuser=chironuser, is_active=True).first()
        if oSnapshot:
            return oSnapshot.get_cohort_def()
        return []

    @staticmethod
    def set_active(chironuser, snapshot_id):
        """return True on success, else false"""
        oSnapshot = CohortDefSnapshot.objects.filter(chironuser=chironuser, id=snapshot_id).first()
        if oSnapshot:
            qSnapshot = CohortDefSnapshot.objects.filter(chironuser=chironuser, is_active=True)
            for o in qSnapshot:
                o.is_active = False
                o.save()
            oSnapshot.is_active = True
            oSnapshot.save()
        return oSnapshot

    def get_cohort_def(self):
        return json.loads(self.cohort_def)

    def set_cohort_def(self, cohort_def):
        self.cohort_def = json.dumps(cohort_def)

    def get_previous(self):
        """
        Returns previous snapshot if it exists, else None
        """
        oSnapshot = (
            CohortDefSnapshot.objects.filter(chironuser=self.chironuser, created__lt=self.created)
            .order_by("-created")
            .first()
        )
        return oSnapshot

    def get_next(self):
        """
        Returns next snapshot if it exists, else None
        """
        oSnapshot = (
            CohortDefSnapshot.objects.filter(chironuser=self.chironuser, created__gt=self.created)
            .order_by("created")
            .first()
        )
        return oSnapshot

    def get_previous_id(self):
        """
        Returns ID if previous snapshot exists, else None
        """
        oSnapshot = self.get_previous()
        if oSnapshot:
            return oSnapshot.id
        return None

    def get_next_id(self):
        """
        Returns ID if next snapshot exists, else None
        """
        oSnapshot = self.get_next()
        if oSnapshot:
            return oSnapshot.id
        return None


class TableDefSnapshot(TimeStampedModel):
    """
    Stores a history of table and sort defs for a chironuser to enable feature like
    restore previous session, undo/redo cohort def changes, etc.
    """

    # TODO: it's confusing that this field links to a chironuser but is called user
    chironuser = models.ForeignKey("ChironUser", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    table_def = models.TextField()

    def save(self, *args, **kwargs):
        if self.is_active:
            # want to wipe out all downstream changes
            oActiveSnapshot = TableDefSnapshot.objects.filter(
                chironuser=self.chironuser, is_active=True
            ).first()
            if oActiveSnapshot:
                qDownstreamSnapshot = TableDefSnapshot.objects.filter(
                    chironuser=self.chironuser, created__gt=oActiveSnapshot.created
                )
                qDownstreamSnapshot.delete()
            # only allow 1 active snapshot for a chironuser at one time
            qSnapshot = TableDefSnapshot.objects.filter(chironuser=self.chironuser, is_active=True)
            for oSnapshot in qSnapshot:
                oSnapshot.is_active = False
                oSnapshot.save()
        super().save(*args, **kwargs)

    @staticmethod
    def clear_history(chironuser):
        """
        Run this before loading a new active cohort def
        """
        qSnapshot = TableDefSnapshot.objects.filter(chironuser=chironuser)
        qSnapshot.delete()

    @staticmethod
    def get_active_snapshot(chironuser):
        oSnapshot = TableDefSnapshot.objects.filter(chironuser=chironuser, is_active=True).first()
        return oSnapshot

    @staticmethod
    def get_active_table_def(chironuser):
        oSnapshot = TableDefSnapshot.objects.filter(chironuser=chironuser, is_active=True).first()
        if oSnapshot:
            return oSnapshot.get_table_def()
        return {"fields": []}

    @staticmethod
    def set_active(chironuser, snapshot_id):
        """return True on success, else false"""
        oSnapshot = TableDefSnapshot.objects.filter(chironuser=chironuser, id=snapshot_id).first()
        if oSnapshot:
            qSnapshot = TableDefSnapshot.objects.filter(chironuser=chironuser, is_active=True)
            for o in qSnapshot:
                o.is_active = False
                o.save()
            oSnapshot.is_active = True
            oSnapshot.save()
        return oSnapshot

    def get_table_def(self):
        return json.loads(self.table_def)

    #     def get_sort_def(self):
    #         return json.loads(self.sort_def)

    def set_table_def(self, table_def):
        self.table_def = json.dumps(table_def)

    #     def set_sort_def(self, sort_def):
    #         self.sort_def = json.dumps(sort_def)

    def get_previous(self):
        """
        Returns previous snapshot if it exists, else None
        """
        oSnapshot = (
            TableDefSnapshot.objects.filter(chironuser=self.chironuser, created__lt=self.created)
            .order_by("-created")
            .first()
        )
        return oSnapshot

    def get_next(self):
        """
        Returns next snapshot if it exists, else None
        """
        oSnapshot = (
            TableDefSnapshot.objects.filter(chironuser=self.chironuser, created__gt=self.created)
            .order_by("created")
            .first()
        )
        return oSnapshot

    def get_previous_id(self):
        """
        Returns ID if previous snapshot exists, else None
        """
        oSnapshot = self.get_previous()
        if oSnapshot:
            return oSnapshot.id
        return None

    def get_next_id(self):
        """
        Returns ID if next snapshot exists, else None
        """
        oSnapshot = self.get_next()
        if oSnapshot:
            return oSnapshot.id
        return None


class AnalysisDefSnapshot(TimeStampedModel):
    """
    Stores a history of table and sort defs for a chironuser to enable feature
    like restore previous session, undo/redo cohort def changes, etc.
    """

    chironuser = models.ForeignKey("ChironUser", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    analysis_def = models.TextField()

    def save(self, *args, **kwargs):
        if self.is_active:
            # want to wipe out all downstream changes
            oActiveSnapshot = AnalysisDefSnapshot.objects.filter(
                chironuser=self.chironuser, is_active=True
            ).first()
            if oActiveSnapshot:
                qDownstreamSnapshot = AnalysisDefSnapshot.objects.filter(
                    chironuser=self.chironuser, created__gt=oActiveSnapshot.created
                )
                qDownstreamSnapshot.delete()
            # only allow 1 active snapshot for a chironuser at one time
            qSnapshot = AnalysisDefSnapshot.objects.filter(
                chironuser=self.chironuser, is_active=True
            )
            for oSnapshot in qSnapshot:
                oSnapshot.is_active = False
                oSnapshot.save()
        super().save(*args, **kwargs)

    @staticmethod
    def clear_history(chironuser):
        """
        Run this before loading a new active cohort def
        """
        qSnapshot = AnalysisDefSnapshot.objects.filter(chironuser=chironuser)
        qSnapshot.delete()

    @staticmethod
    def get_active_snapshot(chironuser):
        oSnapshot = AnalysisDefSnapshot.objects.filter(
            chironuser=chironuser, is_active=True
        ).first()
        return oSnapshot

    @staticmethod
    def get_active_analysis_def(chironuser):
        oSnapshot = AnalysisDefSnapshot.objects.filter(
            chironuser=chironuser, is_active=True
        ).first()
        if oSnapshot:
            return oSnapshot.get_analysis_def()
        return {"fields": []}

    @staticmethod
    def set_active(chironuser, snapshot_id):
        """return True on success, else false"""
        oSnapshot = AnalysisDefSnapshot.objects.filter(
            chironuser=chironuser, id=snapshot_id
        ).first()
        if oSnapshot:
            qSnapshot = AnalysisDefSnapshot.objects.filter(chironuser=chironuser, is_active=True)
            for o in qSnapshot:
                o.is_active = False
                o.save()
            oSnapshot.is_active = True
            oSnapshot.save()
        return oSnapshot

    def get_analysis_def(self):
        return json.loads(self.analysis_def)

    #     def get_sort_def(self):
    #         return json.loads(self.sort_def)

    def set_analysis_def(self, analysis_def):
        self.analysis_def = json.dumps(analysis_def)

    #     def set_sort_def(self, sort_def):
    #         self.sort_def = json.dumps(sort_def)

    def get_previous(self):
        """
        Returns previous snapshot if it exists, else None
        """
        oSnapshot = (
            AnalysisDefSnapshot.objects.filter(
                chironuser=self.chironuser, created__lt=self.created
            )
            .order_by("-created")
            .first()
        )
        return oSnapshot

    def get_next(self):
        """
        Returns next snapshot if it exists, else None
        """
        oSnapshot = (
            AnalysisDefSnapshot.objects.filter(
                chironuser=self.chironuser, created__gt=self.created
            )
            .order_by("created")
            .first()
        )
        return oSnapshot

    def get_previous_id(self):
        """
        Returns ID if previous snapshot exists, else None
        """
        oSnapshot = self.get_previous()
        if oSnapshot:
            return oSnapshot.id
        return None

    def get_next_id(self):
        """
        Returns ID if next snapshot exists, else None
        """
        oSnapshot = self.get_next()
        if oSnapshot:
            return oSnapshot.id
        return None


class ContentSharing(TimeStampedModel):
    content = models.ForeignKey("UserCreatedContent", on_delete=models.CASCADE)
    chironuser = models.ForeignKey("ChironUser", on_delete=models.CASCADE)


class ContentFlag(TimeStampedModel):
    class FlagType(models.TextChoices):
        STAR = "star", "star"

    content = models.ForeignKey("UserCreatedContent", on_delete=models.CASCADE)
    chironuser = models.ForeignKey("ChironUser", on_delete=models.CASCADE)
    flag_type = models.CharField(max_length=10, choices=FlagType.choices)


class ProjectManager(models.Manager):
    def accessible(self, dataset):
        """
        Returns projects that are accessible based on the dataset and other settings
        """
        return self.filter(dataset=dataset)


class Project(TimeStampedModel):
    """
    UserCreatedContent can be grouped into projects.

    Projects may take on a more important role in the future, but currently they're just a way
    to help organize content for display purposes.
    """

    dataset = models.ForeignKey("Dataset", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]

    objects = ProjectManager()

    def __str__(self):
        return self.name

    def get_report_count(self, oChironUser=None):
        if oChironUser:
            qReport = oChironUser.get_viewable_reports()
        else:
            qReport = models.Report.objects.all()
        qReport = qReport.filter(project=self)
        return qReport.count()


class UserCreatedContentManager(models.Manager):
    def accessible(self, dataset):
        """
        Returns content that is accessible based on the dataset and other settings
        """
        return self.filter(dataset=dataset)


class UserCreatedContent(TimeStampedModel):
    class Type(models.TextChoices):
        COHORT = "cohort", "cohort"
        TABLE = "table", "table"
        COHORT_AUTO = (
            "cohort_auto",
            "cohort_auto",
        )  # A Cohort that is being auto-saved for the user

    dataset = models.ForeignKey("Dataset", on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    project = models.ForeignKey("Project", on_delete=models.SET_NULL, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    creator = models.ForeignKey("ChironUser", on_delete=models.PROTECT)
    type = models.CharField(max_length=60, choices=Type.choices)
    definition = models.TextField(default="{}")
    public = models.BooleanField(default=True)
    share_with = models.ManyToManyField(
        "ChironUser",
        through="ContentSharing",
        related_name="shared_content_set",
        blank=True,
    )

    objects = UserCreatedContentManager()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-id"]
        verbose_name_plural = "user created content"

    def get_definition(self):
        definition = json.loads(self.definition)
        definition = self._append_defaults(definition)
        return definition

    def get_def_value(self, value_name):
        definition = self.get_definition()
        return definition.get(value_name, None)

    def set_def_value(self, value_name, value):
        definition = json.loads(self.definition)
        definition[value_name] = value
        self.definition = json.dumps(definition)

    def check_cohort_def_is_dirty(self, cohort_def):
        existing_cohort_def = self.get_def_value("cohort_def")
        # convert both to strings and compare strings
        cohort_def_string = json.dumps(cohort_def)
        existing_cohort_def_string = json.dumps(existing_cohort_def)
        return True if cohort_def_string != existing_cohort_def_string else False

    def get_sharing_description(self):
        if self.public:
            return "public"
        sharee_count = self.share_with.all().count()
        if sharee_count == 0:
            return "private"
        return "{} users".format(sharee_count)

    def check_if_starred(self, oChironUser):
        qFlag = ContentFlag.objects.filter(
            content=self, chironuser=oChironUser, flag_type=ContentFlag.FlagType.STAR
        )
        return True if qFlag else False

    def _append_defaults(self, definition):
        if "records_per_page" not in definition:
            definition["records_per_page"] = 500
        return definition
