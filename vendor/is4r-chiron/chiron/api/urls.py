from django.urls import include, path
from rest_framework import routers

from chiron.api import viewsets

router = routers.DefaultRouter()
router.register(r"chiron_users", viewsets.ChironUserViewSet)
router.register(r"me", viewsets.MeViewSet, basename="me")
router.register(r"collections", viewsets.CollectionViewSet, basename="collections")
router.register(r"concepts", viewsets.ConceptViewSet, basename="concepts")
router.register(
    r"concept_categories", viewsets.ConceptCategoryViewSet, basename="concept_categories"
)
router.register(r"cohort_def", viewsets.CohortDefViewSet, basename="cohort_def")
router.register(r"table_def", viewsets.TableDefViewSet, basename="table_def")
router.register(r"analysis_def", viewsets.AnalysisDefViewSet, basename="analysis_def")
router.register(r"query_tools", viewsets.QueryToolsViewSet, basename="query_tools")
router.register(r"analysis_tools", viewsets.AnalysisToolsViewSet, basename="analysis_tools")
router.register(r"project", viewsets.ProjectViewSet, basename="projects")
router.register(r"reports", viewsets.ReportViewSet, basename="reports")
router.register(r"report_tools", viewsets.ReportToolsViewSet, basename="report_tools")
router.register(r"version", viewsets.VersionViewSet, basename="version")

# router.register(
#     r"user_created_content", viewsets.UserCreatedContentViewSet, basename="user_created_content"
# )


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("", include(router.urls)),
]

app_name = "api"
