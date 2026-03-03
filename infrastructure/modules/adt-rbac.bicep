param adtResourceId string
param principalId string

@description('Role definition GUID for Azure Digital Twins Data Owner')
param roleDefinitionGuid string

resource adt 'Microsoft.DigitalTwins/digitalTwinsInstances@2023-01-31' existing = {
  name: last(split(adtResourceId, '/'))
}

resource ra 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(adtResourceId, principalId, roleDefinitionGuid)
  scope: adt
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionGuid)
    principalType: 'ServicePrincipal'
  }
}
