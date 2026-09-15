"""Identity resolution and the permission gates Chiron only enforces at HTTP.

WHY THIS MODULE EXISTS
----------------------
This server calls Chiron's Python directly rather than going through its REST
API, because the API physically cannot execute a caller-supplied cohort_def:
`QueryToolsViewSet._get_cohort_def` (chiron/api/viewsets/query_tools.py:204-214)
discards it and returns the caller's active snapshot.

The cost of skipping HTTP is that three permission classes never run, because
they are DRF classes invoked by the viewsets and by nothing else:

  * SubjectLevelAccess          chiron/api/permissions.py:64-79
  * CanViewWorkspacePermission  chiron/api_v2/permissions.py:37-45
  * AnalysisViewOn              chiron/api/permissions.py:55-62

So they are re-implemented here and every tool calls `resolve()` first.

Note that `Concept.user_can_view_concept_stats` is NOT a substitute for
SubjectLevelAccess: it explicitly *allows* agg users for non-PHI concepts
(chiron/models/data_definition_models.py:1114-1120).  The agg block is the DRF
class, and only the DRF class.
"""

from __future__ import annotations

from dataclasses import dataclass

from chiron_mcp.config import ACCESS_ORDER, AGG, CONFIG, DEID, PHI


class AccessError(Exception):
    """Raised instead of returning data.  The message is shown to the model."""


@dataclass
class Identity:
    """One resolved (Django user, Dataset) pair and its Chiron access rights."""

    dataset: object  # chiron.models.Dataset
    chironuser: object  # chiron.models.ChironUser
    access_level: str
    can_view_workspace: bool
    can_view_subject_details: bool

    @property
    def dataset_id(self) -> str:
        return self.dataset.unique_id


def _django_user():
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.filter(username=CONFIG.username).first()
    if not user:
        raise AccessError(
            f"No Django user named {CONFIG.username!r} exists in the metadata database."
        )
    if not user.is_active:
        raise AccessError(f"Django user {CONFIG.username!r} is inactive.")
    # A superuser bypasses nothing in Chiron itself, but running the server as one
    # makes the blast radius of any mistake the whole instance.
    if user.is_superuser and not CONFIG.operator:
        raise AccessError(
            f"Django user {CONFIG.username!r} is a superuser. Refusing to start in "
            "analyst mode. Point CHIRON_MCP_USERNAME at a dedicated service user, or "
            "set CHIRON_MCP_OPERATOR=1 if this is deliberate."
        )
    return user


def _ceiling(actual: str) -> str:
    """Clamp an access level to CHIRON_MCP_MAX_ACCESS_LEVEL.

    A ChironUser provisioned at phi on a dataset whose auto_access_level is phi
    (true of synthea-small and synthea-10k on the live instance) is treated as
    deid unless the operator has raised the ceiling explicitly.
    """
    ceiling = CONFIG.max_access_level
    if ACCESS_ORDER.index(actual) <= ACCESS_ORDER.index(ceiling):
        return actual
    return ceiling


