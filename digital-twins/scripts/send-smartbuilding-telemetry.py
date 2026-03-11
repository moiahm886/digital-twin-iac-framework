import json
import time
from azure.eventhub import EventHubProducerClient, EventData

EVENTHUB_CONNECTION_STRING = "Endpoint=sb://moiz-ehns.servicebus.windows.net/;SharedAccessKeyName=telemetrySendListen;SharedAccessKey=8jFBUnPO0shSuTGE74PLzNjqA2GKkljjt+AEhC7qqCE="
EVENTHUB_NAME = "telemetry"

def send_telemetry():
    producer = EventHubProducerClient.from_connection_string(
        conn_str=EVENTHUB_CONNECTION_STRING,
        eventhub_name=EVENTHUB_NAME
    )

    temp_payload = {
        "sensorId": "tempSensor101",
        "temperature": 29.5,
        "timestamp": time.time()
    }

    co2_payload = {
        "sensorId": "co2Sensor101",
        "co2ppm": 780,
        "timestamp": time.time()
    }

    batch = producer.create_batch()
    batch.add(EventData(json.dumps(temp_payload)))
    batch.add(EventData(json.dumps(co2_payload)))

    print("Sending telemetry...")
    producer.send_batch(batch)
    print("Telemetry sent!")

    producer.close()

if __name__ == "__main__":
    send_telemetry()