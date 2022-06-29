from __future__ import unicode_literals

from __future__ import absolute_import
import logging
import os

from mopidy import config, ext


__version__ = '1.0.8'
logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = 'Mopiqtt'
    ext_name = 'mopiqtt'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()

        schema['host'] = config.Hostname()
        schema['port'] = config.Port(optional=True)
        schema['topic'] = config.String()

        schema['username'] = config.String(optional=True)
        schema['password'] = config.Secret(optional=True)

        return schema

    def setup(self, registry):
        from mopiqtt.frontend import MopiqttFrontend
        registry.add('frontend', MopiqttFrontend)
