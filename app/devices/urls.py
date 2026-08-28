from django.urls import path

from .views import device_detail


urlpatterns = [
    path(
        "<int:device_id>/",
        device_detail,
        name="device_detail",
    ),
]