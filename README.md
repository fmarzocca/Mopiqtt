Based on [mopidy-mqtt](https://github.com/odiroot/mopidy-mqtt)

# Mopiqtt
 MQTT interface for Mopidy music server


# Installation

Using pip:
```
pip install Mopiqtt
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
    - Load & play a playlist
    - Request playlists list


# MQTT protocol

## Topics

Default top level topic: `mopidy`.

Control topic: `mopidy/cmnd`.

Information topic `mopidy/stat`.

## Messages to subscribe to (mopidy/stat/`<msg>`)

|      Kind     |  Subtopic |                  Values                   |
|:-------------:|:---------:|:-----------------------------------------:|
| State         |   `/sta`  | `paused` / `stop` / `playing`             |
| Volume        |   `/vol`  |               `<level:int>`               |
| Current track |   `/trk`  | `<artist:str>;<title:str>;<album>` or ` ` |
| List of playlists | `/plists` | `<array of playlists name:uri>`        |

## Publishable messages (mopidy/cmnd/`<msg>`)

|       Kind       | Subtopic |                               Values                              |
|:----------------:|:--------:|:-----------------------------------------------------------------:|
| Playback control | `/plb`   | `play` / `stop` / `pause` / `resume` / `toggle` / `prev` / `next` |
| Volume control   | `/vol`   | `=<int>` or `-<int>` or `+<int>`                                  |
| Clear queue      | `/clr`   | ` `                                                               |
| Add to queue     | `/add`   | `<uri:str>`                                                       |
| Load and play playlist   | `/pload` | `<uri:str>`                                               |
| Request list of playlists | `/plist` | ` `                |

