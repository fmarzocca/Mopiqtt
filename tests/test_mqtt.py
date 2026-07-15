import json
import logging
from types import SimpleNamespace

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
