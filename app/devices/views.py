from django.shortcuts import get_object_or_404, render

from .models import Device


def device_detail(request, device_id):
    device = get_object_or_404(
        Device,
        id=device_id,
    )

    ping_results = device.ping_results.all()[:50]

    events = device.network_events.all()[:50]

    return render(
        request,
        "detail.html",
        {
            "device": device,
            "ping_results": ping_results,
            "events": events,
        },
    )