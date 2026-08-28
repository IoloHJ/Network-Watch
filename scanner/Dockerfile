FROM python:3.12-slim

WORKDIR /scanner

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        iputils-ping \
        iproute2 \
        dnsutils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY scanner.py .

CMD ["python", "scanner.py"]
