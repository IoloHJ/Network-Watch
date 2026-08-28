from django.contrib import admin

from .models import Device, NetworkEvent, PingResult


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "ip_address",
        "hostname",
        "manufacturer",
        "device_type",
        "status",
        "last_seen",
    )

    list_filter = (
        "status",
        "device_type",
        "manufacturer",
    )

    search_fields = (
        "ip_address",
        "hostname",
        "mac_address",
        "manufacturer",
    )


@admin.register(PingResult)
class PingResultAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "timestamp",
        "latency_ms",
        "success",
    )

    list_filter = (
        "success",
        "timestamp",
    )


@admin.register(NetworkEvent)
class NetworkEventAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "event_type",
        "severity",
        "device",
        "message",
    )

    list_filter = (
        "event_type",
        "severity",
    )

    search_fields = (
        "message",
        "device__ip_address",
        "device__hostname",
    )