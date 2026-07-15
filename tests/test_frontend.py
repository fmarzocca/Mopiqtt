import json
from types import SimpleNamespace
from unittest.mock import call, Mock

from mopidy.models import Artist, SearchResult, TlTrack, Track

from mopiqtt import frontend as frontend_module
from mopiqtt.frontend import MopiqttFrontend


def frontend_with_search_result(result):
    search = Mock(return_value=SimpleNamespace(get=Mock(return_value=result)))
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(library=SimpleNamespace(search=search))
    frontend.mqtt = Mock()
    return frontend


def future(value=None, exception=None):
    get = Mock(return_value=value)
    if exception is not None:
        get.side_effect = exception
    return SimpleNamespace(get=get)


def search(frontend):
    frontend.on_action_search(
        json.dumps({"search": ["song"], "uri_schemes": ["test"]})
    )


def test_frontend_module_loads_public_playback_state():
    assert frontend_module.PlaybackState.__module__ in {
        "mopidy.audio.constants",
        "mopidy.types",
    }
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
    pause_result = future()
    playback = SimpleNamespace(
        get_state=Mock(return_value=SimpleNamespace(get=Mock(return_value="playing"))),
        pause=Mock(return_value=pause_result),
    )
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(playback=playback)

    frontend.on_action_plb("toggle")

    playback.pause.assert_called_once_with()
    pause_result.get.assert_called_once_with()


def test_mutating_commands_wait_for_actor_futures():
    play_result = future()
    add_result = future()
    clear_result = future()
    refresh_result = future()
    set_volume_result = future()
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(
        mixer=SimpleNamespace(
            set_volume=Mock(return_value=set_volume_result),
        ),
        playback=SimpleNamespace(play=Mock(return_value=play_result)),
        playlists=SimpleNamespace(refresh=Mock(return_value=refresh_result)),
        tracklist=SimpleNamespace(
            add=Mock(return_value=add_result),
            clear=Mock(return_value=clear_result),
        ),
    )

    frontend.on_action_plb("play")
    frontend.on_action_vol("=25")
    frontend.on_action_add("test:track")
    frontend.on_action_clr("")
    frontend.on_action_plrefresh("test")

    play_result.get.assert_called_once_with()
    set_volume_result.get.assert_called_once_with()
    add_result.get.assert_called_once_with()
    clear_result.get.assert_called_once_with()
    refresh_result.get.assert_called_once_with()


def test_change_track_uses_public_tlid_and_waits_for_playback():
    track = Track(name="Track", uri="test:track")
    tl_track = TlTrack(tlid=7, track=track)
    filter_result = future([tl_track])
    play_result = future()
    playback = SimpleNamespace(play=Mock(return_value=play_result))
    tracklist = SimpleNamespace(filter=Mock(return_value=filter_result))
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(playback=playback, tracklist=tracklist)

    frontend.on_action_chgtrk(track.uri)

    tracklist.filter.assert_called_once_with(criteria={"uri": [track.uri]})
    playback.play.assert_called_once_with(tlid=7)
    play_result.get.assert_called_once_with()


def test_tracklist_changed_handles_track_without_name():
    tracks = [
        Track(uri="test:unnamed"),
        Track(
            uri="test:artist-unnamed",
            name="Track",
            artists=frozenset({Artist()}),
        ),
    ]
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(
        tracklist=SimpleNamespace(get_tracks=Mock(return_value=future(tracks)))
    )
    frontend.mqtt = Mock()

    frontend.tracklist_changed()

    frontend.mqtt.publish.assert_called_once_with(
        "trklist",
        '[{"name": "", "uri": "test:unnamed"}, '
        '{"name": "Track", "uri": "test:artist-unnamed"}]',
    )


def test_track_started_handles_missing_tracklist_index():
    track = Track(name="Track", uri="test:track")
    tl_track = TlTrack(tlid=7, track=track)
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(
        library=SimpleNamespace(get_images=Mock(return_value=future({}))),
        tracklist=SimpleNamespace(
            index=Mock(return_value=future(None)),
            get_length=Mock(return_value=future(1)),
        ),
    )
    frontend.defaultImage = "https://example.com/default.jpg"
    frontend.mqtt = Mock()

    frontend.track_playback_started(tl_track)

    assert (
        call("trk-index", '{"current": null, "last": 1}')
        in frontend.mqtt.publish.mock_calls
    )
