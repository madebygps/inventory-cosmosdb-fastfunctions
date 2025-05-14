from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
import os

COSMOSDB_ENDPOINT = os.environ.get('COSMOSDB_ENDPOINT')
DATABASE_NAME = os.environ.get('COSMOSDB_DATABASE_NAME')
PRODUCTS_CONTAINER = os.environ.get('COSMOSDB_CONTAINER_PRODUCTS')
LOCATIONS_CONTAINER = os.environ.get('COSMOSDB_CONTAINER_LOCATIONS')
INVENTORY_CONTAINER = os.environ.get('COSMOSDB_CONTAINER_INVENTORY')

# Singleton client instance
_client = None
_database = None
_containers = {}

def get_cosmos_client():
    """Get or create the Cosmos DB client using DefaultAzureCredential."""
    global _client
    if _client is None:
        credential = DefaultAzureCredential()
        _client = CosmosClient(COSMOSDB_ENDPOINT, credential=credential)
    return _client

def get_database():
    """Get or create the database instance."""
    global _database, _client
    if _database is None:
        client = get_cosmos_client()
        _database = client.get_database_client(DATABASE_NAME)
    return _database

def get_container(container_name=None):
    """
    Get a container by name. If no name provided, returns the default container.
    
    Args:
        container_name: Name of the container (products, inventory, locations)
        
    Returns:
        The container client
    """
    global _containers
    
    # Get or create container client
    if container_name not in _containers:
        database = get_database()
        _containers[container_name] = database.get_container_client(container_name)
    
    return _containers[container_name]