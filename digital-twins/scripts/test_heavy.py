# test_heavy.py
# Scenario: Heavy Load Test
# Rate: ~1000 msg/s | Duration: 3 minutes
# Approach: 100 msg batches, 0.1s sleep = 10 batches/sec = 1000 msg/s
# Domain: Vehicle 60%, Smart Building 25%, Healthcare 15%

import json
import time
import random
from azure.eventhub import EventHubProducerClient, EventData

CONN_STR = "Endpoint=sb://dtframework-ehns.servicebus.windows.net/;SharedAccessKeyName=telemetrySendListen;SharedAccessKey=tjhw+Y3cIm+hfoApLGMkepc7cHGNe5Ecv+AEhALuDek="
EVENTHUB_NAME = "telemetry"

BATCH_SIZE = 100
DURATION_SECONDS = 180  # 3 minutes

def generate_vehicle_gps():
    return {"sensorId": "gpsSensor001", "domain": "vehicle", "latitude": round(random.uniform(59.3, 59.5), 6), "longitude": round(random.uniform(24.6, 24.9), 6), "timestamp": time.time()}

def generate_vehicle_battery():
    return {"sensorId": "batterySensor001", "domain": "vehicle", "batteryPercent": round(random.uniform(20, 100), 2), "timestamp": time.time()}

def generate_smartbuilding_temp():
    return {"sensorId": "tempSensor101", "domain": "smartbuilding", "temperature": round(random.uniform(20, 35), 2), "timestamp": time.time()}

def generate_smartbuilding_co2():
    return {"sensorId": "co2Sensor101", "domain": "smartbuilding", "co2ppm": round(random.uniform(400, 1200), 2), "timestamp": time.time()}

def generate_healthcare_hr():
    return {"sensorId": "hrSensor", "domain": "healthcare", "bpm": random.randint(60, 100), "timestamp": time.time()}

def generate_healthcare_bp():
    return {"sensorId": "bpSensor", "domain": "healthcare", "systolic": round(random.uniform(110, 140), 1), "diastolic": round(random.uniform(70, 90), 1), "timestamp": time.time()}

# Vehicle 60%, Smart Building 25%, Healthcare 15%
domain_cycle = [
    generate_vehicle_gps,
    generate_vehicle_gps,
    generate_vehicle_battery,
    generate_vehicle_gps,
    generate_vehicle_gps,
    generate_vehicle_battery,
    generate_smartbuilding_temp,
    generate_smartbuilding_co2,
    generate_smartbuilding_temp,
    generate_healthcare_hr,
    generate_healthcare_bp,
    generate_healthcare_hr,
    generate_smartbuilding_co2,
    generate_vehicle_gps,
    generate_vehicle_battery,
    generate_vehicle_gps,
    generate_smartbuilding_temp,
    generate_vehicle_gps,
    generate_healthcare_hr,
    generate_vehicle_gps,
]

def run():
    producer = EventHubProducerClient.from_connection_string(CONN_STR, eventhub_name=EVENTHUB_NAME)

    start_time = time.time()
    end_time = start_time + DURATION_SECONDS
    total_sent = 0
    total_errors = 0
    msg_counter = 0
    batch_counter = 0

    print(f"[Heavy] Starting — ~1000 msg/s for {DURATION_SECONDS}s")
    print(f"[Heavy] Batch size: {BATCH_SIZE}, sleep: 0.1s between batches")
    print(f"[Heavy] Domain split — Vehicle 60%, SmartBuilding 25%, Healthcare 15%")
    print(f"[Heavy] Start time: {time.strftime('%H:%M:%S')}")

    while time.time() < end_time:
        loop_start = time.time()

        try:
            batch = producer.create_batch()
            for _ in range(BATCH_SIZE):
                payload = domain_cycle[msg_counter % len(domain_cycle)]()
                batch.add(EventData(json.dumps(payload)))
                msg_counter += 1
            producer.send_batch(batch)
            total_sent += BATCH_SIZE
            batch_counter += 1
        except Exception as e:
            total_errors += BATCH_SIZE
            print(f"[ERROR] Batch {batch_counter} failed: {e}")

        if batch_counter % 10 == 0:
            elapsed = time.time() - start_time
            rate = total_sent / elapsed if elapsed > 0 else 0
            print(f"[Heavy] {elapsed:.0f}s — sent {total_sent} msgs, rate {rate:.0f} msg/s, errors {total_errors}")

        sleep_time = 0.1 - (time.time() - loop_start)
        if sleep_time > 0:
            time.sleep(sleep_time)

    producer.close()

    duration = time.time() - start_time
    print(f"\n[Heavy] Complete")
    print(f"  Duration:     {duration:.1f}s")
    print(f"  Total sent:   {total_sent}")
    print(f"  Total errors: {total_errors}")
    print(f"  Avg rate:     {total_sent / duration:.2f} msg/s")
    print(f"  Batches sent: {batch_counter}")
    print(f"  End time:     {time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run()