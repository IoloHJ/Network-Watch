from django.urls import path

from .views import discover_devices


urlpatterns = [
    path(
        "devices/discover/",
        discover_devices,
        name="discover_devices",
    ),
]