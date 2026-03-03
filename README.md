# Digital Twin IaC Framework

A domain-agnostic Digital Twin deployment framework built on Microsoft Azure using Infrastructure as Code (Bicep).

---

## Overview

This repository demonstrates a reusable cloud infrastructure backbone that supports multiple Digital Twin domains without redeploying platform services.

The system is structured into two layers:

- **Infrastructure Layer** – Azure services provisioned via modular Bicep templates.
- **Domain Layer** – DTDL models, twin instances, and relationships specific to each domain.

---

## Infrastructure Components

Provisioned entirely via Bicep:

- Azure Digital Twins
- Azure Event Hubs
- Azure Functions
- Azure Storage Account
- Application Insights
- Log Analytics Workspace
- Managed Identity + RBAC

No manual Azure Portal configuration required.

---

## Implemented Domain

### Smart Building
- Room
- HVACUnit
- TemperatureSensor
- CO2Sensor

Status:
- Models deployed
- Twins instantiated
- Relationships established
- Infrastructure fully provisioned via IaC

---

## Deployment Workflow

1. Define DTDL models  
2. Deploy infrastructure (Bicep)  
3. Upload models to ADT  
4. Create twins and relationships  
5. Generate telemetry (planned)  
6. Process and update twins  
7. Monitor system metrics  

---

## Roadmap

- Add Healthcare domain  
- Add Autonomous Vehicle domain  
- Implement synthetic telemetry generator  
- Execute scalability evaluation  

---

## Purpose

Supports the thesis:

**Framework for Deploying Scalable Digital Twin Systems Using Infrastructure as Code on Azure**
