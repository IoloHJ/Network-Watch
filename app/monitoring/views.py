from django.shortcuts import render

from devices.models import NetworkEvent,Device


def events(request):

    network_events = (
        NetworkEvent.objects
        .select_related("device")
        .all()[:200]
    )

    return render(
        request,
        "events.html",
        {
            "events": network_events,
        },
    )