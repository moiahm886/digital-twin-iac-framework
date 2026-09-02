using System.Collections.Concurrent;
using System.Diagnostics;
using System.Text.Json;
using Azure;
using Azure.DigitalTwins.Core;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;

public class EventHubToAdt
{
    private const int MaxConcurrentUpdates = 16;

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

    /// <summary>
    /// Enqueued times arrive as trigger metadata rather than on the message
    /// body. Read once per batch and never allowed to fail the batch: if the
    /// metadata is absent, latency falls back to the producer timestamp.
    /// </summary>
    private DateTimeOffset[] ReadEnqueuedTimes(FunctionContext context, int expected)
    {
        try
        {
            if (context.BindingContext.BindingData.TryGetValue("EnqueuedTimeUtcArray", out var raw)
                && raw is string json)
            {
                var parsed = JsonSerializer.Deserialize<DateTime[]>(json);
                if (parsed is not null && parsed.Length == expected)
                    return parsed
                        .Select(d => new DateTimeOffset(
                            DateTime.SpecifyKind(d, DateTimeKind.Utc)))
                        .ToArray();
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Enqueued time metadata unavailable; using producer timestamp.");
        }
        return Array.Empty<DateTimeOffset>();
    }

    [Function("EventHubToAdt")]
    public async Task Run(
        [EventHubTrigger("%EVENTHUB_NAME%", Connection = "EVENTHUB_CONNECTION",
         ConsumerGroup = "%EVENTHUB_CONSUMER_GROUP%", IsBatched = true)] string[] messages,
        FunctionContext context)
    {
        var sw = Stopwatch.StartNew();
        var gate = new SemaphoreSlim(MaxConcurrentUpdates);
        var receivedAt = DateTimeOffset.UtcNow;

        var enqueued = ReadEnqueuedTimes(context, messages.Length);
        var brokerClock = enqueued.Length == messages.Length;

        // Broker latency uses Azure timestamps at both ends when available, so
        // it is immune to producer clock skew. QueueWait separates time spent
        // waiting in Event Hub from time spent processing.
        var latencies = new ConcurrentBag<double>();
        var queueWaits = new ConcurrentBag<double>();

        var ok = 0;
        var unmatched = 0;
        var failed = 0;
        var throttled = 0;
        string? batchRunId = null;
        Exception? firstFailure = null;

        var work = messages.Select(async (raw, i) =>
        {
            await gate.WaitAsync();
            try
            {
                if (brokerClock)
                    queueWaits.Add((receivedAt - enqueued[i]).TotalMilliseconds);

                using var doc = JsonDocument.Parse(raw);
                var root = doc.RootElement;

                // The run id travels in the message. Setting it as an app setting
                // would restart the Function App and force a cold start per run.
                if (batchRunId is null && root.TryGetProperty("runId", out var rid))
                    batchRunId = rid.GetString();

                var twinId = root.GetProperty("sensorId").GetString();
                if (twinId is null) { Interlocked.Increment(ref unmatched); return; }

                var updates = _map.Resolve(root);
                if (updates is null) { Interlocked.Increment(ref unmatched); return; }

                var patch = new JsonPatchDocument();
                foreach (var (property, value) in updates)
                    patch.AppendReplace("/" + property, value);

                await _adt.UpdateDigitalTwinAsync(twinId, patch);

                var now = DateTimeOffset.UtcNow;
                if (brokerClock)
                    latencies.Add((now - enqueued[i]).TotalMilliseconds);
                else if (root.TryGetProperty("sentAt", out var sentAt))
                    latencies.Add(now.ToUnixTimeMilliseconds() - sentAt.GetInt64());

                Interlocked.Increment(ref ok);
            }
            catch (RequestFailedException rfe) when (rfe.Status == 429)
            {
                // Counted separately: the twin service rate-limited this write.
                Interlocked.CompareExchange(ref firstFailure, rfe, null);
                Interlocked.Increment(ref throttled);
                Interlocked.Increment(ref failed);
                _logger.LogError(rfe, "Twin update throttled (429). RunId={RunId}",
                    batchRunId ?? _runId);
            }
            catch (Exception ex)
            {
                Interlocked.CompareExchange(ref firstFailure, ex, null);
                Interlocked.Increment(ref failed);
                _logger.LogError(ex, "Twin update failed. RunId={RunId} Type={Type}",
                    batchRunId ?? _runId, ex.GetType().Name);
            }
            finally
            {
                gate.Release();
            }
        });

        await Task.WhenAll(work);
        sw.Stop();

        // One structured record per batch, tagged with the run that produced it,
        // so Kusto queries can be scoped to a single load test. Clock records
        // which timestamp source the latency figures came from.
        _logger.LogInformation(
            "BatchComplete RunId={RunId} Clock={Clock} Size={Size} Ok={Ok} " +
            "Unmatched={Unmatched} Failed={Failed} Throttled={Throttled} " +
            "DurationMs={DurationMs} LatencyAvgMs={LatencyAvgMs} LatencyMaxMs={LatencyMaxMs} " +
            "QueueWaitAvgMs={QueueWaitAvgMs} QueueWaitMaxMs={QueueWaitMaxMs}",
            batchRunId ?? _runId, brokerClock ? "broker" : "producer",
            messages.Length, ok, unmatched, failed, throttled,
            sw.ElapsedMilliseconds,
            latencies.Count > 0 ? Math.Round(latencies.Average(), 1) : 0,
            latencies.Count > 0 ? Math.Round(latencies.Max(), 1) : 0,
            queueWaits.Count > 0 ? Math.Round(queueWaits.Average(), 1) : 0,
            queueWaits.Count > 0 ? Math.Round(queueWaits.Max(), 1) : 0);

        // A failed twin update must not be checkpointed as a success. Throwing
        // holds the checkpoint so the batch is redelivered. The first real
        // failure is attached so the cause survives even if worker logs are
        // filtered out.
        if (failed > 0)
            throw new InvalidOperationException(
                $"{failed} of {messages.Length} twin updates failed in this batch " +
                $"({throttled} throttled). First cause: " +
                $"{firstFailure?.GetType().Name}: {firstFailure?.Message}",
                firstFailure);
    }
}