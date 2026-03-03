param location string = resourceGroup().location
param functionAppName string
param storageAccountName string

@secure()
param appInsightsConnectionString string

param adtServiceUrl string

@secure()
param eventHubConnectionString string

param eventHubName string
param consumerGroupName string

resource st 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${functionAppName}-plan'
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {}
}

resource func 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      appSettings: [
        { name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4' 
        }
        { name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'dotnet-isolated' 
        }

        // storage for runtime
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${st.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${listKeys(st.id, st.apiVersion).keys[0].value}'
        }

        // monitoring
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }

        // ADT
        { name: 'ADT_SERVICE_URL'
          value: adtServiceUrl
        }

        // Event Hub trigger config
        { name: 'EVENTHUB_CONNECTION'
          value: eventHubConnectionString 
        }
        { name: 'EVENTHUB_NAME'
          value: eventHubName 
        }
        { name: 'EVENTHUB_CONSUMER_GROUP'
          value: consumerGroupName 
        }
      ]
    }
  }
}

output principalId string = func.identity.principalId
output functionAppNameOut string = func.name
