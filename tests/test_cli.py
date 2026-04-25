from typer.testing import CliRunner

from groupdocs_viewer_ui import __version__
from groupdocs_viewer_ui.cli import cli


def test_version_command_prints_package_version():
    result = CliRunner().invoke(cli, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_serve_rejects_bad_files_dir(tmp_path):
    bogus = tmp_path / "does-not-exist"
    result = CliRunner().invoke(cli, ["serve", "--files", str(bogus)])
    assert result.exit_code == 1
    assert "is not a directory" in (result.stderr or result.stdout)


def test_serve_rejects_bad_rendering_mode(tmp_path):
    result = CliRunner().invoke(
        cli, ["serve", "--files", str(tmp_path), "--rendering-mode", "vector"]
    )
    assert result.exit_code == 1
    assert "rendering-mode" in (result.stderr or result.stdout)


def test_help_lists_commands():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "serve" in result.stdout
    assert "version" in result.stdout
