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
        [EventHubTrigger("%EVENTHUB_NAME%", Connection = "EVENTHUB_CONNECTION", ConsumerGroup = "%EVENTHUB_CONSUMER_GROUP%", IsBatched = false)] byte[] eventData)
    {
        try
        {
            var json = Encoding.UTF8.GetString(eventData);
            _logger.LogInformation($"Received event: {json}");

            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            var sensorId = root.GetProperty("sensorId").GetString();

            if (sensorId == "tempSensor101")
            {
                var temperature = root.GetProperty("temperature").GetDouble();
                var patch = new JsonPatchDocument();
                patch.AppendReplace("/currentTemperature", temperature);

                await _adtClient.UpdateDigitalTwinAsync(sensorId, patch);
                _logger.LogInformation($"Updated {sensorId}.currentTemperature = {temperature}");
            }
            else if (sensorId == "co2Sensor101")
            {
                var co2 = root.GetProperty("co2ppm").GetDouble();
                var patch = new JsonPatchDocument();
                patch.AppendReplace("/currentCO2ppm", co2);

                await _adtClient.UpdateDigitalTwinAsync(sensorId, patch);
                _logger.LogInformation($"Updated {sensorId}.currentCO2ppm = {co2}");
            }
            else
            {
                _logger.LogWarning($"Unknown sensorId: {sensorId}");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing Event Hub message");
        }
    }
}