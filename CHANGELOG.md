# Changelog

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












