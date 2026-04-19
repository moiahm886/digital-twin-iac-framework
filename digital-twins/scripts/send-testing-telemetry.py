import json, time
from azure.eventhub import EventHubProducerClient, EventData

CONN_STR = "Endpoint=sb://dtframework-ehns.servicebus.windows.net/;SharedAccessKeyName=telemetrySendListen;SharedAccessKey=tjhw+Y3cIm+hfoApLGMkepc7cHGNe5Ecv+AEhALuDek="
EVENTHUB_NAME = "telemetry"

def send_all_domains():
    producer = EventHubProducerClient.from_connection_string(CONN_STR, eventhub_name=EVENTHUB_NAME)
    
    payloads = [
        # Smart Building
        {"sensorId": "tempSensor101", "domain": "smartbuilding", "temperature": 31.2, "timestamp": time.time()},
        {"sensorId": "co2Sensor101", "domain": "smartbuilding", "co2ppm": 820.0, "timestamp": time.time()},
        # Vehicle
        {"sensorId": "gpsSensor001", "domain": "vehicle", "latitude": 59.4370, "longitude": 24.7536, "timestamp": time.time()},
        {"sensorId": "batterySensor001", "domain": "vehicle", "batteryPercent": 78.5, "timestamp": time.time()},
        # Healthcare
        {"sensorId": "hrSensor001", "domain": "healthcare", "bpm": 72, "timestamp": time.time()},
        {"sensorId": "bpSensor001", "domain": "healthcare", "systolic": 120.0, "diastolic": 80.0, "timestamp": time.time()},
    ]

    batch = producer.create_batch()
    for p in payloads:
        batch.add(EventData(json.dumps(p)))
    
    producer.send_batch(batch)
    producer.close()
    print(f"Sent {len(payloads)} messages across all 3 domains")

if __name__ == "__main__":
    send_all_domains()