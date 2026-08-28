import ipaddress
import os
import platform
import socket
import subprocess
import time

import requests


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = os.getenv(
    "NETWATCH_API_URL",
    "http://web:8000/api/devices/discover/",
)

SCAN_INTERVAL = int(
    os.getenv(
        "SCAN_INTERVAL",
        "60",
    )
)


# ============================================================
# NETWORK DETECTION
# ============================================================

def get_local_network():
    """
    Determine the local network.

    LOCAL_NETWORK can be supplied through Docker
    environment variables.

    Example:

        LOCAL_NETWORK=192.168.1.0/24

    On macOS, the Docker development environment
    can attempt to determine the gateway.
    """

    configured_network = os.getenv(
        "LOCAL_NETWORK"
    )

    if configured_network:

        return ipaddress.ip_network(
            configured_network,
            strict=False,
        )

    system = platform.system()

    if system == "Darwin":

        result = subprocess.run(
            [
                "route",
                "-n",
                "get",
                "default",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        gateway = None

        for line in result.stdout.splitlines():

            if "gateway:" in line:

                gateway = (
                    line
                    .split("gateway:")[1]
                    .strip()
                )

        if gateway:

            gateway_ip = ipaddress.ip_address(
                gateway
            )

            network = ipaddress.ip_network(
                f"{gateway_ip}/24",
                strict=False,
            )

            return network

    raise RuntimeError(
        "Unable to determine local network. "
        "Set LOCAL_NETWORK, e.g. "
        "192.168.1.0/24"
    )


# ============================================================
# PING
# ============================================================

def ping_host(ip):
    """
    Ping a host.

    Returns:

        (True, latency_ms)

    or:

        (False, None)
    """

    system = platform.system()

    if system == "Windows":

        command = [
            "ping",
            "-n",
            "1",
            "-w",
            "1000",
            str(ip),
        ]

    else:

        command = [
            "ping",
            "-c",
            "1",
            "-W",
            "1",
            str(ip),
        ]

    start = time.perf_counter()

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

    except FileNotFoundError:

        print(
            "ERROR: ping command not found.",
            flush=True,
        )

        return False, None

    elapsed = (
        time.perf_counter() - start
    ) * 1000

    if result.returncode == 0:

        return (
            True,
            round(elapsed, 2),
        )

    return False, None


# ============================================================
# HOSTNAME LOOKUP
# ============================================================

def resolve_hostname(ip):
    """
    Attempt reverse DNS lookup.
    """

    try:

        hostname, _, _ = socket.gethostbyaddr(
            str(ip)
        )

        return hostname

    except (
        socket.herror,
        socket.gaierror,
        OSError,
    ):

        return ""


# ============================================================
# SEND EVENT TO NETWATCH
# ============================================================

def send_event(
    event_type,
    message,
    severity="info",
    ip_address=None,
):
    """
    Send a scanner event to the NetWatch API.
    """

    try:

        # Convert the discovery API URL into
        # the general API base.

        api_base = API_URL.rsplit(
            "/",
            2,
        )[0]

        event_url = (
            f"{api_base}/events/"
        )

        payload = {
            "event_type": event_type,
            "message": message,
            "severity": severity,
        }

        if ip_address:

            payload["ip_address"] = (
                ip_address
            )

        response = requests.post(
            event_url,
            json=payload,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("success"):

            print(
                f"EVENT: {message}",
                flush=True,
            )

            return True

        print(
            f"EVENT ERROR: {data}",
            flush=True,
        )

        return False

    except requests.RequestException as exc:

        print(
            f"Unable to send event: {exc}",
            flush=True,
        )

        return False

    except Exception as exc:

        print(
            "Unexpected event error: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        return False


# ============================================================
# SEND DEVICE TO API
# ============================================================

def send_device(device):
    """
    Send a single discovered device to NetWatch.
    """

    try:

        response = requests.post(
            API_URL,
            json={
                "devices": [
                    device
                ],
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("success"):

            print(
                "DEVICE SENT: "
                f"{device['ip_address']}",
                flush=True,
            )

            return True

        print(
            f"DEVICE API ERROR: {data}",
            flush=True,
        )

        return False

    except requests.RequestException as exc:

        print(
            f"Unable to send device: {exc}",
            flush=True,
        )

        return False

    except Exception as exc:

        print(
            "Unexpected device API error: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        return False


# ============================================================
# SCAN NETWORK
# ============================================================

def scan_network(network):
    """
    Scan the supplied network for live devices.
    """

    print(
        "",
        flush=True,
    )

    print(
        "=" * 60,
        flush=True,
    )

    print(
        f"Scanning network: {network}",
        flush=True,
    )

    print(
        "=" * 60,
        flush=True,
    )

    # --------------------------------------------------------
    # SCAN START EVENT
    # --------------------------------------------------------

    send_event(
        event_type="scan_started",
        message=(
            f"Network scan started: "
            f"{network}"
        ),
        severity="info",
    )

    discovered = []

    # --------------------------------------------------------
    # SCAN EVERY HOST
    # --------------------------------------------------------

    for ip in network.hosts():

        print(
            f"Checking {ip}...",
            flush=True,
        )

        alive, latency = ping_host(ip)

        if not alive:

            continue

        # ----------------------------------------------------
        # HOSTNAME
        # ----------------------------------------------------

        hostname = resolve_hostname(
            ip
        )

        # ----------------------------------------------------
        # DEVICE DATA
        # ----------------------------------------------------

        device = {
            "ip_address": str(ip),
            "hostname": hostname,
            "latency_ms": latency,
        }

        discovered.append(
            device
        )

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        print(
            f"FOUND {ip} "
            f"{hostname or 'Unknown'} "
            f"{latency}ms",
            flush=True,
        )

        # ----------------------------------------------------
        # SEND DEVICE TO API
        # ----------------------------------------------------

        send_device(
            device
        )

        # ----------------------------------------------------
        # LOG DISCOVERY EVENT
        # ----------------------------------------------------

        send_event(
            event_type="device_discovered",
            message=(
                f"Device discovered: "
                f"{hostname or ip}"
            ),
            severity="info",
            ip_address=str(ip),
        )

    # --------------------------------------------------------
    # SCAN COMPLETE EVENT
    # --------------------------------------------------------

    send_event(
        event_type="scan_completed",
        message=(
            f"Network scan completed: "
            f"{len(discovered)} devices found"
        ),
        severity="info",
    )

    print(
        "",
        flush=True,
    )

    print(
        f"Scan complete. "
        f"{len(discovered)} devices found.",
        flush=True,
    )

    return discovered


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 60,
        flush=True,
    )

    print(
        "NetWatch Network Scanner",
        flush=True,
    )

    print(
        "=" * 60,
        flush=True,
    )

    # --------------------------------------------------------
    # DETERMINE NETWORK
    # --------------------------------------------------------

    try:

        network = get_local_network()

    except Exception as exc:

        print(
            "NETWORK DETECTION ERROR: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        send_event(
            event_type="error",
            message=(
                "Unable to determine "
                f"local network: {exc}"
            ),
            severity="critical",
        )

        return

    print(
        f"Network detected: {network}",
        flush=True,
    )

    print(
        f"Scan interval: "
        f"{SCAN_INTERVAL} seconds",
        flush=True,
    )

    # --------------------------------------------------------
    # CONTINUOUS SCANNING
    # --------------------------------------------------------

    while True:

        try:

            devices = scan_network(
                network
            )

            print(
                f"Discovered "
                f"{len(devices)} devices.",
                flush=True,
            )

        except Exception as exc:

            print(
                "SCANNER ERROR: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

            send_event(
                event_type="error",
                message=(
                    f"Scanner error: {exc}"
                ),
                severity="critical",
            )

        print(
            "",
            flush=True,
        )

        print(
            f"Waiting "
            f"{SCAN_INTERVAL} seconds...",
            flush=True,
        )

        time.sleep(
            SCAN_INTERVAL
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
