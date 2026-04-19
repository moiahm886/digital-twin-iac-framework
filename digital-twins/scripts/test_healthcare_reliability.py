# test_healthcare_reliability.py
# Scenario: Healthcare Reliability Test
# Rate: ~50 msg/s | Duration: 2 minutes
# Domain: Healthcare ONLY
# Focus: Zero error tolerance, consistent delivery

import json
import time
import random
from azure.eventhub import EventHubProducerClient, EventData

CONN_STR = "THE_CONNECTION_STRING"
EVENTHUB_NAME = "telemetry"

TARGET_RATE = 50
DURATION_SECONDS = 120  # 2 minutes

def generate_hr():
    return {
        "sensorId": "hrSensor",
        "domain": "healthcare",
        "bpm": random.randint(60, 100),
        "timestamp": time.time()
    }

def generate_bp():
    return {
        "sensorId": "bpSensor",
        "domain": "healthcare",
        "systolic": round(random.uniform(110, 140), 1),
        "diastolic": round(random.uniform(70, 90), 1),
        "timestamp": time.time()
    }

def run():
    producer = EventHubProducerClient.from_connection_string(CONN_STR, eventhub_name=EVENTHUB_NAME)

    interval = 1.0 / TARGET_RATE
    start_time = time.time()
    end_time = start_time + DURATION_SECONDS
    total_sent = 0
    total_errors = 0
    msg_counter = 0

    # Alternate between hr and bp
    sensor_cycle = [generate_hr, generate_bp]

    print(f"[Healthcare] Starting reliability test — {TARGET_RATE} msg/s for {DURATION_SECONDS}s")
    print(f"[Healthcare] Domain: Healthcare ONLY — zero error focus")
    print(f"[Healthcare] Start time: {time.strftime('%H:%M:%S')}")

    while time.time() < end_time:
        loop_start = time.time()

        payload = sensor_cycle[msg_counter % 2]()

        try:
            batch = producer.create_batch()
            batch.add(EventData(json.dumps(payload)))
            producer.send_batch(batch)
            total_sent += 1
        except Exception as e:
            total_errors += 1
            print(f"[ERROR] msg {msg_counter} failed: {e}")

        msg_counter += 1

        elapsed = time.time() - start_time
        if msg_counter % 100 == 0:
            print(f"[Healthcare] {elapsed:.0f}s elapsed — sent {total_sent} msgs, errors {total_errors}")

        sleep_time = interval - (time.time() - loop_start)
        if sleep_time > 0:
            time.sleep(sleep_time)

    producer.close()

    duration = time.time() - start_time
    error_rate = (total_errors / total_sent * 100) if total_sent > 0 else 0

    print(f"\n[Healthcare] Complete")
    print(f"  Duration:       {duration:.1f}s")
    print(f"  Total sent:     {total_sent}")
    print(f"  Total errors:   {total_errors}")
    print(f"  Error rate:     {error_rate:.2f}%")
    print(f"  Avg rate:       {total_sent / duration:.2f} msg/s")
    print(f"  End time:       {time.strftime('%H:%M:%S')}")

    # Explicit reliability verdict
    if total_errors == 0:
        print(f"\n  ✓ RELIABILITY: PASS — zero errors, all messages delivered")
    else:
        print(f"\n  ✗ RELIABILITY: FAIL — {total_errors} messages lost")

if __name__ == "__main__":
    run()