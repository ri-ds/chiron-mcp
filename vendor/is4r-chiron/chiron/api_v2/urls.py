from django.urls import include, path
from rest_framework import routers

from chiron.api_v2 import viewsets

router = routers.DefaultRouter()
router.register(r"auth", viewsets.AuthViewSetV2, basename="auth")
router.register(r"(?P<dataset_string>.+)/concepts", viewsets.ConceptViewSetV2, basename="concepts")
router.register(r"(?P<dataset_string>.+)/reports", viewsets.ReportViewSetV2, basename="reports")
router.register(
    r"(?P<dataset_string>.+)/cohort_def", viewsets.CohortDefViewSetV2, basename="cohort_def"
)
router.register(
    r"(?P<dataset_string>.+)/table_def", viewsets.TableDefViewSetV2, basename="table_def"
)
router.register(
    r"(?P<dataset_string>.+)/analysis_def", viewsets.AnalysisDefViewSetV2, basename="analysis_def"
)
router.register(
    r"(?P<dataset_string>.+)/analysis_tools",
    viewsets.AnalysisToolsViewSetV2,
    basename="analysis_tools",
)
router.register(
    r"(?P<dataset_string>.+)/query_tools", viewsets.QueryToolsViewSetV2, basename="query_tools"
)
router.register(
    r"(?P<dataset_string>.+)/report_tools", viewsets.ReportToolsViewSetV2, basename="report_tools"
)
router.register(
    r"(?P<dataset_string>.+)/concept_categories",
    viewsets.ConceptCategoryViewSetV2,
    basename="concept_categories",
)
router.register(
    r"(?P<dataset_string>.+)/collections",
    viewsets.CollectionViewSetV2,
    basename="collections",
)
router.register(
    r"dataset",
    viewsets.DatasetViewSetV2,
    basename="datasets",
)
urlpatterns = [
    path("", include(router.urls)),
]

app_name = "api_v2"
