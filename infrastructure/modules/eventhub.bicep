param location string = resourceGroup().location
param namespaceName string
param eventHubName string = 'telemetry'
param consumerGroupName string = 'func'

resource ehns 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: namespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    isAutoInflateEnabled: true
    maximumThroughputUnits: 4
  }
}

resource eh 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  parent: ehns
  name: eventHubName
  properties: {
    partitionCount: 4
    messageRetentionInDays: 1
  }
}

resource cg 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2024-01-01' = {
  parent: eh
  name: consumerGroupName
  properties: {}
}

resource auth 'Microsoft.EventHub/namespaces/authorizationRules@2024-01-01' = {
  parent: ehns
  name: 'telemetrySendListen'
  properties: {
    rights: [
      'Listen'
      'Send'
    ]
  }
}

var keys = listKeys(auth.id, auth.apiVersion)

output namespaceId string = ehns.id
output eventHubNameOut string = eventHubName
output consumerGroupNameOut string = consumerGroupName
output eventHubConnectionString string = keys.primaryConnectionString
