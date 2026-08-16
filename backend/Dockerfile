FROM python:3.11-slim

RUN set -eux; \
    for file in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources; do \
      [ -f "$file" ] || continue; \
      sed -i \
        -e 's|http://deb.debian.org/debian|http://mirrors.tencentyun.com/debian|g' \
        -e 's|http://deb.debian.org/debian-security|http://mirrors.tencentyun.com/debian-security|g' \
        "$file"; \
    done; \
    apt-get update; \
    apt-get install -y curl; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --index-url https://mirrors.cloud.tencent.com/pypi/simple \
    --trusted-host mirrors.cloud.tencent.com \
    -r requirements.txt

COPY . .

CMD ["python", "server.py"]
