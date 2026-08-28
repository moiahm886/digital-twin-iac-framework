using System.Text.Json;

/// <summary>
/// Resolves an incoming message to the twin properties it updates, using the
/// merged telemetry map produced from the domain manifests. Loaded once per
/// worker process. Contains no domain names.
/// </summary>
public sealed class TelemetryMap
{
    public sealed record Rule(string[] Fields, Dictionary<string, string> Patch);

    private readonly Rule[] _rules;

    private TelemetryMap(Rule[] rules) => _rules = rules;

    public static TelemetryMap FromEnvironment()
    {
        var raw = Environment.GetEnvironmentVariable("TELEMETRY_MAP");
        if (string.IsNullOrWhiteSpace(raw))
            throw new InvalidOperationException(
                "TELEMETRY_MAP app setting is missing. Run build-telemetry-map.py.");

        using var doc = JsonDocument.Parse(raw);
        var rules = new List<Rule>();

        foreach (var r in doc.RootElement.GetProperty("rules").EnumerateArray())
        {
            var fields = r.GetProperty("fields")
                          .EnumerateArray()
                          .Select(f => f.GetString()!)
                          .ToArray();

            var patch = new Dictionary<string, string>();
            foreach (var p in r.GetProperty("patch").EnumerateObject())
                patch[p.Name] = p.Value.GetString()!;

            rules.Add(new Rule(fields, patch));
        }

        return new TelemetryMap(rules.ToArray());
    }

    /// <summary>
    /// Returns the property/value pairs this message updates, or null if no
    /// rule matches. First matching rule wins; rules are ordered longest
    /// field list first, so a two-field rule beats a one-field subset.
    /// </summary>
    public List<KeyValuePair<string, double>>? Resolve(JsonElement message)
    {
        foreach (var rule in _rules)
        {
            if (!rule.Fields.All(f => message.TryGetProperty(f, out _)))
                continue;

            var updates = new List<KeyValuePair<string, double>>(rule.Patch.Count);
            foreach (var (property, field) in rule.Patch)
                updates.Add(new(property, message.GetProperty(field).GetDouble()));

            return updates;
        }

        return null;
    }

    public int RuleCount => _rules.Length;
}