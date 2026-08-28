using Azure;
using System.Diagnostics;
using System.Text.Json;
using Azure.DigitalTwins.Core;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;

public class EventHubToAdt
{
    private const int MaxConcurrentUpdates = 32;

    private readonly ILogger<EventHubToAdt> _logger;
    private readonly DigitalTwinsClient _adt;
    private readonly TelemetryMap _map;
    private readonly string _runId;

    // All injected as singletons, so the credential is acquired once per worker
    // process rather than once per message.
    public EventHubToAdt(ILogger<EventHubToAdt> logger, DigitalTwinsClient adt, TelemetryMap map)
    {
        _logger = logger;
        _adt = adt;
        _map = map;
        _runId = Environment.GetEnvironmentVariable("RUN_ID") ?? "unset";
    }

    [Function("EventHubToAdt")]
    public async Task Run(
        [EventHubTrigger("%EVENTHUB_NAME%", Connection = "EVENTHUB_CONNECTION",
         ConsumerGroup = "%EVENTHUB_CONSUMER_GROUP%", IsBatched = true)] string[] messages)
    {
        var sw = Stopwatch.StartNew();
        var gate = new SemaphoreSlim(MaxConcurrentUpdates);
        var ok = 0;
        var unmatched = 0;
        var failed = 0;

        var work = messages.Select(async raw =>
        {
            await gate.WaitAsync();
            try
            {
                using var doc = JsonDocument.Parse(raw);
                var root = doc.RootElement;

                var twinId = root.GetProperty("sensorId").GetString();
                if (twinId is null) { Interlocked.Increment(ref unmatched); return; }

                var updates = _map.Resolve(root);
                if (updates is null) { Interlocked.Increment(ref unmatched); return; }

                var patch = new JsonPatchDocument();
                foreach (var (property, value) in updates)
                    patch.AppendReplace("/" + property, value);

                await _adt.UpdateDigitalTwinAsync(twinId, patch);
                Interlocked.Increment(ref ok);
            }
            catch (Exception ex)
            {
                Interlocked.Increment(ref failed);
                _logger.LogError(ex, "Twin update failed. RunId={RunId}", _runId);
            }
            finally
            {
                gate.Release();
            }
        });

        await Task.WhenAll(work);
        sw.Stop();

        // One structured record per batch, tagged with the run that produced it,
        // so Kusto queries can be scoped to a single load test.
        _logger.LogInformation(
            "BatchComplete RunId={RunId} Size={Size} Ok={Ok} Unmatched={Unmatched} " +
            "Failed={Failed} DurationMs={DurationMs}",
            _runId, messages.Length, ok, unmatched, failed, sw.ElapsedMilliseconds);

        // A failed twin update must not be checkpointed as a success. Throwing
        // holds the checkpoint so the batch is retried.
        if (failed > 0)
            throw new InvalidOperationException(
                $"{failed} of {messages.Length} twin updates failed in this batch.");
    }
}