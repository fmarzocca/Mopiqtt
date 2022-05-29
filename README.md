Based on [mopidy-mqtt](https://github.com/odiroot/mopidy-mqtt)

# Mopiqtt
 MQTT interface for Mopidy music server


# Installation

Using pip:
```
pip install Mopidy-MQTT-NG
```

# Configuration

You have to at least configure the MQTT broker access.
By default it's assumed to be installed locally.

```
[mqtt]
host = <mqtt broker address>
port = 1883
topic = mopidy
```

*Note*: Remember to also supply `username` and `password` options if your
MQTT broker requires authentication.

# Features

* Sends information about Mopidy state on any change
    - Playback status
    - Volume
    - Track description
* Reacts to control commands
    - Playback control
    - Tracklist control
    - Volume control
    - Track search [WIP]
* Responds to specific information inquiries

# MQTT protocol

## Topics

Default top level topic: `mopidy`.

Control topic: `mopidy/c`.

Information topic `mopidy/i`.

## Publishing

|      Kind     |  Subtopic |                  Values                   |
|:-------------:|:---------:|:-----------------------------------------:|
| State         |   `/sta`  | `paused` / `stop` / `playing`             |
| Volume        |   `/vol`  |               `<level:int>`               |
| Current track |   `/trk`  | `<artist:str>;<title:str>;<album>` or ` ` |

## Subscribing

|       Kind       | Subtopic |                               Values                              |
|:----------------:|:--------:|:-----------------------------------------------------------------:|
| Playback control | `/plb`   | `play` / `stop` / `pause` / `resume` / `toggle` / `prev` / `next` |
| Volume control   | `/vol`   | `=<int>` or `-<int>` or `+<int>`                                  |
| Clear queue      | `/clr`   | ` `                                                               |
| Add to queue     | `/add`   | `<uri:str>`                                                       |
| Request info     | `/inf`   | `state` / `volume` / `queue`                                  |

Not implemented (yet!) 

|       Kind       | Subtopic |                               Values                              |
|:----------------:|:--------:|:-----------------------------------------------------------------:|
| Load playlist    | `/loa`   | `<uri:str>`                                                       |
| Search tracks    | `/src`   | `<str>`                                                           |
