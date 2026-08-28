using Azure.DigitalTwins.Core;
using Azure.Identity;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = FunctionsApplication.CreateBuilder(args);

builder.ConfigureFunctionsWebApplication();

builder.Services
    .AddApplicationInsightsTelemetryWorkerService()
    .ConfigureFunctionsApplicationInsights();

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