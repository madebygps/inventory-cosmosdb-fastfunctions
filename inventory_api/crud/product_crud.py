from collections import defaultdict
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosBatchOperationError
from inventory_api.models.product import ProductRead, ProductCreate
from azure.cosmos.aio import ContainerProxy
import uuid
from typing import Any, Dict, List, Tuple
from inventory_api.exceptions import (
    ProductNotFoundError,
    ProductAlreadyExistsError,
    DatabaseError,
    PreconditionFailedError,
)
from inventory_api.logging_config import logger
from azure.core import MatchConditions


async def list_products(
    container: ContainerProxy,
    category: str = "electronics",
    limit: int = 50,
    skip: int = 0,
) -> List[ProductRead]:
    query = (
        "SELECT * FROM c WHERE c.category=@cat OFFSET @skip LIMIT @limit"
        if category
        else "SELECT * FROM c OFFSET @skip LIMIT @limit"
    )
    params = [
        {"name": "@cat", "value": category},
        {"name": "@skip", "value": skip},
        {"name": "@limit", "value": limit},
    ]
    try:
        iterator = container.query_items(query=query, parameters=params)
        items = [item async for item in iterator]
        return [ProductRead.model_validate(i) for i in items]
    except CosmosHttpResponseError as e:
        logger.error(
            f"Cosmos DB error during product listing: Status Code {e.status_code}, Message: {e.message}",
            exc_info=True,
        )
        raise DatabaseError(
            f"Cosmos DB error during product listing: Status Code {e.status_code}, Message: {e.message}",
            original_exception=e,
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during product listing: {e}", exc_info=True)
        raise DatabaseError(
            "An unexpected error occurred during database operation.",
            original_exception=e,
        ) from e


async def create_product(
    container: ContainerProxy, product: ProductCreate
) -> ProductRead:
    data = product.model_dump()
    data["id"] = data.get("id", str(uuid.uuid4()))
    try:
        result = await container.create_item(body=data)
        return ProductRead.model_validate(result)
    except CosmosHttpResponseError as e:
        if e.status_code == 409:
            raise ProductAlreadyExistsError(
                f"Product {data['id']} already exists"
            ) from e
        logger.error(
            f"Cosmos DB error during product creation: Status Code {e.status_code}, Message: {e.message}",
            exc_info=True,
        )
        raise DatabaseError(
            f"Cosmos DB error during product creation: Status Code {e.status_code}, Message: {e.message}",
            original_exception=e,
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during product creation: {e}", exc_info=True)
        raise DatabaseError(
            "An unexpected error occurred during database operation.",
            original_exception=e,
        ) from e


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
            raise ProductNotFoundError(
                f"Product with ID '{product_id}' and category '{category}' not found"
            ) from e
        logger.error(
            f"Cosmos DB error during product deletion: Status Code {e.status_code}, Message: {e.message}",
            exc_info=True,
        )
        raise DatabaseError(
            f"Cosmos DB error during product deletion: Status Code {e.status_code}, Message: {e.message}",
            original_exception=e,
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during product deletion: {e}", exc_info=True)
        raise DatabaseError(
            "An unexpected error occurred during database operation.",
            original_exception=e,
        ) from e


async def update_product(
    container: ContainerProxy,
    product_id: str,
    category: str,
    updated_product_data: Dict[str, Any],
    etag: str,
) -> ProductRead:
    """ """
    patch_operations = []
    for key, value in updated_product_data.items():
        if key != "_etag":
            patch_operations.append({"op": "set", "path": f"/{key}", "value": value})

    if not patch_operations:
        raise ValueError("No fields provided for update.")

    try:
        result = await container.patch_item(
            item=product_id,
            partition_key=category,
            patch_operations=patch_operations,
            etag=etag,
            match_condition=MatchConditions.IfNotModified,
        )

        return ProductRead.model_validate(result)

    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            raise ProductNotFoundError(
                f"Product with ID '{product_id}' and category '{category}' not found"
            ) from e
        if e.status_code == 412:
            raise PreconditionFailedError(
                f"Product with ID '{product_id}' has been modified since last retrieved."
            ) from e
        logger.error(
            f"Cosmos DB error during product update: Status Code {e.status_code}, Message: {e.message}",
            exc_info=True,
        )
        raise DatabaseError(
            f"Cosmos DB error during product update: Status Code {e.status_code}, Message: {e.message}",
            original_exception=e,
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during product update: {e}", exc_info=True)
        raise DatabaseError(
            "An unexpected error occurred during database operation.",
            original_exception=e,
        ) from e


async def get_product_by_id(
    container: ContainerProxy, product_id: str, category: str
) -> ProductRead:
    try:
        item = await container.read_item(item=product_id, partition_key=category)
        return ProductRead.model_validate(item)
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            raise ProductNotFoundError(
                f"Product with ID '{product_id}' and category '{category}' not found"
            ) from e
        logger.error(
            f"Cosmos DB error retrieving product {product_id}: Status {e.status_code}, Msg: {e.message}",
            exc_info=True,
        )
        raise DatabaseError(
            f"Cosmos DB error retrieving product {product_id}: Status {e.status_code}, Msg: {e.message}",
            original_exception=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error retrieving product {product_id}: {e}", exc_info=True
        )
        raise DatabaseError(
            "An unexpected error occurred during database operation.",
            original_exception=e,
        ) from e


async def create_products(
    container: ContainerProxy, products: List[ProductCreate]
) -> List[ProductRead]:
    if not products:
        return []

    products_by_category: Dict[str, List[ProductCreate]] = defaultdict(list)
    for product_model in products:
        products_by_category[product_model.category].append(product_model)

    all_successfully_created_products: List[ProductRead] = []

    for category_pk, product_list_for_category in products_by_category.items():
        if not product_list_for_category:
            continue

        batch_operations: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []

        product_data_for_batch = []

        for product_to_create in product_list_for_category:
            data = product_to_create.model_dump()
            data["id"] = data.get("id", str(uuid.uuid4()))
            product_data_for_batch.append(data)  # Store the full data with ID
            batch_operations.append(("create", (data,), {}))

        if not batch_operations:
            continue

        try:
            batch_results = await container.execute_item_batch(
                batch_operations=batch_operations, partition_key=category_pk
            )

            for result_item in batch_results:
                if isinstance(result_item, dict) and result_item.get("id"):
                    all_successfully_created_products.append(
                        ProductRead.model_validate(result_item)
                    )
                else:
                    logger.warning(
                        f"Unexpected item in successful batch result for category '{category_pk}': {result_item}"
                    )

        except CosmosBatchOperationError as e:
            logger.error(
                f"Cosmos DB Batch Operation Error for category '{category_pk}': "
                f"First failed operation index: {e.error_index}. Message: {str(e)}",
                exc_info=True,
            )
            for i, op_response in enumerate(e.operation_responses):
                attempted_item_id = product_data_for_batch[i].get("id", "unknown_id")
                if (
                    op_response.get("statusCode", 200) >= 400
                ):  # Check if it's an error response
                    logger.error(
                        f"  Failed operation in batch for item ID '{attempted_item_id}': {op_response}"
                    )
                else:
                    logger.info(
                        f"  Operation response (may be pre-failure success) for item ID '{attempted_item_id}': {op_response}"
                    )

        except CosmosHttpResponseError as e_http:
            logger.error(
                f"Cosmos DB HTTP error during execute_item_batch for category '{category_pk}': "
                f"Status Code {e_http.status_code}, Message: {e_http.message}. ",
                exc_info=True,
            )
        except Exception as e_generic:
            logger.error(
                f"Unexpected error during execute_item_batch for category '{category_pk}': {e_generic}",
                exc_info=True,
            )

    return all_successfully_created_products
