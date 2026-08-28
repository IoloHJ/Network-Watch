import json
import traceback

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from devices.models import Device, PingResult, NetworkEvent


@csrf_exempt
def discover_devices(request):
    """
    NetWatch device discovery API.

    POST:
        Receives discovered devices from the scanner.

    GET:
        Returns API status information.

    The API deliberately returns detailed JSON errors
    to make Docker/scanner debugging easier.
    """

    # ============================================================
    # GET - API STATUS
    # ============================================================

    if request.method == "GET":
        try:
            device_count = Device.objects.count()

            online_count = Device.objects.filter(
                status=Device.Status.ONLINE
            ).count()

            offline_count = Device.objects.filter(
                status=Device.Status.OFFLINE
            ).count()

            return JsonResponse(
                {
                    "success": True,
                    "service": "NetWatch Device Discovery API",
                    "status": "online",
                    "method": "POST",
                    "endpoint": "/api/devices/discover/",
                    "database": {
                        "connected": True,
                        "total_devices": device_count,
                        "online": online_count,
                        "offline": offline_count,
                    },
                },
                status=200,
            )

        except Exception as exc:

            return JsonResponse(
                {
                    "success": False,
                    "error": "API status check failed",
                    "reason": str(exc),
                    "exception": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                },
                status=500,
            )

    # ============================================================
    # ONLY POST ALLOWED FOR DEVICE DISCOVERY
    # ============================================================

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid HTTP method",
                "reason": (
                    f"{request.method} is not supported. "
                    "Use POST to submit discovered devices."
                ),
                "expected_method": "POST",
                "endpoint": "/api/devices/discover/",
            },
            status=405,
        )

    # ============================================================
    # PARSE JSON
    # ============================================================

    try:

        raw_body = request.body.decode("utf-8")

    except UnicodeDecodeError as exc:

        return JsonResponse(
            {
                "success": False,
                "error": "Unable to decode request body",
                "reason": str(exc),
                "exception": type(exc).__name__,
            },
            status=400,
        )

    try:

        data = json.loads(raw_body)

    except json.JSONDecodeError as exc:

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON",
                "reason": str(exc),
                "exception": type(exc).__name__,
                "position": exc.pos,
                "line": exc.lineno,
                "column": exc.colno,
                "raw_body": raw_body[:1000],
            },
            status=400,
        )

    # ============================================================
    # VALIDATE ROOT JSON
    # ============================================================

    try:

        if not isinstance(data, dict):

            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid request format",
                    "reason": (
                        "The JSON root must be an object."
                    ),
                    "received_type": type(data).__name__,
                },
                status=400,
            )

        if "devices" not in data:

            return JsonResponse(
                {
                    "success": False,
                    "error": "Missing devices field",
                    "reason": (
                        "The request must contain "
                        "a 'devices' list."
                    ),
                    "example": {
                        "devices": [
                            {
                                "ip_address": "192.168.1.254",
                                "hostname": "router",
                                "latency_ms": 2.5,
                            }
                        ]
                    },
                },
                status=400,
            )

        devices = data["devices"]

        if not isinstance(devices, list):

            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid devices field",
                    "reason": (
                        "'devices' must be a list."
                    ),
                    "received_type": (
                        type(devices).__name__
                    ),
                },
                status=400,
            )

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": "Request validation failed",
                "reason": str(exc),
                "exception": type(exc).__name__,
                "traceback": traceback.format_exc(),
            },
            status=400,
        )

    # ============================================================
    # PROCESS DEVICES
    # ============================================================

    now = timezone.now()

    created_count = 0
    updated_count = 0
    ping_count = 0

    errors = []
    processed = []

    for index, item in enumerate(devices):

        # --------------------------------------------------------
        # Validate individual device
        # --------------------------------------------------------

        try:

            if not isinstance(item, dict):

                errors.append(
                    {
                        "index": index,
                        "error": "Invalid device object",
                        "reason": (
                            "Each device must be a JSON object."
                        ),
                        "received_type": (
                            type(item).__name__
                        ),
                    }
                )

                continue

            ip_address = item.get(
                "ip_address"
            )

            if not ip_address:

                errors.append(
                    {
                        "index": index,
                        "error": "Missing IP address",
                        "reason": (
                            "Every discovered device "
                            "must contain 'ip_address'."
                        ),
                        "device": item,
                    }
                )

                continue

            hostname = item.get(
                "hostname",
                "",
            ) or ""

            latency_ms = item.get(
                "latency_ms"
            )

            mac_address = item.get(
                "mac_address",
                "",
            ) or ""

            manufacturer = item.get(
                "manufacturer",
                "",
            ) or ""

            device_type = item.get(
                "device_type",
                Device.DeviceType.UNKNOWN,
            ) or Device.DeviceType.UNKNOWN

        except Exception as exc:

            errors.append(
                {
                    "index": index,
                    "error": "Device validation failed",
                    "reason": str(exc),
                    "exception": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                }
            )

            continue

        # --------------------------------------------------------
        # Database operation
        # --------------------------------------------------------

        try:

            device = Device.objects.filter(
                ip_address=ip_address
            ).first()

            # ====================================================
            # NEW DEVICE
            # ====================================================

            if device is None:

                device = Device.objects.create(
                    ip_address=ip_address,
                    hostname=hostname,
                    mac_address=mac_address,
                    manufacturer=manufacturer,
                    device_type=device_type,
                    status=Device.Status.ONLINE,
                    last_seen=now,
                )

                created_count += 1

                NetworkEvent.objects.create(
                    device=device,
                    event_type=(
                        NetworkEvent.EventType
                        .DEVICE_DISCOVERED
                    ),
                    severity=(
                        NetworkEvent.Severity.INFO
                    ),
                    message=(
                        f"Device discovered: "
                        f"{hostname or ip_address}"
                    ),
                )

                action = "created"

            # ====================================================
            # EXISTING DEVICE
            # ====================================================

            else:

                was_offline = (
                    device.status
                    == Device.Status.OFFLINE
                )

                changed = False

                if hostname and (
                    device.hostname != hostname
                ):
                    device.hostname = hostname
                    changed = True

                if mac_address and (
                    device.mac_address != mac_address
                ):
                    device.mac_address = mac_address
                    changed = True

                if manufacturer and (
                    device.manufacturer
                    != manufacturer
                ):
                    device.manufacturer = manufacturer
                    changed = True

                if device_type and (
                    device.device_type
                    != device_type
                ):
                    device.device_type = device_type
                    changed = True

                device.status = (
                    Device.Status.ONLINE
                )

                device.last_seen = now

                device.save(
                    update_fields=[
                        "hostname",
                        "mac_address",
                        "manufacturer",
                        "device_type",
                        "status",
                        "last_seen",
                        "updated_at",
                    ]
                )

                updated_count += 1

                action = "updated"

                # ------------------------------------------------
                # Device came back online
                # ------------------------------------------------

                if was_offline:

                    NetworkEvent.objects.create(
                        device=device,
                        event_type=(
                            NetworkEvent.EventType
                            .DEVICE_ONLINE
                        ),
                        severity=(
                            NetworkEvent.Severity.INFO
                        ),
                        message=(
                            f"Device back online: "
                            f"{hostname or ip_address}"
                        ),
                    )

                # ------------------------------------------------
                # Device information changed
                # ------------------------------------------------

                elif changed:

                    NetworkEvent.objects.create(
                        device=device,
                        event_type=(
                            NetworkEvent.EventType
                            .DEVICE_CHANGED
                        ),
                        severity=(
                            NetworkEvent.Severity.INFO
                        ),
                        message=(
                            f"Device information "
                            f"updated: "
                            f"{hostname or ip_address}"
                        ),
                    )

            # ====================================================
            # PING RESULT
            # ====================================================

            if latency_ms is not None:

                try:

                    latency_ms = float(
                        latency_ms
                    )

                    PingResult.objects.create(
                        device=device,
                        latency_ms=latency_ms,
                        success=True,
                    )

                    ping_count += 1

                    # --------------------------------------------
                    # High latency
                    # --------------------------------------------

                    if latency_ms >= 100:

                        NetworkEvent.objects.create(
                            device=device,
                            event_type=(
                                NetworkEvent.EventType
                                .HIGH_LATENCY
                            ),
                            severity=(
                                NetworkEvent.Severity.WARNING
                            ),
                            message=(
                                f"High latency detected: "
                                f"{latency_ms}ms"
                            ),
                        )

                except Exception as exc:

                    errors.append(
                        {
                            "ip_address": ip_address,
                            "error": (
                                "Failed to record ping result"
                            ),
                            "reason": str(exc),
                            "exception": (
                                type(exc).__name__
                            ),
                            "traceback": (
                                traceback.format_exc()
                            ),
                        }
                    )

            # ====================================================
            # SUCCESSFUL DEVICE
            # ====================================================

            processed.append(
                {
                    "ip_address": ip_address,
                    "hostname": hostname,
                    "status": device.status,
                    "action": action,
                    "device_id": device.id,
                    "latency_ms": latency_ms,
                }
            )

        # ========================================================
        # DATABASE ERROR
        # ========================================================

        except Exception as exc:

            errors.append(
                {
                    "ip_address": ip_address,
                    "hostname": hostname,
                    "error": "Database operation failed",
                    "reason": str(exc),
                    "exception": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                }
            )

    # ============================================================
    # RESPONSE
    # ============================================================

    success = len(errors) == 0

    return JsonResponse(
        {
            "success": success,
            "message": (
                "Device discovery completed."
                if success
                else "Device discovery completed with errors."
            ),
            "received": len(devices),
            "processed": len(processed),
            "created": created_count,
            "updated": updated_count,
            "ping_results": ping_count,
            "errors": errors,
            "devices": processed,
            "timestamp": now.isoformat(),
        },
        status=200 if success else 207,
    )