"""
URL configuration for tldp project.
"""

from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import RedirectView
from .views import LDPIndexView, LDPListView, serve_file, search_api, search_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/en/", permanent=False)),
    path("api/<str:lang>/ldplist/", LDPListView.as_view(), name="ldplist-api"),
    path("api/search/", search_api, name="search-api"),
    path("search/", search_page, name="search-page"),
    path("<str:lang>/", LDPIndexView.as_view(), name="ldp-lang-root"),
    re_path(
        r"^(?P<lang>\w+)/(?P<key>[^/]+)/(?P<path>.*)$",
        serve_file,
        name="ldp-serve-file",
    ),
]
