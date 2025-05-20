from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.cosmos.aio import ContainerProxy
import uuid
from typing import Optional
from datetime import datetime
import logging
from builtins import anext

from inventory_api.models.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductList,
    ProductStatus,
)

from inventory_api.exceptions import (
    ProductNotFoundError,
    ProductAlreadyExistsError,
    DatabaseError,
    PreconditionFailedError,
)

logger = logging.getLogger(__name__)


async def list_products(
    container: ContainerProxy,
    category: str,
    continuation_token: Optional[str] = None,
    max_items: int = 50,
) -> ProductList:
    """
    Retrieve a paginated list of products by category.
    """
    query = "SELECT * FROM c WHERE c.category = @category"
    params = [{"name": "@category", "value": category}]

    # Create query options dictionary
    query_options = {"max_item_count": max_items}

    try:
        items = []
        next_continuation_token = None

        # Get the query iterator
        query_iterator = container.query_items(
            query=query, parameters=params, partition_key=category, **query_options
        )

        # Create a page iterator
        page_iterator = query_iterator.by_page(continuation_token)

        # Try to get the first page
        try:
            # Get the first page
            first_page = await anext(page_iterator)

            # Since AsyncList is not directly iterable, we need to iterate it asynchronously
            # Convert AsyncList to a regular list
            page_items = [item async for item in first_page]

            # Process items in the page
            for item in page_items:
                try:
                    product = ProductResponse.model_validate(item)
                    items.append(product)
                except Exception as e:
                    logger.warning(f"Failed to validate product: {e}, item: {item}")
                    continue

            # Get continuation token for next page from the page_iterator
            next_continuation_token = page_iterator.continuation_token

        except StopAsyncIteration:
            # No items found with this continuation token
            pass

        # Return the items and continuation token
        return ProductList(items=items, continuation_token=next_continuation_token)

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
) -> ProductResponse:
    """
    Create a new product in the database.

    Args:
        container: Cosmos DB container client
        product: Product data to create

    Returns:
        Newly created product with system fields

    Raises:
        ProductAlreadyExistsError: If a product with same ID/SKU exists
        DatabaseError: If a database operation fails
    """
    data = product.model_dump()
    data["id"] = str(uuid.uuid4())
    data["status"] = ProductStatus.ACTIVE.value
    data["last_updated"] = datetime.utcnow().isoformat()

    try:
        result = await container.create_item(body=data)
        return ProductResponse.model_validate(result)
    except CosmosHttpResponseError as e:
        if e.status_code == 409:
            raise ProductAlreadyExistsError(
                f"Product with ID {data['id']} or SKU {data.get('sku')} already exists"
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


async def get_product_by_id(
    container: ContainerProxy, product_id: str, category: str
) -> ProductResponse:
    """
    Retrieve a product by its ID and category.

    Args:
        container: Cosmos DB container client
        product_id: ID of the product to retrieve
        category: Category of the product (partition key)

    Returns:
        The retrieved product details

    Raises:
        ProductNotFoundError: If the product doesn't exist
        DatabaseError: If a database operation fails
    """
    try:
        item = await container.read_item(item=product_id, partition_key=category)
        return ProductResponse.model_validate(item)
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


async def update_product(
    container: ContainerProxy,
    product_id: str,
    category: str,
    updates: ProductUpdate,
    etag: str,
) -> ProductResponse:
    """
    Update an existing product.

    Args:
        container: Cosmos DB container client
        product_id: ID of the product to update
        category: Category of the product (partition key)
        updates: Fields to update
        etag: Current ETag for concurrency control

    Returns:
        The updated product

    Raises:
        ProductNotFoundError: If the product doesn't exist
        PreconditionFailedError: If the ETag doesn't match (concurrent update)
        DatabaseError: If a database operation fails
    """
    # Convert model to dict and exclude unset fields
    update_dict = updates.model_dump(exclude_unset=True)

    # Don't proceed if there are no changes
    if not update_dict:
        raise ValueError("No fields provided for update.")

    # Add last_updated timestamp
    update_dict["last_updated"] = datetime.utcnow().isoformat()

    # Create patch operations
    patch_operations = []
    for key, value in update_dict.items():
        if key not in ["id", "category", "_etag"]:
            patch_operations.append({"op": "set", "path": f"/{key}", "value": value})

    try:
        result = await container.patch_item(
            item=product_id,
            partition_key=category,
            patch_operations=patch_operations,
            headers={"if-match": etag},
        )
        return ProductResponse.model_validate(result)
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            raise ProductNotFoundError(
                f"Product with ID '{product_id}' and category '{category}' not found"
            ) from e
        if e.status_code == 412:  # Precondition Failed (ETag mismatch)
            raise PreconditionFailedError(
                f"Product with ID '{product_id}' has been modified since last retrieved (ETag mismatch)."
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


async def delete_product(
    container: ContainerProxy,
    product_id: str,
    category: str,
) -> None:
    """
    Delete a product from the database.

    Args:
        container: Cosmos DB container client
        product_id: ID of the product to delete
        category: Category of the product (partition key)

    Raises:
        ProductNotFoundError: If the product doesn't exist
        DatabaseError: If a database operation fails
    """
    try:
        await container.delete_item(item=product_id, partition_key=category)
        return  # Implicit None
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
