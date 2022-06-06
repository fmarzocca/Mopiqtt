import logging
from os import getpid

from paho.mqtt import client as mqtt


log = logging.getLogger(__name__)


HANDLER_PREFIX = 'on_action_'


class Comms:
    def __init__(
            self, frontend, host='localhost', port=1883, topic='mopidy',
            user=None, password=None, **kwargs):
        """
        Configure MQTT communication client.
        frontend (MopiqttFrontend): Instance of extension's frontend.
        """
        self.frontend = frontend
        self.host = host
        self.port = port
        self.topic = topic
        self.user = user
        self.password = password

        self.client = mqtt.Client(
            client_id='mopidy-{}'.format(getpid()), clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self):
        """
        Attempt connection to MQTT broker and initialise network loop.
        """
        if self.user and self.password:
            self.client.username_pw_set(
                username=self.user, password=self.password)

        self.client.connect_async(host=self.host, port=self.port)
        log.debug('Connecting to MQTT broker at %s:%s', self.host, self.port)
        self.client.loop_start()
        log.debug('Started MQTT communication loop.')

    def stop(self):
        """
        Clean up and disconnect from MQTT broker.
        """
        self.client.disconnect()
        log.debug('Disconnected from MQTT broker')

    def _on_connect(self, client, userdata, flags, rc):
        log.info('Successfully connected to MQTT broker, result :%s', rc)

        for name in dir(self.frontend):
            if not name.startswith(HANDLER_PREFIX):
                continue

            suffix = name[len(HANDLER_PREFIX):]
            full_topic = '{}/cmnd/{}'.format(self.topic, suffix)
            result, _ = self.client.subscribe(full_topic)

            if result == mqtt.MQTT_ERR_SUCCESS:
                log.debug('Subscribed to MQTT topic: %s', full_topic)
            else:
                log.warn('Failed to subscribe to MQTT topic: %s, result: %s',
                         full_topic, result)

    def _on_message(self, client, userdata, message):
        topic = message.topic.split('/')[-1]

        handler = getattr(self.frontend, HANDLER_PREFIX + topic, None)
        if not handler:
            log.warn('Cannot handle MQTT messages on topic: %s', message.topic)
            return

        log.debug('Passing payload: %s to MQTT handler: %s',
                  message.payload, handler.__name__)
        handler(value=message.payload.decode('utf8'))

    def publish(self, subtopic, value):
        full_topic = '{}/stat/{}'.format(self.topic, subtopic)

        log.debug('Publishing: %s to MQTT topic: %s', value, full_topic)
        return self.client.publish(topic=full_topic, payload=value)
