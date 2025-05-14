import os
import logging
from typing import Optional
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)


_cosmos_client_instance = None

async def get_cosmos_client() -> CosmosClient:
    """
    Get or create the singleton CosmosDB client instance.
    
    Uses connection pooling and DefaultAzureCredential for authentication.
    Falls back to master key if provided in environment variables.
    
    Returns:
        CosmosClient: The CosmosDB client instance
    """
    global _cosmos_client_instance
    
    if _cosmos_client_instance is not None:
        return _cosmos_client_instance
    
    endpoint = os.environ.get("COSMOSDB_ENDPOINT")
    if not endpoint:
        raise ValueError("COSMOSDB_ENDPOINT environment variable must be set")
    
    
    # Use DefaultAzureCredential for Azure deployments (managed identity)
    logger.info("Creating CosmosDB client with DefaultAzureCredential")
    credential = DefaultAzureCredential()
    _cosmos_client_instance = CosmosClient(
        url=endpoint, 
        credential=credential
        )
    
    return _cosmos_client_instance
