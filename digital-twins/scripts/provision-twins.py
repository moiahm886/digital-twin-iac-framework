import argparse
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor


# --------------------------------------------------------------------------
# expansion: manifest -> (twins, relationships)
# --------------------------------------------------------------------------

def render(template, i):
    """Substitute the instance index into a pattern or property value."""
    if isinstance(template, str) and "{i" in template:
        return template.format(i=i)
    return template


def render_props(props, i):
    return {k: render(v, i) for k, v in (props or {}).items()}


def expand(manifest, count_override=None):
    """Turn the declared shape and count into concrete twins and relationships."""
    prefix = manifest["modelPrefix"]
    ent = manifest["entity"]
    sub = manifest["subsystem"]
    sensors = manifest["sensors"]

    start = ent.get("indexStart", 1)
    count = count_override if count_override is not None else ent.get("count", 1)

    twins, rels = [], []

    for n in range(count):
        i = start + n

        eid = render(ent["idPattern"], i)
        twins.append((eid, f"{prefix}:{ent['model']}", render_props(ent.get("properties"), i)))

        sid = render(sub["idPattern"], i)
        twins.append((sid, f"{prefix}:{sub['model']}", render_props(sub.get("properties"), i)))
        rels.append((eid, sub["relationship"], sid))

        for s in sensors:
            nid = render(s["idPattern"], i)
            twins.append((nid, f"{prefix}:{s['model']}", render_props(s.get("properties"), i)))
            rels.append((sid, "hasSensor", nid))

    return twins, rels


# --------------------------------------------------------------------------
# output paths
# --------------------------------------------------------------------------

def write_ndjson(path, twins, rels):
    """Emit the bulk import document (ADT Import Jobs format)."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"Section": "Header"}) + "\n")
        f.write(json.dumps({"fileVersion": "1.0.0"}) + "\n")
        f.write(json.dumps({"Section": "Twins"}) + "\n")
        for tid, model, props in twins:
            body = {"$dtId": tid, "$metadata": {"$model": model}}
            body.update(props)
            f.write(json.dumps(body) + "\n")
        f.write(json.dumps({"Section": "Relationships"}) + "\n")
        for src, name, tgt in rels:
            f.write(json.dumps({
                "$sourceId": src,
                "$relationshipId": f"{src}-{tgt}",
                "$targetId": tgt,
                "$relationshipName": name,
            }) + "\n")
    return path


def create_individually(client, twins, rels, workers):
    """Create twins one call at a time. Used below the bulk threshold."""
    from azure.digitaltwins.core import DigitalTwinsClient  # noqa: F401

    def put_twin(t):
        tid, model, props = t
        body = {"$metadata": {"$model": model}}
        body.update(props)
        client.upsert_digital_twin(tid, body)

    def put_rel(r):
        src, name, tgt = r
        client.upsert_relationship(src, f"{src}-{tgt}", {
            "$targetId": tgt,
            "$relationshipName": name,
        })

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(put_twin, twins))
        list(pool.map(put_rel, rels))


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--dt-name", help="ADT instance name; omit with --dry-run")
    ap.add_argument("--count", type=int, help="override entity count in the manifest")
    ap.add_argument("--bulk-threshold", type=int, default=500,
                    help="above this many twins, emit NDJSON for a bulk import job")
    ap.add_argument("--ndjson-out", default="build/twins.ndjson")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--dry-run", action="store_true",
                    help="expand and report, create nothing")
    args = ap.parse_args()

    manifest = json.load(open(args.manifest, encoding="utf-8"))
    twins, rels = expand(manifest, args.count)

    print(f"domain          {manifest['domain']}")
    print(f"entities        {args.count or manifest['entity'].get('count', 1)}")
    print(f"twins           {len(twins)}")
    print(f"relationships   {len(rels)}")

    if args.dry_run:
        for t in twins[:8]:
            print("  twin", t[0], t[1].split(":")[-1], t[2])
        for r in rels[:6]:
            print("  rel ", r[0], "-", r[1], "->", r[2])
        if len(twins) > 8:
            print(f"  ... {len(twins) - 8} more twins")
        return

    if not args.dt_name:
        sys.exit("--dt-name is required unless --dry-run")

    if len(twins) > args.bulk_threshold:
        path = write_ndjson(args.ndjson_out, twins, rels)
        print(f"\nwrote {path} ({path.stat().st_size / 1e6:.1f} MB)")
        print("submit it with:")
        print(f"  az storage blob upload -f {path} -c dtimport -n {path.name} "
              f"--account-name <storage>")
        print(f"  az dt job import create -n {args.dt_name} "
              f"--data-file {path.name} --input-blob-container dtimport "
              f"--input-storage-account <storage>")
        return

    from azure.digitaltwins.core import DigitalTwinsClient
    from azure.identity import DefaultAzureCredential

    client = DigitalTwinsClient(
        f"https://{args.dt_name}.api.weu.digitaltwins.azure.net",
        DefaultAzureCredential(),
    )
    create_individually(client, twins, rels, args.workers)
    print("\ncreated.")


if __name__ == "__main__":
    main()