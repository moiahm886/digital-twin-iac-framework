# test_baseline.py
# Scenario: Baseline Load Test
# Rate: 10 msg/s | Duration: 2 minutes
# Domains: All equal (Smart Building, Vehicle, Healthcare)

import json
import time
import random
from azure.eventhub import EventHubProducerClient, EventData

CONN_STR = "CONN_STR"
EVENTHUB_NAME = "telemetry"

TARGET_RATE = 10
DURATION_SECONDS = 120  # 2 minutes

def generate_smartbuilding_payloads():
    return [
        {"sensorId": "tempSensor101", "domain": "smartbuilding", "temperature": round(random.uniform(20, 35), 2), "timestamp": time.time()},
        {"sensorId": "co2Sensor101", "domain": "smartbuilding", "co2ppm": round(random.uniform(400, 1200), 2), "timestamp": time.time()},
    ]

def generate_vehicle_payloads():
    return [
        {"sensorId": "gpsSensor001", "domain": "vehicle", "latitude": round(random.uniform(59.3, 59.5), 6), "longitude": round(random.uniform(24.6, 24.9), 6), "timestamp": time.time()},
        {"sensorId": "batterySensor001", "domain": "vehicle", "batteryPercent": round(random.uniform(20, 100), 2), "timestamp": time.time()},
    ]

def generate_healthcare_payloads():
    return [
        {"sensorId": "hrSensor", "domain": "healthcare", "bpm": random.randint(60, 100), "timestamp": time.time()},
        {"sensorId": "bpSensor", "domain": "healthcare", "systolic": round(random.uniform(110, 140), 1), "diastolic": round(random.uniform(70, 90), 1), "timestamp": time.time()},
    ]

def run():
    producer = EventHubProducerClient.from_connection_string(CONN_STR, eventhub_name=EVENTHUB_NAME)

    interval = 1.0 / TARGET_RATE
    start_time = time.time()
    end_time = start_time + DURATION_SECONDS
    total_sent = 0
    total_errors = 0
    msg_counter = 0

    domain_cycle = [
        generate_smartbuilding_payloads,
        generate_vehicle_payloads,
        generate_healthcare_payloads,
    ]

    print(f"[Baseline] Starting — {TARGET_RATE} msg/s for {DURATION_SECONDS}s")
    print(f"[Baseline] Start time: {time.strftime('%H:%M:%S')}")

    while time.time() < end_time:
        loop_start = time.time()

        generator = domain_cycle[msg_counter % 3]
        payloads = generator()

        try:
            batch = producer.create_batch()
            for p in payloads:
                batch.add(EventData(json.dumps(p)))
            producer.send_batch(batch)
            total_sent += len(payloads)
        except Exception as e:
            total_errors += 1
            print(f"[ERROR] {e}")

        msg_counter += 1

        elapsed = time.time() - start_time
        if msg_counter % 30 == 0:
            print(f"[Baseline] {elapsed:.0f}s elapsed — sent {total_sent} msgs, errors {total_errors}")

        sleep_time = interval - (time.time() - loop_start)
        if sleep_time > 0:
            time.sleep(sleep_time)

    producer.close()

    duration = time.time() - start_time
    print(f"\n[Baseline] Complete")
    print(f"  Duration:     {duration:.1f}s")
    print(f"  Total sent:   {total_sent}")
    print(f"  Total errors: {total_errors}")
    print(f"  Avg rate:     {total_sent / duration:.2f} msg/s")
    print(f"  End time:     {time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run()