from builtins import str
from importlib import import_module
import json
import logging

import pykka
from mopidy.core import CoreListener
from mopidy.models import SearchResult

from .mqtt import Comms
from .utils import describe_track, describe_stream, get_track_artwork


def _load_playback_state():
    for module_name in ("mopidy.types", "mopidy.audio"):
        try:
            module = import_module(module_name)
            return getattr(module, "PlaybackState")
        except (AttributeError, ImportError):
            continue

    raise ImportError("Cannot import PlaybackState from Mopidy")


PlaybackState = _load_playback_state()

log = logging.getLogger(__name__)


VOLUME_MAX = 100
VOLUME_MIN = 0


class MopiqttFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        """
        config (dict): The entire Mopidy configuration.
        core (ActorProxy): Core actor for Mopidy Core API.
        """
        super(MopiqttFrontend, self).__init__()
        self.core = core
        self.mqtt = Comms(frontend=self, **config["mopiqtt"])
        self.defaultImage = (
            "https://upload.wikimedia.org/wikipedia/commons/1/14/No_Image_Available.jpg"
        )

    def on_start(self):
        """
        Hook for doing any setup that should be done *after* the actor is
        started, but *before* it starts processing messages.
        """
        log.debug("Starting MQTT frontend: %s", self)
        self.mqtt.start()

    def on_stop(self):
        """
        Hook for doing any cleanup that should be done *after* the actor has
        processed the last message, and *before* the actor stops.
        """
        log.debug("Stopping MQTT frontend: %s", self)
        self.mqtt.stop()

    def on_failure(self, exception_type, exception_value, traceback):
        """
        Hook for doing any cleanup *after* an unhandled exception is raised,
        and *before* the actor stops.
        """
        log.error("MQTT frontend failed: %s", exception_value)

    @property
    def volume(self):
        return self.core.mixer.get_volume().get()

    @volume.setter
    def volume(self, value):
        # Normalize.
        value = min(value, VOLUME_MAX)
        value = max(value, VOLUME_MIN)
        self.core.mixer.set_volume(value)

    @property
    def current_state(self):
        return self.core.playback.get_state().get()

    def tracklist_changed(self):
        # reports any change to the current tracklist
        # and triggers trklist
        log.debug("MQTT tracklist changed")
        #
        # get list of all tracks in the queue
        #
        tk_list = self.core.tracklist.get_tracks().get()
        tracks = []
        item = {}
        for a in tk_list:
            if a.artists:
                artist = next(iter(a.artists)).name
                item = {"name": artist + " - " + a.name, "uri": a.uri}
            else:
                item = {"name": a.name, "uri": a.uri}
            tracks.append(item)
        self.mqtt.publish("trklist", json.dumps(tracks))
        log.debug("Generated tracklist list")

    def playback_state_changed(self, old_state, new_state):
        """
        old_state (mopidy.core.PlaybackState) - the state before the change.
        new_state (mopidy.core.PlaybackState) - the state after the change.
        """
        log.debug("MQTT playback state changed: %s", new_state)
        self.mqtt.publish("plstate", new_state)

    def track_playback_started(self, tl_track):
        """
        tl_track (mopidy.models.TlTrack) - the track that just started playing.
        """
        log.debug("MQTT track started: %s", tl_track.track)
        self.mqtt.publish("trk", describe_track(tl_track.track))

        # get track's uri
        self.mqtt.publish("trk_uri", tl_track.track.uri)

        # get track's artwork (if any)
        self.mqtt.publish("artw", get_track_artwork(self, tl_track.track))

        # get track playing indexes
        curr = self.core.tracklist.index().get()
        last = self.core.tracklist.get_length().get()
        pl_index = {}
        pl_index["current"] = curr + 1
        pl_index["last"] = last
        pl_index = json.dumps(pl_index)
        self.mqtt.publish("trk-index", pl_index)

    def track_playback_ended(self, tl_track, time_position):
        """
        tl_track (mopidy.models.TlTrack) - the track that was played before
                                           playback stopped.
        time_position (int) - the time position in milliseconds.
        """
        log.debug("MQTT track ended: %s", tl_track.track.name)
        self.mqtt.publish("trk", "")

    def volume_changed(self, volume):
        """
        volume (int) - the new volume in the range [0..100].
        """
        log.debug("MQTT volume changed: %s", volume)
        self.mqtt.publish("vol", str(volume))

    def stream_title_changed(self, title):
        """
        title (string) - the new stream title.
        """
        log.debug("MQTT title changed: %s", title)
        self.mqtt.publish("trk", describe_stream(title))

    def playlists_loaded(self):
        log.debug("Playlists loaded event")
        self.mqtt.publish("refreshed", "")

    def on_action_plb(self, value):
        """Playback control."""
        if value == "play":
            return self.core.playback.play()
        if value == "stop":
            return self.core.playback.stop()
        if value == "pause":
            return self.core.playback.pause()
        if value == "resume":
            return self.core.playback.resume()

        if value == "toggle":
            if self.current_state == PlaybackState.PLAYING:
                return self.core.playback.pause()
            if self.current_state == PlaybackState.PAUSED:
                return self.core.playback.resume()
            if self.current_state == PlaybackState.STOPPED:
                return self.core.playback.play()

        if value == "prev":
            return self.core.playback.previous()
        if value == "next":
            return self.core.playback.next()

        log.warn("Unknown playback control action: %s", value)

    def on_action_vol(self, value):
        """Volume control."""
        if not value or len(value) < 2:
            return log.warn("Invalid volume control parameter: %s", value)

        operator = value[0]
        try:
            amount = int(value[1:])
        except ValueError:
            return log.warn("Invalid volume setting value: %s", value[1:])

        # Exact volume.
        if operator == "=":
            self.volume = amount
            return
        # Volume down.
        if operator == "-":
            self.volume -= amount
            return
        # Volume up.
        if operator == "+":
            self.volume += amount
            return

        log.warn("Unknown volume control operator: %s", operator)

    def on_action_add(self, value):
        """Append URI to queue (tracklist)."""
        if not value:
            return log.warn("Cannot add empty track to queue")

        track = []
        track.append(value)
        self.core.tracklist.add(uris=track)
        log.debug("Added track: %s", value)

    def _resolve_tracks(self, uris):
        if not uris:
            return None

        # Mopidy 3 and 4 implement tracklist.add(uris=...) using this same
        # lookup and flattening each URI in order. Iterating the original URI
        # list here also preserves duplicate playlist entries.
        lookup = self.core.library.lookup(uris=uris).get()
        if not lookup:
            return None

        tracks = []
        for uri in uris:
            uri_tracks = lookup.get(uri)
            if not uri_tracks:
                return None
            tracks.extend(uri_tracks)

        return tracks

    def _restore_tracklist(self, tracks):
        try:
            self.core.tracklist.clear().get()
            if tracks:
                self.core.tracklist.add(tracks=tracks).get()
        except Exception:
            log.exception("Failed to restore previous tracklist")
            return False

        return True

    def _replace_tracklist(self, tracks, shuffle=False):
        try:
            previous_version = self.core.tracklist.get_version().get()
            previous_tracks = self.core.tracklist.get_tracks().get()
            if self.core.tracklist.get_version().get() != previous_version:
                log.warning("Tracklist changed while preparing replacement")
                return False
        except Exception:
            log.exception("Cannot snapshot the current tracklist")
            return False

        try:
            self.core.tracklist.clear().get()
            self.core.tracklist.add(tracks=tracks).get()
            if shuffle:
                self.core.tracklist.shuffle().get()
            self.core.playback.play().get()
        except Exception:
            log.exception("Failed to replace tracklist; restoring previous queue")
            self._restore_tracklist(previous_tracks)
            return False

        return True

    def on_action_pstream(self, value):
        """Load and start a radio stream or a single track (tracklist)."""
        if not value:
            return log.warning("Cannot load empty track to queue")

        try:
            tracks = self._resolve_tracks([value])
        except Exception:
            log.exception("Failed to validate stream: %s", value)
            return

        if not tracks:
            log.info("Invalid stream: %s", value)
            return

        if self._replace_tracklist(tracks):
            log.debug("Started track: %s", value)

    def _get_playlist_tracks(self, uri):
        items = self.core.playlists.get_items(uri).get()
        if not items:
            return None

        uris = []
        for item in items:
            item_uri = getattr(item, "uri", None)
            if not item_uri:
                return None
            uris.append(item_uri)

        return self._resolve_tracks(uris)

    def on_action_pload(self, value):
        """Replace current queue with playlist from URI."""
        if not value:
            return log.warning("Cannot load unnamed playlist")

        try:
            tracks = self._get_playlist_tracks(value)
        except Exception:
            log.exception("Failed to validate playlist: %s", value)
            return

        if not tracks:
            log.info("Invalid playlist: %s", value)
            return

        if self._replace_tracklist(tracks):
            log.debug("Started Playlist: %s", value)

    def on_action_ploadshfl(self, value):
        # Replace current queue with shuffled playlist from URI.
        if not value:
            return log.warning("Cannot load unnamed playlist")

        try:
            tracks = self._get_playlist_tracks(value)
        except Exception:
            log.exception("Failed to validate playlist: %s", value)
            return

        if not tracks:
            log.info("Invalid playlist: %s", value)
            return

        if self._replace_tracklist(tracks, shuffle=True):
            log.debug("Started shuffled Playlist: %s", value)

    def on_action_clr(self, value):
        """Clear the queue (tracklist)."""
        return self.core.tracklist.clear()

    def on_action_plist(self, value):
        # Request a list of all playlist
        plist = self.core.playlists.as_list()
        playlists = []
        item = {}
        for a in plist.get():
            item = {"name": a.name, "uri": a.uri}
            playlists.append(item)
        self.mqtt.publish("plists", json.dumps(playlists))
        log.debug("Generated playlist list")

    def on_action_plrefresh(self, value):
        # refresh a single playlist or all
        # value = uri_scheme, if value=None, all playlists are refreshed
        if value:
            self.core.playlists.refresh(uri_scheme=value)
            log.debug("Refreshed playlists with uri_scheme: %s", value)
        else:
            self.core.playlists.refresh()
            log.debug("Refreshed all playlists")

    def on_action_chgtrk(self, value):
        # change current playing track in the queue
        if not value:
            return log.info("chgtrk: Cannot change track to empty uri")

        flt = self.core.tracklist.filter(criteria={"uri": [value]}).get()
        if not flt:
            return log.info("chgtrk: Invalid track")
        (tlid, trk) = flt[0]
        self.core.playback.play(tlid=tlid)
        log.debug("Changed track to tlid: %s", tlid)

    def on_action_queryschemes(self, value):
        # request uri_schemes handled by search
        schemes = self.core.get_uri_schemes().get()
        log.debug("Uri_schemes handled by search: %s", schemes)
        self.mqtt.publish("uri_schemes", json.dumps(schemes))

    def on_action_search(self, value):
        if not value:
            return log.info("search: Cannot search empty strings")
        value = json.loads(value)
        lookup_str = value["search"]
        lookup_uris = value["uri_schemes"]
        query = {"any": lookup_str}
        results = self.core.library.search(query=query, uris=lookup_uris).get()
        if isinstance(results, SearchResult):
            search_result = results
        else:
            search_result = next(iter(results or ()), None)

        tracks = getattr(search_result, "tracks", ()) or ()
        found = len(tracks)
        item = {}
        final_list = []
        for k in tracks:
            item = {"name": k.name, "uri": k.uri}
            final_list.append(item)
        log.debug(
            "Search for %s in %s ended. Found %d tracks", lookup_str, lookup_uris, found
        )
        self.mqtt.publish("search_results", json.dumps(final_list))
