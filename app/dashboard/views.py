from django.shortcuts import render

from devices.models import Device


def index(request):

    # Get ALL devices from the database
    devices = Device.objects.all().order_by(
        "ip_address"
    )

    # Counts
    total_devices = devices.count()

    online_count = devices.filter(
        status=Device.Status.ONLINE
    ).count()

    offline_count = devices.filter(
        status=Device.Status.OFFLINE
    ).count()

    unknown_count = devices.filter(
        status=Device.Status.UNKNOWN
    ).count()

    context = {
        "devices": devices,
        "total_devices": total_devices,
        "online_count": online_count,
        "offline_count": offline_count,
        "unknown_count": unknown_count,
    }

    return render(
        request,
        "index.html",
        context,
    )