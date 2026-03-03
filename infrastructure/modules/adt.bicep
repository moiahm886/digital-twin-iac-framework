param dtName string
param location string = resourceGroup().location

resource adt 'Microsoft.DigitalTwins/digitalTwinsInstances@2023-01-31' = {
  name: dtName
  location: location
  properties: {}
}

output adtId string = adt.id
output adtHostName string = adt.properties.hostName
