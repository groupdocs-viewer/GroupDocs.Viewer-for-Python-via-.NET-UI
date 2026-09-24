# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Native libraries needed by groupdocs.viewer's bundled .NET runtime + the
# image-rendering path:
#   - .NET runtime deps  : libicu72, libssl3, libgcc-s1, libgssapi-krb5-2,
#                          liblttng-ust1, zlib1g, ca-certificates  (per
#                          Microsoft's "Install .NET on Debian 12" docs).
#                          The python:slim base ships only the bare minimum;
#                          without these the runtime aborts at init time
#                          inside `_resolve_bridge_functions`.
#   - Fonts              : fonts-liberation gives Arial/Times metric-compatible
#                          fallbacks, and ttf-mscorefonts-installer the real
#                          Microsoft core fonts. The latter became necessary in
#                          26.9, which renders MS Project files on Linux: without
#                          them MPP/MPT/MPX fail with "Cannot find fallback font
#                          'Generic Sans Serif'", and Liberation does not satisfy
#                          that lookup. It lives in Debian "contrib" (enabled
#                          below) and its EULA is pre-accepted via debconf.
# Package names are pinned to Debian 13 (trixie) — the base of python:3.12-slim
# at the time of writing. If the Python image bumps to a newer Debian, the
# `libicu76` / `libssl3t64` names may need to bump in lockstep.
RUN sed -i 's/^Components: main$/Components: main contrib/' /etc/apt/sources.list.d/debian.sources \
    && echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections \
    && apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        libicu76 \
        libssl3t64 \
        libgcc-s1 \
        libgssapi-krb5-2 \
        zlib1g \
        libstdc++6 \
        libfontconfig1 \
        fontconfig \
        fonts-dejavu \
        fonts-liberation \
        wget \
        ttf-mscorefonts-installer \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*
# No libgdiplus: since groupdocs-viewer-net 26.9 no render path needs it,
# thumbnails (PNG width) included -- measured in a container without it.

WORKDIR /app

# Install package metadata + sources. The groupdocs-viewer-net wheel is ~185MB,
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
