import pytest

from groupdocs_viewer_ui.api.url_builder import ApiUrlBuilder


def test_relative_page_url():
    b = ApiUrlBuilder()
    assert b.build_page_url("sample.docx", 3) == "/get-page?file=sample.docx&page=3"


def test_relative_thumb_url():
    b = ApiUrlBuilder()
    assert b.build_thumb_url("a.pdf", 1) == "/get-thumb?file=a.pdf&page=1"


def test_relative_pdf_url():
    b = ApiUrlBuilder()
    assert b.build_pdf_url("a.pdf") == "/get-pdf?file=a.pdf"


def test_relative_resource_url():
    b = ApiUrlBuilder()
    assert (
        b.build_resource_url("a.pdf", 2, "styles.css")
        == "/get-resource?file=a.pdf&page=2&resource=styles.css"
    )


def test_absolute_url():
    b = ApiUrlBuilder(
        use_absolute_urls=True, api_domain="https://example.com", api_path="viewer-api"
    )
    assert (
        b.build_thumb_url("a.pdf", 1)
        == "https://example.com/viewer-api/get-thumb?file=a.pdf&page=1"
    )


def test_absolute_url_trims_trailing_slash():
    b = ApiUrlBuilder(
        use_absolute_urls=True, api_domain="https://example.com/", api_path="/viewer-api/"
    )
    assert (
        b.build_pdf_url("a.pdf")
        == "https://example.com/viewer-api/get-pdf?file=a.pdf"
    )


def test_absolute_without_domain_raises():
    b = ApiUrlBuilder(use_absolute_urls=True)
    with pytest.raises(ValueError):
        b.build_pdf_url("a.pdf")


def test_special_characters_are_url_encoded():
    b = ApiUrlBuilder()
    # Forward-slash in file path gets percent-encoded; space becomes '+' (urlencode default).
    assert (
        b.build_page_url("subdir/a b.docx", 1)
        == "/get-page?file=subdir%2Fa+b.docx&page=1"
    )


def test_resource_url_template_includes_api_path_and_placeholders():
    b = ApiUrlBuilder(api_path="viewer-api")
    template = b.build_resource_url_template("docs/a.docx")
    # Note the ``{0}`` and ``{1}`` placeholders are NOT URL-encoded — they
    # are substituted by groupdocs.viewer at render time.
    assert (
        template
        == "/viewer-api/get-resource?file=docs%2Fa.docx&page={0}&resource={1}"
    )


def test_resource_url_template_with_absolute_urls():
    b = ApiUrlBuilder(
        api_path="viewer-api",
        use_absolute_urls=True,
        api_domain="https://example.com",
    )
    template = b.build_resource_url_template("a.docx")
    assert (
        template
        == "https://example.com/viewer-api/get-resource?file=a.docx&page={0}&resource={1}"
    )
