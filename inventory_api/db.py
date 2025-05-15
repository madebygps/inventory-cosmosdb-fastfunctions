from typing import Any
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
import os

COSMOSDB_ENDPOINT  = os.environ["COSMOSDB_ENDPOINT"]
DATABASE_NAME      = os.environ["COSMOSDB_DATABASE"]
PRODUCTS_CONTAINER = os.environ["COSMOSDB_CONTAINER_PRODUCTS"]
LOCATIONS_CONTAINER= os.environ["COSMOSDB_CONTAINER_LOCATIONS"]
INVENTORY_CONTAINER= os.environ["COSMOSDB_CONTAINER_INVENTORY"]


_credential = DefaultAzureCredential()
_client     = CosmosClient(COSMOSDB_ENDPOINT, credential=_credential)


async def get_container(name: str = PRODUCTS_CONTAINER) -> Any:
    """
    FastAPI dependency: returns a pre-opened Cosmos container client.
    """

    database = _client.get_database_client(DATABASE_NAME)
    
    if name == PRODUCTS_CONTAINER:
        return database.get_container_client(PRODUCTS_CONTAINER)
    elif name == LOCATIONS_CONTAINER:
        return database.get_container_client(LOCATIONS_CONTAINER)
    elif name == INVENTORY_CONTAINER:
        return database.get_container_client(INVENTORY_CONTAINER)
    else:
        raise ValueError(f"Unknown container name: {name}")
