Based on [mopidy-mqtt](https://github.com/odiroot/mopidy-mqtt)

# Mopiqtt
 MQTT interface for Mopidy music server. Allows easy integration with Node Red or any MQTT client.
 This package is mainly useful to Node Red users, who can embed in their flows a full control over Mopidy by simple mqtt-in or mqtt-out nodes. See [Node Red examples](https://github.com/fmarzocca/Mopiqtt/tree/Development/NodeRed%20examples). Of course, it can be used by any other MQTT client too.


# Installation

Using pip:
```
[sudo] python3 -m pip install Mopiqtt
```
(If you are running Mopidy as a service, use `sudo`)

# Configuration

Add the following section to your mopidy's configuration file: `/etc/mopidy/mopidy.conf`


```
[mopiqtt]
host = <mqtt broker address>
port = 1883
topic = mopidy
username =
password =
```

*Note*: Remember to also supply `username` and `password` options if your
MQTT broker requires authentication. If not, just leave blank the two values.

*Note*: Restart Mopidy with `sudo service mopidy restart`

To check Mopidy log run `sudo tail -f /var/log/mopidy/mopidy.log`

# Features

* Sends information about Mopidy state on any change
    - Playback status
    - Volume
    - Track description
    - Playlists list
    - Artwork
    - Track index
* Reacts to control commands
    - Playback control
    - Tracklist control
    - Volume control
    - Load & play a playlist (straight or shuffle)
    - Request playlists list
    - Refresh playlists
    - Get tracklist


# MQTT protocol

## Topics

Default top level topic: `mopidy`.

Control topic: `mopidy/cmnd`.

Information topic `mopidy/stat`.

## Messages to subscribe to (mopidy/stat/`<msg>`)

|               |  Subtopic |                  Values                   |
|:-------------:|:---------:|:-----------------------------------------:|
| Playback State|   `/plstate`  | `paused` / `stop` / `playing`         |
| Volume        |   `/vol`  |               `<level:int>`               |
| Current track |   `/trk`  | `<artist:str>;<title:str>;<album>` or ` ` |
| List of playlists | `/plists` | `<array of playlists name:uri>`       |
| Track Artwork (*)| `/artw`   |   `<url of image to download>`         | 
| Playing track index (*)| `/trk-index` |  ` {current: x, last: y}`     |
| Playlists have been refreshed | `/refreshed` | ` `                    |
| List of tracks in the queue(**)   | `/trklist` | `<array of tracks name:uri>` |

`(*)`  Published after any track started playback  
`(**)` Published after any tracklist change

## Messages to publish to (mopidy/cmnd/`<msg>`)

|                 | Subtopic |                               Parameters                              |
|:----------------:|:--------:|:-----------------------------------------------------------------:|
| Playback control | `/plb`   | `play` / `stop` / `pause` / `resume` / `toggle` / `prev` / `next` |
| Volume control   | `/vol`   | `=<int>` or `-<int>` or `+<int>`                                  |
| Clear queue      | `/clr`   | ` `                                                               |
| Add to queue     | `/add`   | `<uri:str>`                                                       |
| Load and play playlist (straight)  | `/pload` | `<uri:str>`                                     |
| Load and play playlist (shuffle)   |   `/ploadshfl` | `<uri:str>`                               |   
| Request list of playlists| `/plist` | ` `                                                       |
| Load and play a radio stream (or a single track) | `/pstream`| `<uri:str>`                      |
| Refresh one or all playlists(*)| `/plrefresh` | `<uri_scheme>` or `None`                        |
| Change current playing track(**)| `/chgtrk` |    `<uri:str>`                                    |


`(*)` If `uri_scheme` is None, all backends are asked to refresh. If `uri_scheme` is an URI scheme handled by a backend, only that backend is asked to refresh.  
`(**)` Note that the track must already be in the tracklist.


# Contribute

You can contribute to Mopiqtt by:
   
[![paypal](https://img.shields.io/badge/donate-paypal-blue.svg?style=flat-square)](https://www.paypal.com/donate/?hosted_button_id=NQHVVDCNK3UDL)

# Credits
- Current maintainer: [fmarzocca](https://github.com/fmarzocca)

Based on previous works of:
-  [odiroot](https://github.com/odiroot)
-  [magcode](https://github.com/magcode>)

# Project resources
[![Downloads](https://pepy.tech/badge/mopiqtt)](https://pepy.tech/project/mopiqtt)

- [Source code](<https://github.com/fmarzocca/mopiqtt>)
- [Issue tracker](<https://github.com/fmarzocca/mopiqtt/issues>)
- [Changelog](<https://github.com/fmarzocca/mopiqtt/blob/main/CHANGELOG.md>)
