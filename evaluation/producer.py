import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

from azure.eventhub import EventData, EventHubProducerClient

# sensor templates, one per sensor type in the three manifests
SENSORS = {
    "smartbuilding": [
        ("tempSensor101", lambda: {"temperature": round(20 + 5 * time.time() % 5, 2)}),
        ("co2Sensor101", lambda: {"co2ppm": round(400 + 200 * (time.time() % 1), 1)}),
    ],
    "vehicle": [
        ("batterySensor001", lambda: {"batteryPercent": round(60 + 30 * (time.time() % 1), 1)}),
        ("gpsSensor001", lambda: {"latitude": 58.3776, "longitude": 26.7290}),
    ],
    "healthcare": [
        ("hrSensor001", lambda: {"bpm": round(60 + 40 * (time.time() % 1), 1)}),
        ("bpSensor001", lambda: {"systolic": 118.0, "diastolic": 78.0}),
    ],
}

MIXES = {
    "equal": {"smartbuilding": 1 / 3, "vehicle": 1 / 3, "healthcare": 1 / 3},
    "vehicle-heavy": {"vehicle": 0.6, "smartbuilding": 0.25, "healthcare": 0.15},
}


def build_message(domain, run_id, seq):
    sensor_id, values = SENSORS[domain][seq % len(SENSORS[domain])]
    msg = {
        "sensorId": sensor_id,
        "domain": domain,                       # ignored by the Function, kept for traceability
        "runId": run_id,
        "seq": seq,
        "sentAt": int(time.time() * 1000),      # epoch ms, used for end-to-end latency
    }
    msg.update(values())
    return msg


def plan(count, mix):
    """Interleave domains so the mix holds throughout the run, not just overall."""
    weights = MIXES[mix]
    order, acc = [], {d: 0.0 for d in weights}
    for _ in range(count):
        for d in acc:
            acc[d] += weights[d]
        pick = max(acc, key=acc.get)
        acc[pick] -= 1.0
        order.append(pick)
    return order


def send(conn, hub, run_id, count, rate, batch_size, workers):
    producer = EventHubProducerClient.from_connection_string(conn, eventhub_name=hub)
    domains = plan(count, args.mix)

    sent = 0
    started = time.perf_counter()
    interval = batch_size / rate          # seconds between batches to hold the rate

    def flush(items):
        batch = producer.create_batch()
        for m in items:
            batch.add(EventData(json.dumps(m)))
        producer.send_batch(batch)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = []
        while sent < count:
            n = min(batch_size, count - sent)
            items = [build_message(domains[sent + k], run_id, sent + k) for k in range(n)]
            futures.append(pool.submit(flush, items))
            sent += n
            target = started + (sent / rate)
            drift = target - time.perf_counter()
            if drift > 0:
                time.sleep(drift)
        for f in futures:
            f.result()

    producer.close()
    elapsed = time.perf_counter() - started
    return sent, elapsed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=int, required=True, help="target messages per second")
    ap.add_argument("--count", type=int, default=3000, help="measured messages to send")
    ap.add_argument("--warmup", type=int, default=500, help="discarded messages sent first")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mix", choices=list(MIXES), default="equal")
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--hub", default=os.environ.get("EVENTHUB_NAME", "telemetry"))
    ap.add_argument("--connection", default=os.environ.get("EVENTHUB_CONNECTION"))
    args = ap.parse_args()

    if not args.connection:
        raise SystemExit("set EVENTHUB_CONNECTION or pass --connection")

    if args.warmup:
        wid = f"{args.run_id}-warmup"
        n, t = send(args.connection, args.hub, wid, args.warmup, args.rate,
                    args.batch_size, args.workers)
        print(f"warmup   run={wid:24} sent={n:6} in {t:6.1f}s  ({n/t:7.1f} msg/s)")
        time.sleep(5)

    n, t = send(args.connection, args.hub, args.run_id, args.count, args.rate,
                args.batch_size, args.workers)
    print(f"measured run={args.run_id:24} sent={n:6} in {t:6.1f}s  ({n/t:7.1f} msg/s) "
          f"target={args.rate}")