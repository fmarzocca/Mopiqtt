UNKNOWN = u''


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

    return u';'.join([title, artist, album])


def describe_stream(raw_title):
    """
    Attempt to parse given stream title in very rudimentary way.
    """
    title = UNKNOWN
    artist = UNKNOWN
    album = UNKNOWN

    # Very common separator.
    if '-' in raw_title:
        parts = raw_title.split('-')
        artist = parts[0].strip()
        title = parts[1].strip()
    else:
        # Just assume we only have track title.
        title = raw_title

    return u';'.join([title, artist, album])

def get_track_artwork(self, track):
    imageUri=self.core.library.get_images([track.uri]).get()[track.uri]
    if (imageUri):
        if imageUri[0].uri.startswith("/local"):
            return self.defaultImage
        else:
            return imageUri[0].uri

        return image
    else:
        return self.defaultImage
        