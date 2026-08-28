from django.shortcuts import render

from devices.models import Device


def dashboard(request):
    device_count = Device.objects.count()

    online_count = Device.objects.filter(
        status=Device.Status.ONLINE
    ).count()

    offline_count = Device.objects.filter(
        status=Device.Status.OFFLINE
    ).count()

    context = {
        "device_count": device_count,
        "online_count": online_count,
        "offline_count": offline_count,
        "network_status": (
            "Healthy"
            if offline_count == 0
            else "Attention Required"
        ),
    }

    return render(
        request,
        "index.html",
        context,
    )