from __future__ import unicode_literals


from __future__ import absolute_import
from mopiqtt import frontend, Extension


def test_extension():
    ext = Extension()

    schema = ext.get_config_schema()
    assert schema

    config = ext.get_default_config()
    assert '[mqtt]' in config


def test_smoke(config, core):
    frontend.MopiqttFrontend(config, core)
