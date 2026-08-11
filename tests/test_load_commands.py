from types import SimpleNamespace
from unittest.mock import Mock

from mopidy.models import Track

from mopiqtt.frontend import MopiqttFrontend


class Future:
    def __init__(self, value=None, exception=None):
        self.value = value
        self.exception = exception

    def get(self):
        if self.exception:
            raise self.exception
        return self.value


class Tracklist:
    def __init__(
        self,
        tracks,
        fail_next_clear=False,
        fail_next_add=False,
        fail_shuffle=False,
    ):
        self.tracks = list(tracks)
        self.version = 0
        self.next_tlid = 1
        self.fail_next_clear = fail_next_clear
        self.fail_next_add = fail_next_add
        self.fail_shuffle = fail_shuffle
        self.get_version = Mock(side_effect=self._get_version)
        self.get_tracks = Mock(side_effect=self._get_tracks)
        self.clear = Mock(side_effect=self._clear)
        self.add = Mock(side_effect=self._add)
        self.shuffle = Mock(side_effect=self._shuffle)

    def _get_version(self):
        return Future(self.version)

    def _get_tracks(self):
        return Future(list(self.tracks))

    def _clear(self):
        self.tracks = []
        self.version += 1
        if self.fail_next_clear:
            self.fail_next_clear = False
            return Future(exception=RuntimeError("clear failed"))
        return Future()

    def _add(self, tracks=None, *, at_position=None, uris=None):
        tracks = list(tracks or [])
        if self.fail_next_add:
            self.fail_next_add = False
            if tracks:
                self.tracks.append(tracks[0])
                self.version += 1
            return Future(exception=RuntimeError("add failed"))
        tl_tracks = []
        for track in tracks:
            self.tracks.append(track)
            tl_tracks.append(SimpleNamespace(tlid=self.next_tlid, track=track))
            self.next_tlid += 1
        if tl_tracks:
            self.version += 1
        return Future(tl_tracks)

    def _shuffle(self, start=None, end=None):
        self.tracks.reverse()
        self.version += 1
        if self.fail_shuffle:
            return Future(exception=RuntimeError("shuffle failed"))
        return Future()


def make_frontend(
    initial_tracks,
    playlist_items=None,
    lookup=None,
    fail_clear=False,
    fail_add=False,
    fail_shuffle=False,
    fail_play=False,
):
    tracklist = Tracklist(
        initial_tracks,
        fail_next_clear=fail_clear,
        fail_next_add=fail_add,
        fail_shuffle=fail_shuffle,
    )
    get_items = Mock(return_value=Future(playlist_items))
    library_lookup = Mock(return_value=Future(lookup))
    play_result = Future(exception=RuntimeError("play failed")) if fail_play else Future()
    playback = SimpleNamespace(play=Mock(return_value=play_result))

    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(
        playlists=SimpleNamespace(get_items=get_items),
        library=SimpleNamespace(lookup=library_lookup),
        tracklist=tracklist,
        playback=playback,
    )
    return frontend, tracklist, get_items, library_lookup, playback


def test_pload_replaces_queue_after_full_validation():
    previous = Track(name="Previous", uri="test:previous")
    loaded = Track(name="Loaded", uri="test:loaded")
    item = SimpleNamespace(uri=loaded.uri)
    frontend, tracklist, _, lookup, playback = make_frontend(
        [previous], playlist_items=[item], lookup={loaded.uri: [loaded]}
    )

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [loaded]
    lookup.assert_called_once_with(uris=[loaded.uri])
    tracklist.add.assert_called_once_with(tracks=[loaded])
    playback.play.assert_called_once_with()


def test_pload_keeps_queue_when_playlist_does_not_exist():
    previous = Track(name="Previous", uri="test:previous")
    frontend, tracklist, get_items, lookup, playback = make_frontend(
        [previous], playlist_items=None
    )

    frontend.on_action_pload("test:missing")

    assert tracklist.tracks == [previous]
    get_items.assert_called_once_with("test:missing")
    lookup.assert_not_called()
    tracklist.clear.assert_not_called()
    playback.play.assert_not_called()


def test_pload_keeps_queue_when_playlist_is_empty():
    previous = Track(name="Previous", uri="test:previous")
    frontend, tracklist, _, lookup, playback = make_frontend(
        [previous], playlist_items=[]
    )

    frontend.on_action_pload("test:empty")

    assert tracklist.tracks == [previous]
    lookup.assert_not_called()
    tracklist.clear.assert_not_called()
    playback.play.assert_not_called()


