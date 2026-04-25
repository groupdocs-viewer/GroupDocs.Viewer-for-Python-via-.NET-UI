import json

from groupdocs_viewer_ui.api.contracts import (
    FileSystemItem,
    PageData,
    ViewDataRequest,
    ViewDataResponse,
)


def test_view_data_request_accepts_camel_case():
    req = ViewDataRequest.model_validate(
        {"file": "a.docx", "fileType": "docx", "password": "x"}
    )
    assert req.file == "a.docx"
    assert req.file_type == "docx"
    assert req.password == "x"


def test_view_data_request_tolerates_missing_optional_fields():
    req = ViewDataRequest.model_validate({"file": "a.docx"})
    assert req.file_type is None
    assert req.password is None


def test_file_system_item_serializes_camel_case():
    item = FileSystemItem(path="/a", name="a.docx", is_dir=False, size=42)
    assert item.model_dump(by_alias=True) == {
        "path": "/a",
        "name": "a.docx",
        "isDir": False,
        "size": 42,
    }


def test_page_data_emits_null_urls_when_not_rendered():
    # .NET System.Text.Json includes null values by default, and the SPA
    # checks pageUrl/thumbUrl for truthiness — we must behave the same way.
    page = PageData(number=1, width=100, height=200)
    dumped = page.model_dump(by_alias=True)
    assert dumped["pageUrl"] is None
    assert dumped["thumbUrl"] is None


def test_view_data_response_round_trip():
    resp = ViewDataResponse(
        file="/a.docx",
        file_type="docx",
        file_name="a.docx",
        can_print=True,
        search_term=None,
        pages=[
            PageData(
                number=1,
                width=100,
                height=200,
                page_url="/get-page?file=/a.docx&page=1",
            )
        ],
    )
    payload = json.loads(resp.model_dump_json(by_alias=True))
    assert payload["fileType"] == "docx"
    assert payload["canPrint"] is True
    assert payload["pages"][0]["pageUrl"] == "/get-page?file=/a.docx&page=1"
