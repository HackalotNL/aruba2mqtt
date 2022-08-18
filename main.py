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

apTopicMap = {
    'aiAPCPUUtilization': PREFIX + 'ap/%s/cpu_utilization',
    'aiAPMemoryFree': PREFIX + 'ap/%s/mem_free',
    'aiAPTotalMemory': PREFIX + 'ap/%s/mem_total',
}


def trigger_update(publish):
    apStats, assocAp, assocSsid = gather(SNMP_HOST, SNMP_PORT, SNMP_COMMUNITY)
    for mac, ap in apStats.items():
        for label, value in ap.items():
            if label not in apTopicMap:
                continue

            publish(apTopicMap[label] % ap['aiAPName'], value)

        publish(
            PREFIX + 'ap/%s/mem_free_percentage' % ap['aiAPName'],
            round(ap['aiAPMemoryFree'] / ap['aiAPTotalMemory'] * 100, 1)
        )

    for mac, count in assocAp.items():
        publish(PREFIX + 'ap/%s/clients' % apStats[mac]['aiAPName'], count)

    for ssid, count in assocSsid.items():
        publish(PREFIX + 'ssid/%s' % str(ssid), count)


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

        sleeptime = now + 60 - datetime.now().timestamp()
        while sleeptime > 0 and not done:
            sleeptime -= 1
            time.sleep(1)
