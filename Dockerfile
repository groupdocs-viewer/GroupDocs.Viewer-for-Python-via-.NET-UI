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
#   - System.Drawing.Common : libgdiplus + libc6-dev (the latter ships some
#                          headers/symbols Gdip dlopens against on Debian).
#   - Fonts              : fonts-liberation gives Arial/Times metric-compatible
#                          fallbacks without the EULA dance the MS Core Fonts
#                          installer requires.
# Package names are pinned to Debian 13 (trixie) — the base of python:3.12-slim
# at the time of writing. If the Python image bumps to a newer Debian, the
# `libicu76` / `libssl3t64` names may need to bump in lockstep.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        libicu76 \
        libssl3t64 \
        libgcc-s1 \
        libgssapi-krb5-2 \
        zlib1g \
        libstdc++6 \
        libgdiplus \
        libc6-dev \
        libfontconfig1 \
        fontconfig \
        fonts-dejavu \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    # .NET's System.Drawing.Common dlopen()s `libgdiplus` (no version suffix);
    # Debian's package only installs `libgdiplus.so.0`. Create the alias so the
    # PNG/JPEG render path can find it.
    && if [ ! -e /usr/lib/x86_64-linux-gnu/libgdiplus.so ]; then \
        ln -s /usr/lib/x86_64-linux-gnu/libgdiplus.so.0 \
              /usr/lib/x86_64-linux-gnu/libgdiplus.so; \
    fi

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
