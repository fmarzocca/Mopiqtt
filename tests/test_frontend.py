import json
from types import SimpleNamespace
from unittest.mock import Mock

from mopidy.models import SearchResult, Track

from mopiqtt import frontend as frontend_module
from mopiqtt.frontend import MopiqttFrontend


def frontend_with_search_result(result):
    search = Mock(return_value=SimpleNamespace(get=Mock(return_value=result)))
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(library=SimpleNamespace(search=search))
    frontend.mqtt = Mock()
    return frontend


def search(frontend):
    frontend.on_action_search(
        json.dumps({"search": ["song"], "uri_schemes": ["test"]})
    )


def test_frontend_module_loads_with_mopidy4_playback_state():
    assert frontend_module.PlaybackState.__module__ == "mopidy.types"
    assert frontend_module.PlaybackState.PLAYING == "playing"


def test_playback_state_loader_supports_mopidy3(monkeypatch):
    class Mopidy3PlaybackState:
        PAUSED = "paused"
        PLAYING = "playing"
        STOPPED = "stopped"

    def import_mopidy3_module(module_name):
        if module_name == "mopidy.types":
            raise ImportError
        if module_name == "mopidy.audio":
            return SimpleNamespace(PlaybackState=Mopidy3PlaybackState)
        raise AssertionError("Unexpected module: {}".format(module_name))

    monkeypatch.setattr(frontend_module, "import_module", import_mopidy3_module)

    assert frontend_module._load_playback_state() is Mopidy3PlaybackState


def test_search_handles_mopidy4_result():
    result = [SearchResult(tracks=(Track(name="Song", uri="test:song"),))]
    frontend = frontend_with_search_result(result)

    search(frontend)

    frontend.mqtt.publish.assert_called_once_with(
        "search_results", '[{"name": "Song", "uri": "test:song"}]'
    )


def test_search_handles_mopidy3_result():
    result = [
        SimpleNamespace(tracks=[SimpleNamespace(name="Song", uri="test:song")])
    ]
    frontend = frontend_with_search_result(result)

    search(frontend)

    frontend.mqtt.publish.assert_called_once_with(
        "search_results", '[{"name": "Song", "uri": "test:song"}]'
    )


def test_search_handles_empty_result():
    frontend = frontend_with_search_result([])

    search(frontend)

    frontend.mqtt.publish.assert_called_once_with("search_results", "[]")


def test_search_handles_missing_result():
    frontend = frontend_with_search_result(None)

    search(frontend)

    frontend.mqtt.publish.assert_called_once_with("search_results", "[]")


def test_search_handles_result_without_tracks():
    frontend = frontend_with_search_result([SearchResult()])

    search(frontend)

    frontend.mqtt.publish.assert_called_once_with("search_results", "[]")


def test_playback_toggle_accepts_mopidy3_string_state():
    playback = SimpleNamespace(
        get_state=Mock(return_value=SimpleNamespace(get=Mock(return_value="playing"))),
        pause=Mock(),
    )
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(playback=playback)

    frontend.on_action_plb("toggle")

    playback.pause.assert_called_once_with()
