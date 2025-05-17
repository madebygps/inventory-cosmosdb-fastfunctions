from azure.cosmos.exceptions import CosmosHttpResponseError
from inventory_api.models.product import ProductRead, ProductCreate
from azure.cosmos.aio import ContainerProxy
import uuid
from typing import List
from inventory_api.exceptions import ProductNotFoundError, ProductAlreadyExistsError, DatabaseError
from inventory_api.logging_config import logger

async def list_products(
    container: ContainerProxy,
    category: str = "electronics",
    limit: int = 50,
    skip: int = 0,
) -> List[ProductRead]:
    query = (
        "SELECT * FROM c WHERE c.category=@cat OFFSET @skip LIMIT @limit"
        if category else
        "SELECT * FROM c OFFSET @skip LIMIT @limit"
    )
    params = [
        {"name":"@cat","value":category},
        {"name":"@skip","value":skip},
        {"name":"@limit","value":limit},
    ]
    try:
        iterator = container.query_items(query=query, parameters=params)
        items = [item async for item in iterator]
        return [ProductRead.model_validate(i) for i in items]
    except CosmosHttpResponseError as e:
        logger.error(f"Cosmos DB error during product listing: Status Code {e.status_code}, Message: {e.message}", exc_info=True)
        raise DatabaseError(f"Cosmos DB error during product listing: Status Code {e.status_code}, Message: {e.message}", original_exception=e) from e
    except Exception as e:
         logger.error(f"Unexpected error during product listing: {e}", exc_info=True)
         raise DatabaseError("An unexpected error occurred during database operation.", original_exception=e) from e

async def create_product(
    container: ContainerProxy,
    product: ProductCreate
) -> ProductRead:
    data = product.model_dump()
    data["id"] = data.get("id", str(uuid.uuid4()))
    try:
        result = await container.create_item(body=data)
        return ProductRead.model_validate(result)
    except CosmosHttpResponseError as e:
        if e.status_code == 409:
            raise ProductAlreadyExistsError(f"Product {data['id']} already exists") from e
        logger.error(f"Cosmos DB error during product creation: Status Code {e.status_code}, Message: {e.message}", exc_info=True)
        raise DatabaseError(f"Cosmos DB error during product creation: Status Code {e.status_code}, Message: {e.message}", original_exception=e) from e
    except Exception as e:
         logger.error(f"Unexpected error during product creation: {e}", exc_info=True)
         raise DatabaseError("An unexpected error occurred during database operation.", original_exception=e) from e

async def delete_product(
    category: str,
    container: ContainerProxy,
    product_id: str,
    ):
    try:
        await container.delete_item(item=product_id, partition_key=category)
        return
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            raise ProductNotFoundError(f"Product with ID '{product_id}' and category '{category}' not found") from e
        logger.error(f"Cosmos DB error during product deletion: Status Code {e.status_code}, Message: {e.message}", exc_info=True)
        raise DatabaseError(f"Cosmos DB error during product deletion: Status Code {e.status_code}, Message: {e.message}", original_exception=e) from e
    except Exception as e:
         logger.error(f"Unexpected error during product deletion: {e}", exc_info=True)
         raise DatabaseError("An unexpected error occurred during database operation.", original_exception=e) from e

async def create_products(
    container: ContainerProxy,
    products: List[ProductCreate]
) -> List[ProductRead]:
    if not products:
        return []
    pk = products[0].category
    batch = container.create_transactional_batch(partition_key=pk)
    try:
        for prod in products:
            data = prod.model_dump()
            data["id"] = data.get("id", str(uuid.uuid4()))
            batch.create_item(body=data)
        response = await batch.execute()
        if not response.get_successful():
            logger.error(f"Transactional batch failed. Status code: {response.status_code}")
            for op in response.get_all_operations():
                if not op.successful:
                    logger.error(f"Batch operation failed: {op.error_message}")
            raise DatabaseError(f"Transactional batch failed with status code: {response.status_code}", original_exception=response)
        items = [op.resource for op in response.get_all_operations()]
        return [ProductRead.model_validate(item) for item in items]
    except CosmosHttpResponseError as e:
        logger.error(f"Cosmos DB error during batch execution: Status Code {e.status_code}, Message: {e.message}", exc_info=True)
        raise DatabaseError(f"Cosmos DB error during batch execution: Status Code {e.status_code}, Message: {e.message}", original_exception=e) from e
    except Exception as e:
        logger.error(f"Unexpected error during batch execution: {e}", exc_info=True)
        raise DatabaseError("An unexpected error occurred during database operation.", original_exception=e) from e
