from django.shortcuts import render
from django.shortcuts import render


def dashboard(request):
    context = {
        "device_count": 0,
        "online_count": 0,
        "offline_count": 0,
        "network_status": "Healthy",
    }

    return render(
        request,
        "index.html",
        context,
    )