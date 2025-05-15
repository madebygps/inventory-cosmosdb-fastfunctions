metadata description = 'Creates an Azure App Service plan for Flex Consumption.'

@description('Name of the App Service Plan')
param name string

@description('Azure region where the App Service Plan will be deployed')
param location string = resourceGroup().location

@description('Tags to apply to the App Service Plan')
param tags object = {}

@description('Whether the App Service Plan is reserved (required for Linux plans)')
param reserved bool = true

@description('Whether the App Service Plan is zone redundant')
param zoneRedundant bool = false

resource appServicePlan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: name
  location: location
  tags: tags
  kind: 'functionapp'
  sku: {
    tier: 'FlexConsumption'
    name: 'FC1'
  }
  properties: {
    reserved: reserved
    zoneRedundant: zoneRedundant
  }
}

output id string = appServicePlan.id
output name string = appServicePlan.name
