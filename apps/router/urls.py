from django.urls import path

from apps.router.views import QueryAPIView

urlpatterns = [
    path("query/", QueryAPIView.as_view(), name="query"),
]
