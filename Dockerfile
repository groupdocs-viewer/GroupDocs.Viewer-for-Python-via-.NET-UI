# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Native libraries that groupdocs.viewer needs for image rendering on Linux.
# fonts-liberation provides Arial/Times metric-compatible fallbacks without
# the EULA dance ttf-mscorefonts-installer would require.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdiplus \
        libfontconfig1 \
        fontconfig \
        fonts-dejavu \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install package metadata + sources. The groupdocs-viewer-net wheel is ~193MB,
# so this layer takes a while on first build but caches well.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

VOLUME ["/docs", "/cache"]
EXPOSE 8080

ENTRYPOINT ["groupdocs-viewer-ui", "serve", \
            "--host", "0.0.0.0", \
            "--port", "8080", \
            "--files", "/docs", \
            "--cache", "/cache"]
