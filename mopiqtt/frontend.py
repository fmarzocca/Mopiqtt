from builtins import str
import logging

import pykka
from mopidy.core import CoreListener
from mopidy.audio import PlaybackState
from mopidy.models import SearchResult, Track, Artist, Album

from .mqtt import Comms
from .utils import describe_track, describe_stream, get_track_artwork

import json
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
        self.mqtt = Comms(frontend=self, **config['mopiqtt'])
        self.defaultImage = "https://fakeimg.pl/350x300/eeeeee/?text=No%20Image%20Avail.&font=Roboto"

    def on_start(self):
        """
        Hook for doing any setup that should be done *after* the actor is
        started, but *before* it starts processing messages.
        """
        log.debug('Starting MQTT frontend: %s', self)
        self.mqtt.start()

    def on_stop(self):
        """
        Hook for doing any cleanup that should be done *after* the actor has
        processed the last message, and *before* the actor stops.
        """
        log.debug('Stopping MQTT frontend: %s', self)
        self.mqtt.stop()

    def on_failure(self, exception_type, exception_value, traceback):
        """
        Hook for doing any cleanup *after* an unhandled exception is raised,
        and *before* the actor stops.
        """
        log.error('MQTT frontend failed: %s', exception_value)

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
        log.debug('MQTT tracklist changed')
        #
        # get list of all tracks in the queue
        #
        tk_list = self.core.tracklist.get_tracks().get()
        tracks =[]
        item = {}
        for a in tk_list:
            if a.artists:
                artist = next(iter(a.artists)).name
                item = {"name":artist+" - "+a.name,"uri":a.uri}
            else:
                item = {"name":a.name,"uri":a.uri}
            tracks.append(item)
        self.mqtt.publish("trklist",json.dumps(tracks))
        log.debug("Generated tracklist list")

    def playback_state_changed(self, old_state, new_state):
        """
        old_state (mopidy.core.PlaybackState) - the state before the change.
        new_state (mopidy.core.PlaybackState) - the state after the change.
        """
        log.debug('MQTT playback state changed: %s', new_state)
        self.mqtt.publish('plstate', new_state)

    def track_playback_started(self, tl_track):
        """
        tl_track (mopidy.models.TlTrack) - the track that just started playing.
        """
        log.debug('MQTT track started: %s', tl_track.track)
        self.mqtt.publish('trk', describe_track(tl_track.track))
        
        # get track's artwork (if any)
        self.mqtt.publish('artw', get_track_artwork(self, tl_track.track))
        
        # get track playing indexes
        curr = self.core.tracklist.index().get()
        last = self.core.tracklist.get_length().get()
        pl_index ={}
        pl_index["current"]= curr+1
        pl_index["last"]=last
        pl_index = json.dumps(pl_index) 
        self.mqtt.publish('trk-index',pl_index)

    def track_playback_ended(self, tl_track, time_position):
        """
        tl_track (mopidy.models.TlTrack) - the track that was played before
                                           playback stopped.
        time_position (int) - the time position in milliseconds.
        """
        log.debug('MQTT track ended: %s', tl_track.track.name)
        self.mqtt.publish('trk', '')

    def volume_changed(self, volume):
        """
        volume (int) - the new volume in the range [0..100].
        """
        log.debug('MQTT volume changed: %s', volume)
        self.mqtt.publish('vol', str(volume))

    def stream_title_changed(self, title):
        """
        title (string) - the new stream title.
        """
        log.debug('MQTT title changed: %s', title)
        self.mqtt.publish('trk', describe_stream(title))

    def playlists_loaded(self):
        log.debug('Playlists loaded event')
        self.mqtt.publish('refreshed', '')


    def on_action_plb(self, value):
        """Playback control."""
        if value == 'play':
            return self.core.playback.play()
        if value == 'stop':
            return self.core.playback.stop()
        if value == 'pause':
            return self.core.playback.pause()
        if value == 'resume':
            return self.core.playback.resume()

        if value == 'toggle':
            if self.current_state == PlaybackState.PLAYING:
                return self.core.playback.pause()
            if self.current_state == PlaybackState.PAUSED:
                return self.core.playback.resume()
            if self.current_state == PlaybackState.STOPPED:
                return self.core.playback.play()

        if value == 'prev':
            return self.core.playback.previous()
        if value == 'next':
            return self.core.playback.next()

        log.warn('Unknown playback control action: %s', value)

    def on_action_vol(self, value):
        """Volume control."""
        if not value or len(value) < 2:
            return log.warn('Invalid volume control parameter: %s', value)

        operator = value[0]
        try:
            amount = int(value[1:])
        except ValueError:
            return log.warn('Invalid volume setting value: %s', value[1:])

        # Exact volume.
        if operator == '=':
            self.volume = amount
            return
        # Volume down.
        if operator == '-':
            self.volume -= amount
            return
        # Volume up.
        if operator == '+':
            self.volume += amount
            return

        log.warn('Unknown volume control operator: %s', operator)

    def on_action_add(self, value):
        """Append URI to queue (tracklist)."""
        if not value:
            return log.warn('Cannot add empty track to queue')

        track=[]
        track.append(value)
        self.core.tracklist.add(uris=track)
        log.debug("Added track: %s",value)

    def on_action_pstream(self, value):
        """Load and start a radio stream or a single track (tracklist)."""
        if not value:
            return log.warn('Cannot load empty track to queue')

        track=[]
        track.append(value)
        self.core.tracklist.clear()
        self.core.tracklist.add(uris=track)
        self.core.playback.play()
        log.debug("Started track: %s",value)

    def on_action_pload(self, value):
        """Replace current queue with playlist from URI."""
        if not value:
            return log.warn('Cannot load unnamed playlist')

        self.core.tracklist.clear()
        #Read playlist (e.g. Spotify, Tidal, streams)
        items = self.core.playlists.get_items(value)
        tracks=[]
        try:
            for a in items.get():
                tracks.append(a.uri)
        except ValueError:
            return log.info("Invalid playlist: %s",value)
        self.core.tracklist.add(uris=tracks)
        self.core.playback.play()
        log.debug("Started Playlist: %s", value)

    def on_action_ploadshfl(self, value):
        #Replace current queue with shuffled playlist from URI.
        if not value:
            return log.warn('Cannot load unnamed playlist')

        self.core.tracklist.clear()
        #Read playlist (e.g. Spotify, Tidal, streams)
        items = self.core.playlists.get_items(value)
        tracks=[]
        try:
            for a in items.get():
                tracks.append(a.uri)
        except ValueError:
            return log.info("Invalid playlist: %s",value)
        self.core.tracklist.add(uris=tracks)
        self.core.tracklist.shuffle()
        self.core.playback.play()
        log.debug("Started shuffled Playlist: %s", value)         

    def on_action_clr(self, value):
        """Clear the queue (tracklist)."""
        return self.core.tracklist.clear()

    def on_action_plist(self,value):
        # Request a list of all playlist
        plist=self.core.playlists.as_list()
        playlists = []
        item = {}
        for a in plist.get():
            item = {"name": a.name, "uri":a.uri}
            playlists.append(item)
        self.mqtt.publish("plists",json.dumps(playlists))
        log.debug("Generated playlist list")

    def on_action_plrefresh (self, value):
        # refresh a single playlist or all
        # value = uri_scheme, if value=None, all playlists are refreshed
        if value:
            self.core.playlists.refresh(uri_scheme=value)
            log.debug ("Refreshed playlists with uri_scheme: %s",value)
        else:
            self.core.playlists.refresh()
            log.debug("Refreshed all playlists")

    def on_action_chgtrk(self,value):
        # change current playing track in the queue
        if not value:
            return log.info('chgtrk: Cannot change track to empty uri')

        flt = self.core.tracklist.filter(criteria={'uri':[value]}).get()
        if not flt:
            return log.info('chgtrk: Invalid track')
        (tlid,trk) = flt[0]
        self.core.playback.play(tlid=tlid)
        log.debug("Changed track to tlid: %s",tlid)

    def on_action_queryschemes(self,value):
        # request uri_schemes handled by search
        schemes = self.core.get_uri_schemes().get()
        log.debug("Uri_schemes handled by search: %s",schemes)
        self.mqtt.publish("uri_schemes",json.dumps(schemes))


    def on_action_search(self,value):
        if not value:
            return log.info('search: Cannot search empty strings')
        value = json.loads(value)
        lookup_str = (value["search"])
        lookup_uris = value["uri_schemes"]
        query = {"any":lookup_str}
        ret:SearchResult
        ret = self.core.library.search(query=query,uris=lookup_uris).get()
        found=(len(ret[0].tracks))
        tracks = ret[0].tracks 
        item ={}
        final_list=[]
        for k in tracks:
            item = {"name":k.name,"uri":k.uri}
            final_list.append(item)
        log.debug("Search for %s in %s ended. Found %d tracks",lookup_str,lookup_uris, found)
        self.mqtt.publish("search_results",json.dumps(final_list))





