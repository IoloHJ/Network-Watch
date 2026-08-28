from django.db import models

from django.db import models


class Device(models.Model):
    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        UNKNOWN = "unknown", "Unknown"

    class DeviceType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        ROUTER = "router", "Router"
        COMPUTER = "computer", "Computer"
        PHONE = "phone", "Phone"
        TABLET = "tablet", "Tablet"
        TV = "tv", "TV"
        CAMERA = "camera", "Camera"
        PRINTER = "printer", "Printer"
        SERVER = "server", "Server"
        IOT = "iot", "IoT"
        OTHER = "other", "Other"

    hostname = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    ip_address = models.GenericIPAddressField(
        unique=True,
    )

    mac_address = models.CharField(
        max_length=17,
        blank=True,
        default="",
    )

    manufacturer = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.UNKNOWN,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNKNOWN,
    )

    first_seen = models.DateTimeField(
        auto_now_add=True,
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["ip_address"]

    def __str__(self):
        if self.hostname:
            return f"{self.hostname} ({self.ip_address})"

        return self.ip_address


class PingResult(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="ping_results",
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
    )

    latency_ms = models.FloatField(
        null=True,
        blank=True,
    )

    success = models.BooleanField(
        default=False,
    )

    error_message = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        status = "Success" if self.success else "Failed"

        if self.latency_ms is not None:
            return (
                f"{self.device.ip_address} - "
                f"{status} - "
                f"{self.latency_ms:.2f}ms"
            )

        return f"{self.device.ip_address} - {status}"



class NetworkEvent(models.Model):
    class EventType(models.TextChoices):
        DEVICE_ONLINE = "device_online", "Device Online"
        DEVICE_OFFLINE = "device_offline", "Device Offline"
        DEVICE_DISCOVERED = "device_discovered", "Device Discovered"
        DEVICE_CHANGED = "device_changed", "Device Changed"
        HIGH_LATENCY = "high_latency", "High Latency"
        SCAN_STARTED = "scan_started", "Scan Started"
        SCAN_COMPLETED = "scan_completed", "Scan Completed"
        ERROR = "error", "Error"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="network_events",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFO,
    )

    message = models.TextField()

    timestamp = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.event_type}: {self.message}"