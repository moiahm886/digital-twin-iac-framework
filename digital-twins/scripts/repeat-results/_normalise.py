import json, re, sys
suffix = sys.argv[1]
text = open(sys.argv[2], encoding="utf-8").read()
text = text.replace(suffix, "SUFFIX")
text = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "GUID", text)
print(json.dumps(json.loads(text), sort_keys=True, indent=2))