def resolve(dataset_id: str) -> Identity:
    """Resolve the bound identity against one dataset, or raise AccessError.

    Deliberately does NOT reproduce the autocreate branch of
    `get_request_chironuser` (chiron/authorization.py:61-72).  That branch writes
    a ChironUser row as a side effect of a read, provisioning access at
    `Dataset.auto_access_level` -- which is 'phi' on two of the live datasets.
    A read through this server never grants anyone anything.
    """
    from chiron import models

    if CONFIG.dataset_allowlist and dataset_id not in CONFIG.dataset_allowlist:
        raise AccessError(
            f"Dataset {dataset_id!r} is not in CHIRON_MCP_DATASETS "
            f"({', '.join(CONFIG.dataset_allowlist)})."
        )

    oDataset = models.Dataset.objects.filter(unique_id=dataset_id).first()
    if not oDataset:
        raise AccessError(f"No dataset with unique_id {dataset_id!r}.")

    user = _django_user()

    # The exact lookup Chiron performs at chiron/authorization.py:59 -- minus the
    # autocreate fallback that follows it.
    oChironUser = models.ChironUser.objects.filter(user=user, dataset=oDataset).first()
    if not oChironUser:
        hint = ""
        if oDataset.autocreate_chiron_user:
            hint = (
                " This dataset has autocreate_chiron_user set, so Chiron's own UI would "
                "have provisioned access on first contact at access level "
                f"'{oDataset.auto_access_level}'. This server does not do that: create the "
                "ChironUser deliberately if access is intended."
            )
        raise AccessError(
            f"User {CONFIG.username!r} has no ChironUser on dataset {dataset_id!r}.{hint}"
        )

    if oChironUser.access_level is None:
        raise AccessError(f"ChironUser {oChironUser.pk} has no access_level set.")

    return Identity(
        dataset=oDataset,
        chironuser=oChironUser,
        access_level=_ceiling(oChironUser.access_level),
        can_view_workspace=bool(oChironUser.can_view_workspace),
        can_view_subject_details=bool(oChironUser.can_view_subject_details),
    )


# --- the gates ---------------------------------------------------------------


def require_subject_level(ident: Identity) -> None:
    """Mirror of SubjectLevelAccess (chiron/api/permissions.py:64-79).

    Chiron's API 403s an agg identity on concepts, query_tools, report_tools,
    reports, cohort_def and table_def.  Refusing here rather than masking is what
    Chiron's own UI does; the masking path
    (`_analysis_view_aggregate_pivottable`, chiron/query_engine/abstract_querytool.py:198)
    exists only for the analysis view and has no equivalent in get_report_preview
    or get_full_report.
    """
    if ident.access_level not in (PHI, DEID):
        raise AccessError(
            f"Access level '{ident.access_level}' cannot see subject-level data. "
            "Chiron's own API returns 403 for this identity on this kind of request. "
            "Use chiron_crosstab, which is the aggregate-safe path."
        )


def require_workspace(ident: Identity) -> None:
    """Mirror of CanViewWorkspacePermission (chiron/api_v2/permissions.py:37-45)."""
    if not ident.can_view_workspace:
        raise AccessError(
            f"ChironUser on dataset {ident.dataset_id!r} does not have "
            "can_view_workspace, so concept and query functionality is not available."
        )


def require_analysis_view() -> None:
    """Mirror of AnalysisViewOn (chiron/api/permissions.py:55-62).

    Gates the whole analysis/pivot surface on a deployment setting that defaults
    to False (chiron/chiron_settings.py:67).
    """
    from chiron import chiron_settings

    if not chiron_settings.CHIRON_SHOW_ANALYSIS_VIEW:
        raise AccessError(
            "CHIRON_SHOW_ANALYSIS_VIEW is off for this deployment, so the analysis "
            "view is disabled. Chiron's own API returns 403 here."
        )


def require_operator() -> None:
    """Gate for the operations tool group."""
    if not CONFIG.operator:
        raise AccessError(
            "Operations tools are disabled. Set CHIRON_MCP_OPERATOR=1 to enable them."
        )
    user = _django_user()
    if not user.is_staff:
        raise AccessError(
            f"Django user {CONFIG.username!r} is not staff; operations tools require it."
        )


def checked_chironuser(ident: Identity):
    """Return the ChironUser, refusing to ever hand a processor None.

    `CohortDefProcessor.__init__` does
    `self.chironuser = chironuser if chironuser else SystemChironUser(oDataset)`
    (chiron/processors/abstract/cohort_def_processor.py:42).  SystemChironUser has
    hardcoded PHI access, returns every PermissionGroup with no dataset filter, and
    its own docstring warns it grants access to everything.  A None reaching a
    processor is therefore a silent privilege escalation, so it is a hard error here.
    """
    if ident.chironuser is None:
        raise AccessError(
            "Internal error: no ChironUser resolved. Refusing to continue, because "
            "Chiron would silently substitute SystemChironUser (full PHI, all datasets)."
        )
    return ident.chironuser
