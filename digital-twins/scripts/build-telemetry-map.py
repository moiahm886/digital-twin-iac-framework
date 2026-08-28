import argparse
import glob
import json
import os
import pathlib
import subprocess


def build(manifest_dir):
    rules = []
    for path in sorted(glob.glob(os.path.join(manifest_dir, "*.json"))):
        manifest = json.load(open(path, encoding="utf-8"))
        for sensor in manifest["sensors"]:
            for rule in sensor.get("telemetry", []):
                rules.append({
                    "fields": rule["fields"],
                    "patch": rule["patch"],
                })
    # longest field list first, so a two-field rule is matched before a
    # one-field rule that happens to be a subset of it
    rules.sort(key=lambda r: -len(r["fields"]))
    return {"rules": rules}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifests", default="../manifests")
    ap.add_argument("--out", default="build/telemetry-map.json")
    ap.add_argument("--set-app-setting", action="store_true")
    ap.add_argument("--function-app")
    ap.add_argument("--resource-group")
    args = ap.parse_args()

    doc = build(args.manifests)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {out} with {len(doc['rules'])} rules")
    for r in doc["rules"]:
        print("  ", r["fields"], "->", list(r["patch"]))

    if args.set_app_setting:
        compact = json.dumps(doc, separators=(",", ":"))
        subprocess.run([
            "az", "functionapp", "config", "appsettings", "set",
            "-n", args.function_app, "-g", args.resource_group,
            "--settings", f"TELEMETRY_MAP={compact}",
        ], check=True)
        print("app setting TELEMETRY_MAP updated")


if __name__ == "__main__":
    main()