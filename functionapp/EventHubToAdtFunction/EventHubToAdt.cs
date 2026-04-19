using System;
using System.Text;
using System.Threading.Tasks;
using Azure;
using Azure.DigitalTwins.Core;
using Azure.Identity;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;
using System.Text.Json;

public class EventHubToAdt
{
    private readonly ILogger _logger;
    private readonly DigitalTwinsClient _adtClient;

    public EventHubToAdt(ILoggerFactory loggerFactory)
    {
        _logger = loggerFactory.CreateLogger<EventHubToAdt>();
        var adtUrl = Environment.GetEnvironmentVariable("ADT_SERVICE_URL");
        _adtClient = new DigitalTwinsClient(new Uri(adtUrl), new DefaultAzureCredential());
    }

    [Function("EventHubToAdt")]
    public async Task Run(
        [EventHubTrigger("%EVENTHUB_NAME%", Connection = "EVENTHUB_CONNECTION",
         ConsumerGroup = "%EVENTHUB_CONSUMER_GROUP%", IsBatched = false)] byte[] eventData)
    {
        var json = Encoding.UTF8.GetString(eventData);
        _logger.LogInformation($"Received event: {json}");

        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            var sensorId = root.GetProperty("sensorId").GetString();
            var domain = root.TryGetProperty("domain", out var d) ? d.GetString() : InferDomain(sensorId);

            switch (domain)
            {
                case "smartbuilding":
                    await HandleSmartBuilding(sensorId, root);
                    break;
                case "vehicle":
                    await HandleVehicle(sensorId, root);
                    break;
                case "healthcare":
                    await HandleHealthcare(sensorId, root);
                    break;
                default:
                    _logger.LogWarning($"Unknown domain for sensorId: {sensorId}");
                    break;
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"Error processing message: {json}");
        }
    }

    // Smart Building: temp + CO2
    private async Task HandleSmartBuilding(string sensorId, JsonElement root)
{
    var patch = new JsonPatchDocument();

    if (root.TryGetProperty("temperature", out var temp))
    {
        patch.AppendReplace("/currentTemperature", temp.GetDouble());
        await _adtClient.UpdateDigitalTwinAsync(sensorId, patch);
        _logger.LogInformation("Domain={Domain} SensorId={SensorId} Property=currentTemperature Value={Value}", 
            "SmartBuilding", sensorId, temp.GetDouble());
    }
    else if (root.TryGetProperty("co2ppm", out var co2))
    {
        patch.AppendReplace("/currentCO2ppm", co2.GetDouble());
        await _adtClient.UpdateDigitalTwinAsync(sensorId, patch);
        _logger.LogInformation("Domain={Domain} SensorId={SensorId} Property=currentCO2ppm Value={Value}", 
            "SmartBuilding", sensorId, co2.GetDouble());
    }
}

    // Vehicle: GPS location + battery
    private async Task HandleVehicle(string sensorId, JsonElement root)
{
    var patch = new JsonPatchDocument();

    if (root.TryGetProperty("latitude", out var lat) && root.TryGetProperty("longitude", out var lon))
    {
        patch.AppendReplace("/currentLatitude", lat.GetDouble());
        patch.AppendReplace("/currentLongitude", lon.GetDouble());
        await _adtClient.UpdateDigitalTwinAsync(sensorId, patch);
        _logger.LogInformation("Domain={Domain} SensorId={SensorId} Property=location Lat={Lat} Lon={Lon}", 
            "Vehicle", sensorId, lat.GetDouble(), lon.GetDouble());
    }
    else if (root.TryGetProperty("batteryPercent", out var battery))
    {
        patch.AppendReplace("/currentChargePercentage", battery.GetDouble());
        await _adtClient.UpdateDigitalTwinAsync(sensorId, patch);
        _logger.LogInformation("Domain={Domain} SensorId={SensorId} Property=currentChargePercentage Value={Value}", 
            "Vehicle", sensorId, battery.GetDouble());
    }
}
private async Task HandleHealthcare(string sensorId, JsonElement root)
{
    var patch = new JsonPatchDocument();

    if (root.TryGetProperty("bpm", out var bpm))
    {
        patch.AppendReplace("/currentBPM", bpm.GetDouble());
        await _adtClient.UpdateDigitalTwinAsync(sensorId, patch);
        _logger.LogInformation("Domain={Domain} SensorId={SensorId} Property=currentBPM Value={Value}", 
            "Healthcare", sensorId, bpm.GetDouble());
    }
    else if (root.TryGetProperty("systolic", out var sys) && root.TryGetProperty("diastolic", out var dia))
    {
        patch.AppendReplace("/currentSystolic", sys.GetDouble());
        patch.AppendReplace("/currentDiastolic", dia.GetDouble());
        await _adtClient.UpdateDigitalTwinAsync(sensorId, patch);
        _logger.LogInformation("Domain={Domain} SensorId={SensorId} Property=bloodPressure Systolic={Sys} Diastolic={Dia}", 
            "Healthcare", sensorId, sys.GetDouble(), dia.GetDouble());
    }
}

    // Fallback if domain not explicitly in payload
    private static string InferDomain(string sensorId)
    {
        if (sensorId == null) return "unknown";
        if (sensorId.StartsWith("temp") || sensorId.StartsWith("co2")) return "smartbuilding";
        if (sensorId.StartsWith("gps") || sensorId.StartsWith("battery")) return "vehicle";
        if (sensorId.StartsWith("hr") || sensorId.StartsWith("bp") || sensorId.StartsWith("spo2")) return "healthcare";
        return "unknown";
    }
}