import paho.mqtt.client as mqtt
import signal
import time
from datetime import datetime
from snmp import gather
try:
    from config import *
except ModuleNotFoundError:
    print('Copy over config.py.example to config.py and restart the script')
    exit(0)


def trigger_update(publish):
    apStats, assocAp, assocSsid = gather(SNMP_HOST, SNMP_PORT, SNMP_COMMUNITY)
    for mac, ap in apStats.items():
        for label, value in ap.items():
            if label not in TOPIC_MAP:
                continue

            publish(PREFIX + TOPIC_MAP[label] % ap['aiAPName'], value)

        if 'ap_mem_free' in TOPIC_MAP:
            publish(
                PREFIX + TOPIC_MAP['ap_mem_free'] % ap['aiAPName'],
                round(ap['aiAPMemoryFree'] / ap['aiAPTotalMemory'] * 100, 1)
            )

    if 'ap_clients' in TOPIC_MAP:
        for mac, count in assocAp.items():
            publish(PREFIX + TOPIC_MAP['ap_clients'] % apStats[mac]['aiAPName'], count)

    if 'ssid_connected' in TOPIC_MAP:
        for ssid, count in assocSsid.items():
            publish(PREFIX + TOPIC_MAP['ssid_connected'] % str(ssid), count)

    if 'ssid_connected_total' in TOPIC_MAP:
        publish(PREFIX + TOPIC_MAP['ssid_connected_total'], sum(assocSsid.values()))


if __name__ == '__main__':
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    done = False

    def publish(topic, message):
        client.publish(topic, str(message))

    def do_exit(signal, frame):
        global done
        client.loop_stop()
        done = True

    signal.signal(signal.SIGINT, do_exit)

    while not done:
        now = datetime.now().timestamp()

        trigger_update(publish)

        sleeptime = now + UPDATE_INTERVAL - datetime.now().timestamp()
        while sleeptime > 0 and not done:
            sleeptime -= 1
            time.sleep(1)
