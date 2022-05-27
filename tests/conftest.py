from __future__ import absolute_import
import pytest
from mopidy.core import Core


@pytest.fixture
def config():
    return {
        'core': {},
        'mqtt': {
            'host': 'localhost',
            'port': 1883,
            'topic': 'mopidy',
        },
    }


@pytest.fixture
def core(config):
    actor = Core.start(
        config=config, backends=[]).proxy()

    yield actor
    actor.stop()
