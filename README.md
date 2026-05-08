# Digital Twin IaC Framework

A domain-agnostic framework for deploying scalable Digital Twin systems on Microsoft Azure using Infrastructure as Code (Bicep). Developed as part of the M.Sc. Software Engineering thesis *Framework for Deploying Scalable Digital Twins Using Infrastructure as Code* at the University of Tartu, 2026.

---

## Motivation

Digital Twin systems are typically built as bespoke, domain-specific deployments. The same cloud infrastructure (telemetry ingestion, twin storage, processing, monitoring) is rebuilt from scratch for every new use case. This framework decouples the infrastructure layer from the domain layer, so the same provisioned backbone can host multiple Digital Twin domains without redeployment.

The entire infrastructure is provisioned declaratively via Bicep. No manual Azure Portal configuration is required at any stage.

---

## Architecture

The system is organised into two clearly separated layers.

The **infrastructure layer** is reusable across all domains and is provisioned via Bicep:

* Azure Digital Twins (ADT) for twin graph storage and query
* Azure Event Hubs (Standard tier, auto-inflate up to 4 throughput units, 4 partitions) for telemetry ingestion
* Azure Functions (Consumption plan Y1, .NET isolated worker, C#) for event-driven twin updates
* Azure Storage Account (Standard_LRS) for function runtime state
* Application Insights and Log Analytics Workspace for observability
* System-assigned Managed Identity granted the Azure Digital Twins Data Owner role for keyless access to ADT

The **domain layer** is swappable per use case. The repository ships with three implemented domains: smart building, healthcare, and autonomous vehicle. Each domain is a folder of DTDL v3 models and a PowerShell script that creates the corresponding twins and relationships.

End-to-end data flow:

```
Python load generator  ->  Event Hub (telemetry)  ->  Azure Function (EventHubToAdt, C#)  ->  Azure Digital Twins
                                                              |
                                                              v
                                                     Application Insights
                                                              |
                                                              v
                                                     Log Analytics Workspace
```

---

## Repository Structure

```
digital-twin-iac-framework/
├── infrastructure/
│   ├── main.bicep                          # Top-level deployment, wires all modules together
│   └── modules/
│       ├── adt.bicep                       # Azure Digital Twins instance
│       ├── eventhub.bicep                  # Event Hub namespace, hub, consumer group, auth rule
│       ├── functionapp.bicep               # Storage, App Service plan (Y1), Function App, app settings
│       ├── monitoring.bicep                # Log Analytics workspace + Application Insights
│       └── adt-rbac.bicep                  # Role assignment: Function MI -> ADT Data Owner
├── functionapp/
│   └── EventHubToAdtFunction/
│       ├── EventHubToAdt.cs                # The Function: Event Hub trigger, JSON Patch updates
│       ├── Program.cs                      # .NET isolated worker bootstrap with App Insights
│       ├── EventHubToAdtFunction.csproj
│       ├── host.json
│       └── local.settings.json
├── digital-twins/
│   ├── models/
│   │   ├── core/                           # Shared base interfaces (Entity, Sensor, Subsystem)
│   │   ├── smartbuilding/                  # Room, HVACUnit, TemperatureSensor, CO2Sensor
│   │   ├── healthcare/                     # PatientMonitor, MonitoringUnit, HeartRateSensor, BloodPressureSensor
│   │   └── vehicle/                        # AutonomousVehicle, Powertrain, GPSSensor, BatterySensor
│   └── scripts/
│       ├── upload-infra.ps1                # az deployment group create wrapper for main.bicep
│       ├── upload-models.ps1               # az dt model create for all four model folders
│       ├── create-twins-smartbuilding.ps1  # Creates twins + relationships for the building domain
│       ├── create-twins-healthcare.ps1     # Creates twins + relationships for the healthcare domain
│       ├── create-twins-vehicle.ps1        # Creates twins + relationships for the vehicle domain
│       ├── send-testing-telemetry.py       # Smoke test: one batch covering all three domains
│       ├── test_baseline.py                # 10 msg/s for 2 minutes, all domains equal
│       ├── test_light.py                   # ~100 msg/s for 3 minutes, all domains equal
│       ├── test_medium.py                  # ~250 msg/s for 2 minutes, vehicle-weighted
│       ├── test_heavy.py                   # ~1000 msg/s for 3 minutes, vehicle 60% / building 25% / healthcare 15%
│       └── test_healthcare_reliability.py  # 50 msg/s for 2 minutes, healthcare only, zero-error focus
├── docs/
│   ├── architecture/diagrams/              # Visual Paradigm source diagrams
│   └── screenshots/                        # Deployment screenshots
├── slr_evidence.xlsx                       # Systematic literature review evidence
├── README.md
└── .gitignore
```

---

## DTDL Model Hierarchy

All domain models extend a small core hierarchy defined in `digital-twins/models/core/`:

* `Entity` is the root interface, providing a `status` property.
* `Sensor` and `Subsystem` extend `Entity` and act as base types for domain-specific twins.

Domain interfaces use the DTMI namespace `dtmi:dtframework:<domain>:<TwinType>;1`. For example, the smart building temperature sensor is `dtmi:dtframework:smartbuilding:TemperatureSensor;1`, which extends `dtmi:dtframework:core:Sensor;1` and adds a `currentTemperature` property and a `temperatureReading` telemetry definition.

---

## The EventHubToAdt Function

The processing layer is a single C# function in `functionapp/EventHubToAdtFunction/EventHubToAdt.cs`. It is triggered per message by the `telemetry` Event Hub on the `func` consumer group, parses the JSON payload, and dispatches to a domain-specific handler based on the `domain` field (with a `sensorId` prefix-based fallback in `InferDomain`).

Each handler builds a `JsonPatchDocument` and calls `DigitalTwinsClient.UpdateDigitalTwinAsync`:

| Domain | Handler | Properties updated |
|---|---|---|
| `smartbuilding` | `HandleSmartBuilding` | `currentTemperature`, `currentCO2ppm` |
| `vehicle` | `HandleVehicle` | `currentLatitude` + `currentLongitude`, `currentChargePercentage` |
| `healthcare` | `HandleHealthcare` | `currentBPM`, `currentSystolic` + `currentDiastolic` |

The `DigitalTwinsClient` is constructed with `DefaultAzureCredential`, so the Function authenticates to ADT through its system-assigned managed identity. No keys or connection strings to ADT exist anywhere in code or configuration. The ADT endpoint and Event Hub trigger settings are passed in through app settings (`ADT_SERVICE_URL`, `EVENTHUB_NAME`, `EVENTHUB_CONNECTION`, `EVENTHUB_CONSUMER_GROUP`), which are written by `infrastructure/modules/functionapp.bicep` at deployment time.

Structured logs are emitted on every successful update with `Domain`, `SensorId`, and the property and value involved. These flow to Application Insights and the Log Analytics workspace, where they support the load-test analysis described below.

---

## Implemented Domains

### Smart Building

`Room` -> (`hasHVAC`) -> `HVACUnit` -> (`hasSensor`) -> `TemperatureSensor`, `CO2Sensor`. Reference twins created by `create-twins-smartbuilding.ps1`: `room101`, `hvac101`, `tempSensor101`, `co2Sensor101`.

### Healthcare

`PatientMonitor` -> (`hasMonitoringUnit`) -> `MonitoringUnit` -> (`hasSensor`) -> `HeartRateSensor`, `BloodPressureSensor`.

### Autonomous Vehicle

`AutonomousVehicle` -> (`hasPowertrain`) -> `Powertrain`, plus `GPSSensor` and `BatterySensor` attached as sensors.

---

## Scalability Evaluation

The framework was evaluated under five increasing load scenarios using the Python scripts in `digital-twins/scripts/`. Each script publishes telemetry directly to the `telemetry` Event Hub using `azure.eventhub.EventHubProducerClient`.

| Scenario | Script | Target rate | Duration | Domain mix |
|---|---|---|---|---|
| Baseline | `test_baseline.py` | 10 msg/s | 2 min | Equal split across all three domains |
| Light | `test_light.py` | ~100 msg/s | 3 min | Equal split |
| Medium | `test_medium.py` | ~250 msg/s | 2 min | Vehicle-weighted |
| Heavy | `test_heavy.py` | ~1000 msg/s | 3 min | Vehicle 60%, smart building 25%, healthcare 15% |
| Healthcare reliability | `test_healthcare_reliability.py` | 50 msg/s | 2 min | Healthcare only, zero-error focus |

Key findings:

* **Event Hub absorbed all incoming traffic with zero message loss** across every scenario, including the heavy load at roughly 1000 msg/s.
* **The Azure Functions Consumption plan reached a sustained processing ceiling at approximately 80 to 90 messages per second**, beyond which message backlog began to accumulate in the consumer group. Ingestion was never the constraint; the Function tier was.
* **Azure Digital Twins** sustained the twin update rate produced by the Function with no API throttling observed in the tested range.
* **The healthcare reliability scenario** completed with zero errors, demonstrating that the system meets a stricter delivery guarantee at moderate sustained load.

The architectural implication is that the framework scales horizontally without structural modification. For workloads beyond roughly 90 msg/s sustained, the only change required is upgrading the Function App from the Consumption plan to a Premium or Dedicated plan; no code, model, or topology changes are needed.

---

## Deployment Workflow

1. **Define or update DTDL models** in `digital-twins/models/<domain>/`.
2. **Create the resource group** (e.g. `rg-dt-framework`).
3. **Deploy the infrastructure** by running `digital-twins/scripts/upload-infra.ps1`, which invokes `az deployment group create` against `infrastructure/main.bicep`.
4. **Upload the models** to ADT by running `digital-twins/scripts/upload-models.ps1` (calls `az dt model create --from-directory` for `core`, `smartbuilding`, `healthcare`, and `vehicle`).
5. **Instantiate twins and relationships** by running the relevant `create-twins-<domain>.ps1` script.
6. **Deploy the Function App code** from `functionapp/EventHubToAdtFunction/` (e.g. via `func azure functionapp publish` or VS Code).
7. **Send a smoke test** with `send-testing-telemetry.py`, then the load-test scripts as needed.
8. **Observe** end-to-end behaviour in Application Insights and Log Analytics.

---

## Technology Stack

| Layer | Technology |
|---|---|
| IaC | Bicep |
| Twin platform | Azure Digital Twins, DTDL v3 |
| Ingestion | Azure Event Hubs (Standard, auto-inflate, 4 partitions) |
| Processing | Azure Functions, .NET isolated worker, C#, Consumption plan (Y1) |
| Observability | Application Insights, Log Analytics |
| Load generation | Python with `azure-eventhub` |
| Identity | System-assigned managed identity, Azure Digital Twins Data Owner role |
| Setup automation | PowerShell (Azure CLI wrappers) |

---

## Roadmap

* Premium-plan benchmarking to characterise the high-throughput regime beyond 90 msg/s
* Multi-region deployment templates
* CI/CD pipeline (GitHub Actions) for automated infrastructure validation and Function deployment
* Grafana dashboards committed alongside the Log Analytics queries

---

## Thesis Reference

This repository accompanies the M.Sc. thesis:

> **Framework for Deploying Scalable Digital Twins Using Infrastructure as Code**
> Moiz Ahmad, M.Sc. Software Engineering, University of Tartu, 2026.

---

## Author

**Moiz Ahmad**, [github.com/moiahm886](https://github.com/moiahm886)
