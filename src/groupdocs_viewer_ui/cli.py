"""``groupdocs-viewer-ui`` command-line entry point."""
from __future__ import annotations

import sys
from pathlib import Path

import typer
import uvicorn

from groupdocs_viewer_ui import __version__, create_app
from groupdocs_viewer_ui.api.url_builder import ApiUrlBuilder
from groupdocs_viewer_ui.cache.local import LocalFileCache
from groupdocs_viewer_ui.config import Config
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer

cli = typer.Typer(
    add_completion=False,
    help="Web UI for groupdocs-viewer-net.",
    no_args_is_help=True,
)


@cli.command()
def serve(
    files: Path = typer.Option(
        Path.cwd(),
        "--files",
        "-f",
        help="Directory containing documents to browse and view.",
    ),
    cache: Path | None = typer.Option(
        None,
        "--cache",
        "-c",
        help="Directory for the on-disk render cache. Disabled if omitted.",
    ),
    host: str = typer.Option("127.0.0.1", "--host", "-H"),
    port: int = typer.Option(8080, "--port", "-p"),
    rendering_mode: str = typer.Option(
        "html",
        "--rendering-mode",
        "-m",
        help="Render documents as 'html' or 'image'.",
    ),
    ui_path: str = typer.Option(
        "/viewer", "--ui-path", help="URL path the SPA is served at."
    ),
    api_path: str = typer.Option(
        "viewer-api", "--api-path", help="URL path the viewer API is served at."
    ),
    html_external_resources: bool = typer.Option(
        False,
        "--html-external-resources/--html-embedded-resources",
        help="Render HTML pages with external CSS/font/image resources "
        "(cacheable across pages) instead of inlining everything.",
    ),
) -> None:
    """Start a development server with the viewer UI."""
    if not files.is_dir():
        typer.echo(f"error: --files {files} is not a directory", err=True)
        raise typer.Exit(1)

    mode_normalized = rendering_mode.strip().lower()
    if mode_normalized not in ("html", "image"):
        typer.echo(
            f"error: --rendering-mode must be 'html' or 'image', got {rendering_mode!r}",
            err=True,
        )
        raise typer.Exit(1)

    config = Config(
        rendering_mode=mode_normalized,  # type: ignore[arg-type]
        ui_path=ui_path,
        api_path=api_path,
    )
    if html_external_resources and mode_normalized != "html":
        typer.echo(
            "error: --html-external-resources is only valid with --rendering-mode html",
            err=True,
        )
        raise typer.Exit(1)

    storage = LocalFileStorage(files)
    cache_obj = LocalFileCache(cache) if cache else None
    url_builder = ApiUrlBuilder(api_path=api_path)
    viewer = SelfHostViewer(
        rendering_mode=mode_normalized,
        storage=storage,
        html_external_resources=html_external_resources,
        resource_url_template_factory=(
            url_builder.build_resource_url_template if html_external_resources else None
        ),
    )

    typer.echo(f"groupdocs-viewer-ui {__version__}")
    typer.echo(f"  files:  {files}")
    typer.echo(f"  cache:  {cache or '(disabled)'}")
    typer.echo(f"  SPA:    http://{host}:{port}{ui_path.rstrip('/')}/")
    typer.echo(f"  API:    http://{host}:{port}/{api_path.strip('/')}")

    uvicorn.run(
        create_app(config, storage=storage, cache=cache_obj, viewer=viewer),
        host=host,
        port=port,
        log_level="info",
    )


@cli.command()
def version() -> None:
    """Print the installed package version."""
    typer.echo(__version__)


def main() -> int:
    cli()
    return 0


if __name__ == "__main__":
    sys.exit(main())