def test_pload_keeps_queue_when_playlist_item_has_no_uri():
    previous = Track(name="Previous", uri="test:previous")
    frontend, tracklist, _, lookup, playback = make_frontend(
        [previous], playlist_items=[SimpleNamespace()]
    )

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [previous]
    lookup.assert_not_called()
    tracklist.clear.assert_not_called()
    playback.play.assert_not_called()


def test_pload_skips_unresolved_playlist_items_and_keeps_valid_order(caplog):
    previous = Track(name="Previous", uri="test:previous")
    valid = Track(name="Valid", uri="test:valid")
    missing_uri = "test:missing"
    items = [SimpleNamespace(uri=valid.uri), SimpleNamespace(uri=missing_uri)]
    frontend, tracklist, _, lookup, playback = make_frontend(
        [previous],
        playlist_items=items,
        lookup={valid.uri: [valid], missing_uri: []},
    )

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [valid]
    lookup.assert_called_once_with(uris=[valid.uri, missing_uri])
    playback.play.assert_called_once_with()
    assert "contains 2 tracks; 1 could not be resolved and were skipped" in caplog.text
    assert f"Skipped unresolved track: {missing_uri}" in caplog.text


def test_pload_keeps_queue_when_all_playlist_items_are_unresolved(caplog):
    previous = Track(name="Previous", uri="test:previous")
    missing_uris = ["test:missing-1", "test:missing-2"]
    items = [SimpleNamespace(uri=item_uri) for item_uri in missing_uris]
    frontend, tracklist, _, _, playback = make_frontend(
        [previous], playlist_items=items, lookup={item_uri: [] for item_uri in missing_uris}
    )

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [previous]
    tracklist.clear.assert_not_called()
    playback.play.assert_not_called()
    assert "No tracks could be resolved for playlist: test:playlist" in caplog.text


def test_pload_preserves_order_and_duplicate_items():
    previous = Track(name="Previous", uri="test:previous")
    first = Track(name="First", uri="test:first")
    second = Track(name="Second", uri="test:second")
    items = [
        SimpleNamespace(uri=first.uri),
        SimpleNamespace(uri=second.uri),
        SimpleNamespace(uri=first.uri),
    ]
    frontend, tracklist, _, lookup, _ = make_frontend(
        [previous],
        playlist_items=items,
        lookup={first.uri: [first], second.uri: [second]},
    )

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [first, second, first]
    lookup.assert_called_once_with(uris=[first.uri, second.uri, first.uri])


def test_pload_accepts_playlist_containing_stream():
    previous = Track(name="Previous", uri="test:previous")
    stream = Track(name="Stream", uri="https://example.com/radio")
    frontend, tracklist, _, _, playback = make_frontend(
        [previous],
        playlist_items=[SimpleNamespace(uri=stream.uri)],
        lookup={stream.uri: [stream]},
    )

    frontend.on_action_pload("test:streams")

    assert tracklist.tracks == [stream]
    playback.play.assert_called_once_with()


def test_ploadshfl_replaces_and_shuffles_valid_playlist():
    previous = Track(name="Previous", uri="test:previous")
    first = Track(name="First", uri="test:first")
    second = Track(name="Second", uri="test:second")
    items = [SimpleNamespace(uri=first.uri), SimpleNamespace(uri=second.uri)]
    frontend, tracklist, _, _, playback = make_frontend(
        [previous],
        playlist_items=items,
        lookup={first.uri: [first], second.uri: [second]},
    )

    frontend.on_action_ploadshfl("test:playlist")

    assert sorted(track.uri for track in tracklist.tracks) == sorted(
        [first.uri, second.uri]
    )
    tracklist.shuffle.assert_called_once_with()
    playback.play.assert_called_once_with()


def test_ploadshfl_skips_unresolved_items_before_shuffling():
    previous = Track(name="Previous", uri="test:previous")
    valid = Track(name="Valid", uri="test:valid")
    missing_uri = "test:missing"
    items = [SimpleNamespace(uri=missing_uri), SimpleNamespace(uri=valid.uri)]
    frontend, tracklist, _, _, playback = make_frontend(
        [previous],
        playlist_items=items,
        lookup={missing_uri: [], valid.uri: [valid]},
    )

    frontend.on_action_ploadshfl("test:playlist")

    assert tracklist.tracks == [valid]
    tracklist.shuffle.assert_called_once_with()
    playback.play.assert_called_once_with()


