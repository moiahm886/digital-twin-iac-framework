# test_medium.py
# Scenario: Medium Load Test
# Rate: 500 msg/s | Duration: 3 minutes
# Domains: Vehicle heavy, Smart Building moderate, Healthcare light

import json
import time
import random
import threading
from azure.eventhub import EventHubProducerClient, EventData

CONN_STR = "Endpoint=sb://dtframework-ehns.servicebus.windows.net/;SharedAccessKeyName=telemetrySendListen;SharedAccessKey=tjhw+Y3cIm+hfoApLGMkepc7cHGNe5Ecv+AEhALuDek="
EVENTHUB_NAME = "telemetry"

TARGET_RATE = 500
DURATION_SECONDS = 180  # 3 minutes
NUM_WORKERS = 5         # 100 msg/s each

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

# Vehicle 50%, Smart Building 30%, Healthcare 20%
domain_cycle = [
    generate_vehicle_gps,
    generate_vehicle_battery,
    generate_vehicle_gps,
    generate_vehicle_battery,
    generate_vehicle_gps,
    generate_smartbuilding_temp,
    generate_smartbuilding_co2,
    generate_smartbuilding_temp,
    generate_healthcare_hr,
    generate_healthcare_bp,
]

stats = {"sent": 0, "errors": 0}
stats_lock = threading.Lock()

def worker(worker_id, end_time):
    producer = EventHubProducerClient.from_connection_string(CONN_STR, eventhub_name=EVENTHUB_NAME)
    interval = 1.0 / (TARGET_RATE / NUM_WORKERS)
    msg_counter = 0

    while time.time() < end_time:
        loop_start = time.time()

        payload = domain_cycle[msg_counter % len(domain_cycle)]()

        try:
            batch = producer.create_batch()
            batch.add(EventData(json.dumps(payload)))
            producer.send_batch(batch)
            with stats_lock:
                stats["sent"] += 1
        except Exception as e:
            with stats_lock:
                stats["errors"] += 1
            print(f"[Worker {worker_id}] ERROR: {e}")

        msg_counter += 1

        sleep_time = interval - (time.time() - loop_start)
        if sleep_time > 0:
            time.sleep(sleep_time)

    producer.close()

def run():
    start_time = time.time()
    end_time = start_time + DURATION_SECONDS

    print(f"[Medium] Starting — {TARGET_RATE} msg/s for {DURATION_SECONDS}s with {NUM_WORKERS} workers")
    print(f"[Medium] Domain split — Vehicle 50%, SmartBuilding 30%, Healthcare 20%")
    print(f"[Medium] Start time: {time.strftime('%H:%M:%S')}")

    threads = []
    for i in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(i, end_time))
        threads.append(t)
        t.start()

    # Progress monitor
    while time.time() < end_time:
        time.sleep(30)
        elapsed = time.time() - start_time
        with stats_lock:
            print(f"[Medium] {elapsed:.0f}s elapsed — sent {stats['sent']} msgs, errors {stats['errors']}")

    for t in threads:
        t.join()

    duration = time.time() - start_time
    print(f"\n[Medium] Complete")
    print(f"  Duration:     {duration:.1f}s")
    print(f"  Total sent:   {stats['sent']}")
    print(f"  Total errors: {stats['errors']}")
    print(f"  Avg rate:     {stats['sent'] / duration:.2f} msg/s")
    print(f"  End time:     {time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run()