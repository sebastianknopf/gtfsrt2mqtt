import logging
import requests
import time
import yaml

from google.transit import gtfs_realtime_pb2
from paho.mqtt import client

from gtfsrt2mqtt.repeatedtimer import RepeatedTimer

class GTFSRealtimePublisher:

    def __init__(self, config_filename):

        # load config and set default values
        if config_filename is not None:
            with open(config_filename, 'r') as config_file:
                self._config = yaml.safe_load(config_file)

        # connecto to MQTT broker as defined in config
        self._mqtt = client.Client(client.CallbackAPIVersion.VERSION2, protocol=client.MQTTv5)
        self._mqtt.connect(self._config['mqtt']['host'], self._config['mqtt']['port'])

        self._mqtt.loop_start()

        # create empty timer instances
        self._service_alerts_timer = None
        self._trip_updates_timer = None
        self._vehicle_positions_timer = None

    def __enter__(self):
        return self
    
    def __exit__(self, exception_type, exception_value, exception_traceback):
        if self._service_alerts_timer is not None:
            self._service_alerts_timer.stop()

        if self._trip_updates_timer is not None:
            self._trip_updates_timer.stop()

        if self._vehicle_positions_timer is not None:
            self._vehicle_positions_timer.stop()

        self._mqtt.loop_stop()
    
    def _fetch_service_alerts(self):
        feed_message = self._fetch_feed_message(self._config['gtfsrt']['service_alerts_url'])

    def _fetch_trip_updates(self):
        feed_message = self._fetch_feed_message(self._config['gtfsrt']['trip_updates_url'])

        message_count = 0
        start_time = int(time.time())

        for entity in feed_message.entity:
            if entity.HasField('trip_update'):

                diff_feed_message = gtfs_realtime_pb2.FeedMessage()
                diff_feed_message.header.gtfs_realtime_version = feed_message.header.gtfs_realtime_version
                diff_feed_message.header.incrementality = diff_feed_message.header.DIFFERENTIAL
                diff_feed_message.header.timestamp = int(time.time())

                diff_entity = diff_feed_message.entity.add()

                diff_entity.CopyFrom(entity)

                # generate MQTT topic from placeholders
                topic = self._config['mqtt']['trip_updates_topic']

                if entity.trip_update.HasField('trip') and entity.trip_update.trip.HasField('trip_id'):
                    topic = topic.replace('[tripId]', entity.trip_update.trip.trip_id.replace('/', '_'))
                
                if entity.trip_update.HasField('trip') and entity.trip_update.trip.HasField('route_id'):
                    topic = topic.replace('[routeId]', entity.trip_update.trip.route_id.replace('/', '_'))

                if entity.trip_update.HasField('trip') and entity.trip_update.trip.HasField('start_time'):
                    topic = topic.replace('[startTime]', entity.trip_update.trip.start_time.replace('/', '_'))

                if entity.trip_update.HasField('trip') and entity.trip_update.trip.HasField('start_date'):
                    topic = topic.replace('[startDate]', entity.trip_update.trip.start_date.replace('/', '_'))

                topic = topic.replace('+', '_')
                topic = topic.replace('#', '_')
                topic = topic.replace('$', '_')

                # publish message to MQTT
                # self._mqtt.publish(topic, None, 1, True)
                self._mqtt.publish(topic, diff_feed_message.SerializeToString(), 0, True)

                message_count = message_count + 1

        end_time = int(time.time())

        logging.info(f"published {message_count} GTFSRT messages in {str(end_time - start_time)} seconds")

    def _fetch_vehicle_positions(self):
        feed_message = self._fetch_feed_message(self._config['gtfsrt']['vehicle_positions_url'])

    def _fetch_feed_message(self, url):
        response = requests.get(url)

        feed_message = gtfs_realtime_pb2.FeedMessage()
        feed_message.ParseFromString(response.content)

        return feed_message

    def run(self):
        if not self._config['app']['service_alerts_update_frequency_seconds'] == 0:
            self._service_alerts_timer = RepeatedTimer(self._config['app']['service_alerts_update_frequency_seconds'], self._fetch_service_alerts)
            self._service_alerts_timer.start()

        if not self._config['app']['trip_updates_update_frequency_seconds'] == 0:
            self._trip_updates_timer = RepeatedTimer(self._config['app']['trip_updates_update_frequency_seconds'], self._fetch_trip_updates)
            self._trip_updates_timer.start()

        if not self._config['app']['vehicle_positions_update_frequency_seconds'] == 0:
            self._vehicle_positions_timer = RepeatedTimer(self._config['app']['vehicle_positions_update_frequency_seconds'], self._fetch_vehicle_positions)
            self._vehicle_positions_timer.start()

        while True:
            pass