def test_pstream_replaces_queue_after_validation():
    previous = Track(name="Previous", uri="test:previous")
    stream = Track(name="Stream", uri="https://example.com/radio")
    frontend, tracklist, _, lookup, playback = make_frontend(
        [previous], lookup={stream.uri: [stream]}
    )

    frontend.on_action_pstream(stream.uri)

    assert tracklist.tracks == [stream]
    lookup.assert_called_once_with(uris=[stream.uri])
    playback.play.assert_called_once_with()


def test_pstream_keeps_queue_when_stream_is_invalid():
    previous = Track(name="Previous", uri="test:previous")
    stream_uri = "https://example.com/missing"
    frontend, tracklist, _, _, playback = make_frontend(
        [previous], lookup={stream_uri: []}
    )

    frontend.on_action_pstream(stream_uri)

    assert tracklist.tracks == [previous]
    tracklist.clear.assert_not_called()
    playback.play.assert_not_called()


def test_playlist_lookup_error_keeps_queue():
    previous = Track(name="Previous", uri="test:previous")
    item = SimpleNamespace(uri="test:unavailable")
    frontend, tracklist, _, lookup, playback = make_frontend(
        [previous], playlist_items=[item]
    )
    lookup.return_value = Future(exception=RuntimeError("lookup failed"))

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [previous]
    tracklist.clear.assert_not_called()
    playback.play.assert_not_called()


def test_get_items_error_keeps_queue():
    previous = Track(name="Previous", uri="test:previous")
    frontend, tracklist, get_items, lookup, playback = make_frontend([previous])
    get_items.return_value = Future(exception=RuntimeError("get_items failed"))

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [previous]
    lookup.assert_not_called()
    tracklist.clear.assert_not_called()
    playback.play.assert_not_called()


def test_clear_error_restores_previous_queue():
    previous = Track(name="Previous", uri="test:previous")
    loaded = Track(name="Loaded", uri="test:loaded")
    frontend, tracklist, _, _, playback = make_frontend(
        [previous],
        playlist_items=[SimpleNamespace(uri=loaded.uri)],
        lookup={loaded.uri: [loaded]},
        fail_clear=True,
    )

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [previous]
    assert tracklist.clear.call_count == 2
    playback.play.assert_not_called()


def test_loading_error_restores_previous_queue():
    previous = Track(name="Previous", uri="test:previous")
    loaded = Track(name="Loaded", uri="test:loaded")
    item = SimpleNamespace(uri=loaded.uri)
    frontend, tracklist, _, _, playback = make_frontend(
        [previous],
        playlist_items=[item],
        lookup={loaded.uri: [loaded]},
        fail_add=True,
    )

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [previous]
    assert tracklist.clear.call_count == 2
    assert tracklist.add.call_count == 2
    playback.play.assert_not_called()


def test_shuffle_error_restores_previous_queue():
    previous = Track(name="Previous", uri="test:previous")
    loaded = Track(name="Loaded", uri="test:loaded")
    item = SimpleNamespace(uri=loaded.uri)
    frontend, tracklist, _, _, playback = make_frontend(
        [previous],
        playlist_items=[item],
        lookup={loaded.uri: [loaded]},
        fail_shuffle=True,
    )

    frontend.on_action_ploadshfl("test:playlist")

    assert tracklist.tracks == [previous]
    playback.play.assert_not_called()


def test_playback_error_restores_previous_queue():
    previous = Track(name="Previous", uri="test:previous")
    stream = Track(name="Stream", uri="https://example.com/radio")
    frontend, tracklist, _, _, playback = make_frontend(
        [previous],
        lookup={stream.uri: [stream]},
        fail_play=True,
    )

    frontend.on_action_pstream(stream.uri)

    assert tracklist.tracks == [previous]
    playback.play.assert_called_once_with()


def test_concurrent_tracklist_change_aborts_before_clear():
    previous = Track(name="Previous", uri="test:previous")
    loaded = Track(name="Loaded", uri="test:loaded")
    frontend, tracklist, _, _, playback = make_frontend(
        [previous],
        playlist_items=[SimpleNamespace(uri=loaded.uri)],
        lookup={loaded.uri: [loaded]},
    )
    tracklist.get_version.side_effect = [Future(0), Future(1)]

    frontend.on_action_pload("test:playlist")

    assert tracklist.tracks == [previous]
    tracklist.clear.assert_not_called()
    playback.play.assert_not_called()
