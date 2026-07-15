import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock

from paho.mqtt import client as mqtt
from paho.mqtt.client import ReasonCode
from paho.mqtt.packettypes import PacketTypes

from mopiqtt.frontend import MopiqttFrontend
from mopiqtt.mqtt import Comms


def mqtt_message(action, payload):
    return SimpleNamespace(topic="mopidy/cmnd/{}".format(action), payload=payload)


def test_malformed_json_payload_is_logged(caplog):
    class Frontend:
        def on_action_search(self, value):
            json.loads(value)

    comms = Comms(frontend=Frontend())

    with caplog.at_level(logging.ERROR, logger="mopiqtt.mqtt"):
        comms._on_message(None, None, mqtt_message("search", b"{invalid"))

    assert "topic=mopidy/cmnd/search" in caplog.text
    assert "payload='{invalid'" in caplog.text
    assert "JSONDecodeError" in caplog.text


def test_handler_exception_is_logged(caplog):
    class Frontend:
        def on_action_test(self, value):
            raise RuntimeError("handler failed")

    comms = Comms(frontend=Frontend())

    with caplog.at_level(logging.ERROR, logger="mopiqtt.mqtt"):
        comms._on_message(None, None, mqtt_message("test", b"payload"))

    assert "topic=mopidy/cmnd/test" in caplog.text
    assert "payload='payload'" in caplog.text
    assert "RuntimeError: handler failed" in caplog.text


def test_callback_processes_messages_after_an_error():
    class Frontend:
        def __init__(self):
            self.received = []

        def on_action_test(self, value):
            self.received.append(value)
            if value == "invalid":
                raise ValueError("invalid payload")

    frontend = Frontend()
    comms = Comms(frontend=frontend)

    comms._on_message(None, None, mqtt_message("test", b"invalid"))
    comms._on_message(None, None, mqtt_message("test", b"valid"))

    assert frontend.received == ["invalid", "valid"]


def test_callback_observes_actor_future_errors(caplog):
    failed_future = SimpleNamespace(
        get=Mock(side_effect=RuntimeError("playback failed"))
    )
    frontend = object.__new__(MopiqttFrontend)
    frontend.core = SimpleNamespace(
        playback=SimpleNamespace(play=Mock(return_value=failed_future))
    )
    comms = Comms(frontend=frontend)

    with caplog.at_level(logging.ERROR, logger="mopiqtt.mqtt"):
        comms._on_message(None, None, mqtt_message("plb", b"play"))

    assert "RuntimeError: playback failed" in caplog.text


def test_rejected_connection_does_not_subscribe(caplog):
    comms = Comms(frontend=SimpleNamespace(on_action_test=Mock()))
    comms.client = Mock()
    reason_code = ReasonCode(PacketTypes.CONNACK, identifier=135)

    with caplog.at_level(logging.ERROR, logger="mopiqtt.mqtt"):
        comms._on_connect(comms.client, None, None, reason_code, None)

    assert "Failed to connect to MQTT broker" in caplog.text
    comms.client.subscribe.assert_not_called()


def test_successful_connection_subscribes_to_public_handlers():
    comms = Comms(frontend=SimpleNamespace(on_action_test=Mock()))
    comms.client = Mock()
    comms.client.subscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 1)
    reason_code = ReasonCode(PacketTypes.CONNACK, identifier=0)

    comms._on_connect(comms.client, None, None, reason_code, None)

    comms.client.subscribe.assert_called_once_with("mopidy/cmnd/test")
