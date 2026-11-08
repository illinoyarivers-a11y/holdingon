FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    tcl \
    tcllib \
    tdom \
    tcl-tls \
    zip \
    imagemagick \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
EXPOSE 8000
CMD ["python3", "backend/server.py"]
