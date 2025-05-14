@description('Name of the Cosmos DB account')
param name string

@description('Azure region where the Cosmos DB account will be deployed')
param location string = resourceGroup().location

@description('Tags to apply to the Cosmos DB account')
param tags object = {}

@description('Name of the database to create in the Cosmos DB account')
param databaseName string

// Container names for our application
@description('Name of the products container')
param productsContainerName string = 'products'

@description('Name of the locations container')
param locationsContainerName string = 'locations'

@description('Name of the inventory items container')
param inventoryItemsContainerName string = 'inventoryitems'

// Partition key paths for each container
@description('Path used for products partition key')
param productsPartitionKeyPath string = '/category'

@description('Path used for locations partition key')
param locationsPartitionKeyPath string = '/id'

@description('Path used for inventory items partition key')
param inventoryItemsPartitionKeyPath string = '/id'

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location  // Changed from location to locationName
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    publicNetworkAccess: 'Enabled'
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  name: databaseName
  parent: cosmosDbAccount
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// Products container
resource productsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  name: productsContainerName
  parent: cosmosDatabase
  properties: {
    resource: {
      id: productsContainerName
      partitionKey: {
        paths: [
          productsPartitionKeyPath
        ]
        kind: 'Hash'
      }
    }
    // No throughput property as serverless doesn't support it
  }
}

// Locations container
resource locationsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  name: locationsContainerName
  parent: cosmosDatabase
  properties: {
    resource: {
      id: locationsContainerName
      partitionKey: {
        paths: [
          locationsPartitionKeyPath
        ]
        kind: 'Hash'
      }
    }
    // No throughput property as serverless doesn't support it
  }
}

// Inventory items container
resource inventoryItemsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  name: inventoryItemsContainerName
  parent: cosmosDatabase
  properties: {
    resource: {
      id: inventoryItemsContainerName
      partitionKey: {
        paths: [
          inventoryItemsPartitionKeyPath
        ]
        kind: 'Hash'
      }
    }
    // No throughput property as serverless doesn't support it
  }
}

output cosmosEndpoint string = cosmosDbAccount.properties.documentEndpoint
output cosmosDatabaseName string = cosmosDatabase.name
output cosmosAccountId string = cosmosDbAccount.id
output cosmosAccountName string = cosmosDbAccount.name
output productsContainerName string = productsContainer.name
output locationsContainerName string = locationsContainer.name
output inventoryItemsContainerName string = inventoryItemsContainer.name
