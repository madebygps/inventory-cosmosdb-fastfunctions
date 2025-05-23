from typing import Optional
from azure.cosmos.aio import CosmosClient, ContainerProxy
from azure.identity.aio import DefaultAzureCredential
import os

from enum import Enum

class ContainerType(str, Enum):
    PRODUCTS = "products" 

_client: Optional[CosmosClient] = None
_credential: Optional[DefaultAzureCredential] = None

COSMOSDB_ENDPOINT = os.environ["COSMOSDB_ENDPOINT"]
DATABASE_NAME = os.environ["COSMOSDB_DATABASE"]
CONTAINERS = {
    "products": os.environ["COSMOSDB_CONTAINER_PRODUCTS"],
}

async def _ensure_client() -> CosmosClient:
    global _client, _credential
    if _client is None:
        _credential = DefaultAzureCredential()
        _client = CosmosClient(COSMOSDB_ENDPOINT, _credential)
    return _client

async def get_container(container_type: ContainerType) -> ContainerProxy:
    container_name = CONTAINERS.get(container_type)
    if not container_name:
        raise ValueError(
            f"Container '{container_type}' not configured. "
            f"Valid options: {list(CONTAINERS.keys())}"
        )

    client = await _ensure_client()
    database = client.get_database_client(DATABASE_NAME)
    return database.get_container_client(container_name)

