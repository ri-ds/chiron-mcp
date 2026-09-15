from django.urls import path, include

urlpatterns = [
    path("", include(("chiron.urls", "chiron"), namespace="chiron")),
]
