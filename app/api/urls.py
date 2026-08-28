from django.urls import path

from .views import discover_devices, scanner_event


urlpatterns = [
    path(
        "devices/discover/",
        discover_devices,
        name="discover_devices",
    ),
    path(
        "events/",
        scanner_event,
        name="scanner_event",
    ),
]