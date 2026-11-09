import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from controllers.DataController import DataController
from models.enums import ResponseSignal


@pytest.fixture
def controller():
    """Instantiate DataController without triggering BaseController settings loading."""
    with patch('controllers.BaseController.BaseController.__init__', return_value=None):
        ctrl = DataController()
        # Settings normally injected by BaseController.__init__
        ctrl.app_settings = MagicMock()
        ctrl.app_settings.FILE_ALLOWED_EXTENTIONS = ["application/pdf", "text/plain"]
        ctrl.app_settings.FILE_MAX_SIZE_IN_MB = 10
        yield ctrl


def _make_upload_file(filename, content_type, size):
    f = MagicMock()
    f.filename = filename
    f.content_type = content_type
    f.size = size
    return f


# ------------------------------------------------------------------- #
# validate()  -> content_type, then extension, then size
# ------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_validate_accepts_allowed_pdf(controller):
    file = _make_upload_file("doc.pdf", "application/pdf", size=1024)
    is_valid, signal = await controller.validate(file)
    assert is_valid is True
    assert signal == ResponseSignal.FILE_VALIDATED_SUCCESS.value


@pytest.mark.asyncio
async def test_validate_accepts_allowed_txt(controller):
    file = _make_upload_file("notes.txt", "text/plain", size=512)
    is_valid, signal = await controller.validate(file)
    assert is_valid is True
    assert signal == ResponseSignal.FILE_VALIDATED_SUCCESS.value


@pytest.mark.asyncio
async def test_validate_rejects_disallowed_content_type(controller):
    file = _make_upload_file("doc.pdf", "application/x-msdownload", size=1024)
    is_valid, signal = await controller.validate(file)
    assert is_valid is False
    assert signal == ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value


@pytest.mark.asyncio
async def test_validate_rejects_disallowed_extension(controller):
    # content_type is allowed, but extension is not .txt/.pdf -> still rejected
    file = _make_upload_file("malware.exe", "application/pdf", size=1024)
    is_valid, signal = await controller.validate(file)
    assert is_valid is False
    assert signal == ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value


@pytest.mark.asyncio
async def test_validate_rejects_oversized_file(controller):
    # FILE_MAX_SIZE_IN_MB=10 -> max bytes = 10 * 1048576
    too_big = (10 * 1048576) + 1
    file = _make_upload_file("doc.pdf", "application/pdf", size=too_big)
    is_valid, signal = await controller.validate(file)
    assert is_valid is False
    assert signal == ResponseSignal.FILE_SIZE_EXCEEDED.value


# ------------------------------------------------------------------- #
# __cleaned_filename()  (private, accessed via name mangling)
# ------------------------------------------------------------------- #
def test_cleaned_filename_removes_special_chars(controller):
    cleaned = controller._DataController__cleaned_filename("my file (v2)!.txt")
    assert cleaned == "myfilev2.txt"


def test_cleaned_filename_keeps_dots_and_word_chars(controller):
    cleaned = controller._DataController__cleaned_filename("report_2024.pdf")
    assert cleaned == "report_2024.pdf"


# ------------------------------------------------------------------- #
# gen_unique_filename()  -> random prefix + '_' + cleaned name
# ------------------------------------------------------------------- #
def test_gen_unique_filename_no_collision(controller):
    controller._gen_rand_str = MagicMock(return_value="abc")
    controller.join_path = MagicMock(side_effect=lambda p, f: os.path.join(p, f))

    with patch("os.path.exists", return_value=False):
        result = controller.gen_unique_filename("mydoc.pdf", "/tmp/proj")

    assert result == "abc_mydoc.pdf"
    controller._gen_rand_str.assert_called_once_with(length=1)


def test_gen_unique_filename_increments_on_collision(controller):
    # first candidate collides -> prefix length grows and a new random string is drawn
    controller._gen_rand_str = MagicMock(side_effect=["a", "bb"])
    controller.join_path = MagicMock(side_effect=lambda p, f: os.path.join(p, f))

    with patch("os.path.exists", side_effect=[True, False]):
        result = controller.gen_unique_filename("doc.pdf", "/tmp/proj")

    assert result == "bb_doc.pdf"
    assert controller._gen_rand_str.call_count == 2