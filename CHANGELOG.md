# Changelog
## Unreleased

## 2.0.1 - 2026-08-11

### Fixed
* Playlist loading now skips tracks that Mopidy cannot resolve while preserving valid tracks, their original order, and valid duplicates; if no track can be resolved, the current queue remains unchanged

## 2.0.0 - 2026-07-15

### Compatibility
* Added compatibility with Mopidy 4 while retaining Mopidy 3.4 support
* Added official support for Python 3.13 and later

### Changed
* Preserved queues during playlist and stream validation, and restored them after loading errors when Mopidy rollback operations succeed

### Fixed
* Prevented invalid MQTT payloads and handler errors from stopping subsequent messages
* Fixed search result handling for Mopidy 4 and empty results while retaining Mopidy 3 compatibility
* Fixed artwork fallback handling for missing, local, or unavailable images
* Reported rejected MQTT connections
* Awaited Mopidy command futures and reported failures instead of silently discarding asynchronous errors
* Prevented incomplete track metadata or a missing track index from breaking MQTT status updates

### Internal
* Added automated CI coverage for Mopidy 3 and 4 on Python 3.13 and 3.14
* Added PEP 517 build metadata in `pyproject.toml`

## 1.2.1
* Fixes failing tests [#6](https://github.com/fmarzocca/Mopiqtt/issues/6)

## 1.2.0
* Added track uri message

## 1.1.0
* New paho-mqqt requirement (v.>=2.0)

## 1.0.11
* Fixes [#4](https://github.com/fmarzocca/Mopiqtt/issues/4)

## 1.0.10
* Fixed default artwork image

## 1.0.9
* Bugfix on mqtt username (Credit: @hirschharald) Closes [#2](https://github.com/fmarzocca/Mopiqtt/issues/2) 

## 1.0.8
* Local artwork is not supported

## 1.0.7
* Added `mopidy/cmnd/queryschemes` to request a list of uri-schemes Mopidy can handle in searches
* Added `mopidy/stat/uri_schemes` to get a list of uri-schemes Mopidy can handle in searches
* Added `mopidy/cmnd/search` to search libraries for any string (artist, album, track)
* Added Added `mopidy/stat/search_results` to get results of search command

## 1.0.6
* Fixed bug on `mopidy/cmnd/plrefresh`
* Class name renaming

## 1.0.5
* Improved error catching
* Added `mopidy/stat/trklist` message showing the list of tracks in the queue
* Added `mopidy/cmnd/chgtrk`  to change current playing track in tracklist

## 1.0.4
* Fixed bug on `mopidy/cmnd/add`
* Added `mopidy/cmnd/pstream` to load and play a radio stream (or any single track)
* Added `mopidy/stat/refreshed` event when playlists have been refreshed
* Added `mopidy/stat/plrefresh` to refresh one or all playlists

## 1.0.3
* Better playlist list formatting **Breaking change:** Now the list is an array of objects
* Introducing position of current playing track

## 1.0.2
* Added `mopidy/cmnd/ploadshf` to load and play shuffled playlists

## 1.0.1
* First release
