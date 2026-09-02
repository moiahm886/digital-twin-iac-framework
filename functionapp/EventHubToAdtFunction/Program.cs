using Azure.DigitalTwins.Core;
using Azure.Identity;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = FunctionsApplication.CreateBuilder(args);

builder.ConfigureFunctionsWebApplication();

builder.Services
    .AddApplicationInsightsTelemetryWorkerService()
    .ConfigureFunctionsApplicationInsights();

// The isolated worker installs a filter that drops everything below Warning
// before it reaches Application Insights. Removing it is what makes the
// per-batch Information logs visible for the evaluation queries.
builder.Services.Configure<LoggerFilterOptions>(options =>
{
    var rule = options.Rules.FirstOrDefault(r => r.ProviderName
        == "Microsoft.Extensions.Logging.ApplicationInsights.ApplicationInsightsLoggerProvider");
    if (rule is not null)
        options.Rules.Remove(rule);
});

// One client and one credential for the lifetime of the worker process.
// Previously both were constructed on every invocation.
builder.Services.AddSingleton(_ =>
{
    var url = Environment.GetEnvironmentVariable("ADT_SERVICE_URL")
              ?? throw new InvalidOperationException("ADT_SERVICE_URL is not set.");
    return new DigitalTwinsClient(new Uri(url), new DefaultAzureCredential());
});

// The telemetry map is parsed once at startup, not per message.
builder.Services.AddSingleton(_ => TelemetryMap.FromEnvironment());

builder.Build().Run();