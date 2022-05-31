Based on [mopidy-mqtt](https://github.com/odiroot/mopidy-mqtt)

# Mopiqtt
 MQTT interface for Mopidy music server. Allows easy integration with Node Red or any MQTT client.


# Installation

Using pip:
```
python3 -m pip install Mopiqtt
```

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
* Reacts to control commands
    - Playback control
    - Tracklist control
    - Volume control
    - Load & play a playlist (straight or shuffle)
    - Request playlists list


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
| Playing track index (*)| `/trk-index` |  ` {current: x, last: y}`        |

`(*)` Published after any track started playback

## Messages to publish to (mopidy/cmnd/`<msg>`)

|                 | Subtopic |                               Parameters                              |
|:----------------:|:--------:|:-----------------------------------------------------------------:|
| Playback control | `/plb`   | `play` / `stop` / `pause` / `resume` / `toggle` / `prev` / `next` |
| Volume control   | `/vol`   | `=<int>` or `-<int>` or `+<int>`                                  |
| Clear queue      | `/clr`   | ` `                                                               |
| Add to queue     | `/add`   | `<uri:str>`                                                       |
| Load and play playlist (straight)  | `/pload` | `<uri:str>`                                     |
| Load and play playlist (shuffle)   |   `/ploadshfl` | `<uri:str>`                                |   
| Request list of playlists| `/plist` | ` `                                                       |

## Credits
- Current maintainer: [fmarzocca](https://github.com/fmarzocca)

Based on previous works of:
-  [odiroot](https://github.com/odiroot)
-  [magcode](https://github.com/magcode>)

## Contribute

You can contribute to Mopiqtt by:
   
[![paypal](https://img.shields.io/badge/donate-paypal-blue.svg?style=flat-square)](https://www.paypal.com/donate/?hosted_button_id=NQHVVDCNK3UDL)

## Changelog

**1.0.1**
* First release

**1.0.2**
* Added `mopidy/cmnd/ploadshf` to load and play shuffled playlists

**1.0.3**
* Better playlist list formatting **Breaking change:** Now the list is an array of objects
* Introducing position of current playing track

