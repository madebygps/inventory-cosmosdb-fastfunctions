from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.cosmos.aio import ContainerProxy
import uuid
from typing import Optional
from datetime import datetime, timezone
from builtins import anext

from pydantic import ValidationError

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

from inventory_api.logging_config import get_child_logger, tracer

# Create a child logger for this module
logger = get_child_logger("crud.product")


def normalize_category(category: str) -> str:
    """
    Normalize category for case-insensitive operations.
    
    Args:
        category: The original category string
        
    Returns:
        Normalized category string (lowercase)
    """
    return category.lower().strip()


async def list_products(
    container: ContainerProxy,
    category: str,
    continuation_token: Optional[str] = None,
    max_items: int = 50,
) -> ProductList:
    """
    Retrieve a paginated list of products by category.
    """
    with tracer.start_as_current_span("list_products") as span:
        span.set_attribute("category", category)
        span.set_attribute("max_items", max_items)
        span.set_attribute("has_continuation_token", continuation_token is not None)
        
        logger.info(
            "Listing products", 
            extra={
                "category": category, 
                "max_items": max_items,
                "has_continuation_token": continuation_token is not None
            }
        )
        
        # Normalize category for case-insensitive search
        normalized_category = normalize_category(category)
        
        query = "SELECT * FROM c WHERE UPPER(c.category) = UPPER(@category)"
        params = [{"name": "@category", "value": normalized_category}]

        # Create query options dictionary
        query_options = {"max_item_count": max_items}

        try:
            items = []
            next_continuation_token = None

            # Represents the entire potential result set of the query
            query_iterator = container.query_items(
                query=query, parameters=params, partition_key=category, **query_options
            )

            # Mechanism to get page (subset) of total result set at a time
            page_iterator = query_iterator.by_page(continuation_token)

            try:
                # Get page of items
                page = await anext(page_iterator)

                # Get items in the page
                page_items = [item async for item in page]

                # Process items in the page
                for item in page_items:
                    try:
                        product = ProductResponse.model_validate(item)
                        items.append(product)
                    except ValidationError as e:
                        logger.debug(f"Pydantic validation errors: {e.errors()}")
                        continue

                # Get continuation token for next page from the page_iterator
                next_continuation_token = page_iterator.continuation_token
                
                logger.info(f"Retrieved {len(items)} products", extra={"count": len(items)})
                span.set_attribute("products.count", len(items))
                span.set_attribute("has_more_results", next_continuation_token is not None)

            except StopAsyncIteration:
                logger.info("No results found or end of results reached")
                span.set_attribute("products.count", 0)

            return ProductList(items=items, continuation_token=next_continuation_token)

        except CosmosHttpResponseError as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "cosmos_http_error")
            span.set_attribute("error.status_code", e.status_code)
            
            logger.error(
                "Cosmos DB error during product listing",
                extra={
                    "status_code": e.status_code, 
                    "message": e.message,
                    "category": category
                },
                exc_info=True,
            )
            raise DatabaseError(
                f"Cosmos DB error during product listing: Status Code {e.status_code}, Message: {e.message}",
                original_exception=e,
            ) from e
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            
            logger.error(
                "Unexpected error during product listing", 
                extra={
                    "error_type": type(e).__name__,
                    "category": category
                },
                exc_info=True
            )
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
    with tracer.start_as_current_span("create_product") as span:
        data = product.model_dump()
        data["id"] = str(uuid.uuid4())
        data["status"] = ProductStatus.ACTIVE.value
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # Normalize category for consistent storage
        data["category"] = normalize_category(data["category"])
        
        # Add attributes to span for tracing
        span.set_attribute("product.id", data["id"])
        span.set_attribute("product.category", data["category"])
        span.set_attribute("product.name", data["name"])
        
        logger.info(
            "Creating new product",
            extra={
                "product_id": data["id"],
                "category": data["category"],
                "product_name": data["name"]
            }
        )

        try:
            result = await container.create_item(body=data)
            logger.info(
                "Product created successfully",
                extra={"product_id": data["id"], "category": data["category"]}
            )
            return ProductResponse.model_validate(result)
        except CosmosHttpResponseError as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "cosmos_http_error")
            span.set_attribute("error.status_code", e.status_code)
            
            if e.status_code == 409:
                logger.warning(
                    "Product already exists",
                    extra={"product_id": data["id"], "category": data["category"]}
                )
                raise ProductAlreadyExistsError(
                    f"Product with ID {data['id']} or SKU {data.get('sku')} already exists"
                ) from e
                
            logger.error(
                "Cosmos DB error during product creation",
                extra={
                    "status_code": e.status_code,
                    "message": e.message,
                    "product_id": data["id"],
                    "category": data["category"]
                },
                exc_info=True,
            )
            raise DatabaseError(
                f"Cosmos DB error during product creation: Status Code {e.status_code}, Message: {e.message}",
                original_exception=e,
            ) from e
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            
            logger.error(
                "Unexpected error during product creation",
                extra={
                    "error_type": type(e).__name__,
                    "product_id": data["id"],
                    "category": data["category"]
                },
                exc_info=True
            )
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
    with tracer.start_as_current_span("get_product_by_id") as span:
        # Normalize category for consistent lookup
        normalized_category = normalize_category(category)
        
        # Add attributes to span for tracing
        span.set_attribute("product.id", product_id)
        span.set_attribute("product.category", normalized_category)
        
        logger.info(
            "Retrieving product by ID",
            extra={"product_id": product_id, "category": normalized_category}
        )
        
        try:
            item = await container.read_item(item=product_id, partition_key=normalized_category)
            logger.info(
                "Product retrieved successfully",
                extra={"product_id": product_id, "category": category}
            )
            return ProductResponse.model_validate(item)
        except CosmosHttpResponseError as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "cosmos_http_error")
            span.set_attribute("error.status_code", e.status_code)
            
            if e.status_code == 404:
                logger.warning(
                    "Product not found",
                    extra={"product_id": product_id, "category": category}
                )
                raise ProductNotFoundError(
                    f"Product with ID '{product_id}' and category '{category}' not found"
                ) from e
            
            logger.error(
                "Cosmos DB error retrieving product",
                extra={
                    "product_id": product_id,
                    "category": category,
                    "status_code": e.status_code,
                    "message": e.message
                },
                exc_info=True,
            )
            raise DatabaseError(
                f"Cosmos DB error retrieving product {product_id}: Status {e.status_code}, Msg: {e.message}",
                original_exception=e,
            ) from e
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            
            logger.error(
                "Unexpected error retrieving product",
                extra={
                    "product_id": product_id,
                    "category": category,
                    "error_type": type(e).__name__
                },
                exc_info=True
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
    update_dict = updates.model_dump(exclude_unset=True)

    # If no fields are provided for update, raise an error
    if not update_dict:
        raise ValueError("No fields provided for update.")

    # Normalize category for consistent lookup
    normalized_category = normalize_category(category)

    # Update the last_updated field
    update_dict["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Create list of patch (set) operations
    patch_operations = []
    for key, value in update_dict.items():
        if key not in ["id", "category", "_etag"]: # Exclude system fields
            patch_operations.append({"op": "set", "path": f"/{key}", "value": value})

    try:
        result = await container.patch_item(
            item=product_id,
            partition_key=normalized_category,
            patch_operations=patch_operations,
            headers={"if-match": etag}, # ETag for concurrency control
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
    # Normalize category for consistent lookup
    normalized_category = normalize_category(category)
    
    try:
        await container.delete_item(item=product_id, partition_key=normalized_category)
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
