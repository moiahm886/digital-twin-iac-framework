param prefix string = 'dtframework'
param location string = resourceGroup().location

param dtName string = '${prefix}-dt-instance'
param ehNamespaceName string = '${prefix}-ehns'
param functionAppName string = '${prefix}-dt-func'

@description('Must be globally unique, lowercase, 3-24 chars')
param storageAccountName string

param logAnalyticsName string = '${prefix}-law'
param appInsightsName string = '${prefix}-ai'

@description('Role definition GUID for Azure Digital Twins Data Owner')
param adtDataOwnerRoleGuid string

module adt './modules/adt.bicep' = {
  name: 'deploy-adt'
  params: {
    dtName: dtName
    location: location
  }
}

module eh './modules/eventhub.bicep' = {
  name: 'deploy-eh'
  params: {
    location: location
    namespaceName: ehNamespaceName
    eventHubName: 'telemetry'
    consumerGroupName: 'func'
  }
}

module mon './modules/monitoring.bicep' = {
  name: 'deploy-monitoring'
  params: {
    location: location
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
  }
}

module fa './modules/functionapp.bicep' = {
  name: 'deploy-function'
  params: {
    location: location
    functionAppName: functionAppName
    storageAccountName: storageAccountName
    appInsightsConnectionString: mon.outputs.appInsightsConnectionString
    adtServiceUrl: 'https://${adt.outputs.adtHostName}'
    eventHubConnectionString: eh.outputs.eventHubConnectionString
    eventHubName: eh.outputs.eventHubNameOut
    consumerGroupName: eh.outputs.consumerGroupNameOut
  }
}

module rbac './modules/adt-rbac.bicep' = {
  name: 'grant-adt-role'
  params: {
    adtResourceId: adt.outputs.adtId
    principalId: fa.outputs.principalId
    roleDefinitionGuid: adtDataOwnerRoleGuid
  }
}

output adtHostName string = adt.outputs.adtHostName
output functionApp string = fa.outputs.functionAppNameOut
