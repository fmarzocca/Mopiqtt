from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mopiqtt.utils import get_track_artwork


DEFAULT_IMAGE = "https://example.com/default.jpg"
TRACK_URI = "test:track"


def frontend_with_artwork(artwork):
    get_images = Mock(return_value=SimpleNamespace(get=Mock(return_value=artwork)))
    frontend = SimpleNamespace(
        core=SimpleNamespace(library=SimpleNamespace(get_images=get_images)),
        defaultImage=DEFAULT_IMAGE,
    )
    return frontend, get_images


def test_artwork_falls_back_when_response_is_missing():
    frontend, _ = frontend_with_artwork(None)

    assert get_track_artwork(frontend, SimpleNamespace(uri=TRACK_URI)) == DEFAULT_IMAGE


def test_artwork_falls_back_when_track_key_is_missing():
    frontend, _ = frontend_with_artwork({})

    assert get_track_artwork(frontend, SimpleNamespace(uri=TRACK_URI)) == DEFAULT_IMAGE


def test_artwork_falls_back_when_image_list_is_empty():
    frontend, _ = frontend_with_artwork({TRACK_URI: ()})

    assert get_track_artwork(frontend, SimpleNamespace(uri=TRACK_URI)) == DEFAULT_IMAGE


def test_artwork_falls_back_for_local_uri():
    frontend, _ = frontend_with_artwork(
        {TRACK_URI: (SimpleNamespace(uri="/local/image.jpg"),)}
    )

    assert get_track_artwork(frontend, SimpleNamespace(uri=TRACK_URI)) == DEFAULT_IMAGE


@pytest.mark.parametrize(
    "image_uri",
    ["http://example.com/image.jpg", "https://example.com/image.jpg"],
)
def test_artwork_preserves_http_uri(image_uri):
    frontend, _ = frontend_with_artwork(
        {TRACK_URI: (SimpleNamespace(uri=image_uri),)}
    )

    assert get_track_artwork(frontend, SimpleNamespace(uri=TRACK_URI)) == image_uri


def test_artwork_falls_back_when_track_has_no_uri():
    frontend, get_images = frontend_with_artwork({})

    assert get_track_artwork(frontend, SimpleNamespace()) == DEFAULT_IMAGE
    get_images.assert_not_called()


def test_artwork_falls_back_when_backend_raises(caplog):
    get_images = Mock(
        return_value=SimpleNamespace(get=Mock(side_effect=RuntimeError("backend failed")))
    )
    frontend = SimpleNamespace(
        core=SimpleNamespace(library=SimpleNamespace(get_images=get_images)),
        defaultImage=DEFAULT_IMAGE,
    )

    assert get_track_artwork(frontend, SimpleNamespace(uri=TRACK_URI)) == DEFAULT_IMAGE
    assert "backend failed" in caplog.text
