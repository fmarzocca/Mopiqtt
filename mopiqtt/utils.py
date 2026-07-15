import logging


log = logging.getLogger(__name__)


UNKNOWN = ""


def describe_track(track):
    """
    Prepare a short human-readable Track description.

    track (mopidy.models.Track): Track to source song data from.
    """
    title = track.name or UNKNOWN

    # Simple/regular case: normal song (e.g. from Spotify).
    if track.artists:
        artist = next(iter(track.artists)).name
    elif track.album and track.album.artists:  # Album-only artist case.
        artist = next(iter(track.album.artists)).name
    else:
        artist = UNKNOWN

    if track.album and track.album.name:
        album = track.album.name
    else:
        album = UNKNOWN

    return ";".join([title, artist, album])


def describe_stream(raw_title):
    """
    Attempt to parse given stream title in very rudimentary way.
    """
    title = UNKNOWN
    artist = UNKNOWN
    album = UNKNOWN

    # Very common separator.
    if "-" in raw_title:
        parts = raw_title.split("-")
        artist = parts[0].strip()
        title = parts[1].strip()
    else:
        # Just assume we only have track title.
        title = raw_title

    return ";".join([title, artist, album])


def get_track_artwork(self, track):
    track_uri = getattr(track, "uri", None)
    if not track_uri:
        return self.defaultImage

    try:
        artwork = self.core.library.get_images([track_uri]).get()
        images = (artwork or {}).get(track_uri, ())
        if not images:
            return self.defaultImage

        image_uri = getattr(images[0], "uri", None)
        if not image_uri:
            return self.defaultImage
        if image_uri == "/local" or image_uri.startswith("/local/"):
            return self.defaultImage

        return image_uri
    except Exception:
        log.exception("Failed to get artwork for track URI: %s", track_uri)
        return self.defaultImage
