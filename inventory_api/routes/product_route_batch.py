from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from inventory_api.models.product import (
    ProductResponse, 
    ProductBatchCreate,
    ProductBatchUpdate,
    ProductBatchDelete
)
from inventory_api.crud.product_crud_batch import (
    create_products,
    update_products,
    delete_products
)
from inventory_api.db import get_container, ContainerType
from azure.cosmos.aio import ContainerProxy

from inventory_api.exceptions import DatabaseError
from inventory_api.logging_config import get_child_logger, tracer

# Create a child logger for this module
logger = get_child_logger("routes.product_batch")

router = APIRouter(prefix="/products/batch", tags=["product-batch"])


async def get_products_container() -> ContainerProxy:
    return await get_container(ContainerType.PRODUCTS)


@router.post("/", response_model=List[ProductResponse], status_code=status.HTTP_201_CREATED)
async def add_products_batch(
    batch_create: ProductBatchCreate,
    container: ContainerProxy = Depends(get_products_container),
):
    with tracer.start_as_current_span("api_add_products_batch") as span:
        batch_size = len(batch_create.items)
        span.set_attribute("batch.size", batch_size)
        
        # Track categories in the batch
        categories = set(item.category for item in batch_create.items)
        span.set_attribute("batch.categories_count", len(categories))
        
        logger.info(
            f"Handling batch create request for {batch_size} products",
            extra={
                "batch_size": batch_size,
                "categories": list(categories)
            }
        )
        
        try:
            result = await create_products(container=container, batch_create=batch_create)
            
            # Log success with metrics
            success_count = len(result)
            span.set_attribute("batch.success_count", success_count)
            span.set_attribute("batch.success_rate", success_count / batch_size if batch_size > 0 else 1.0)
            
            logger.info(
                f"Successfully created {success_count}/{batch_size} products",
                extra={
                    "success_count": success_count,
                    "batch_size": batch_size,
                    "success_rate": success_count / batch_size if batch_size > 0 else 1.0
                }
            )
            
            return result
        except DatabaseError as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "database_error")
            
            logger.error(
                "Database error during batch product creation",
                extra={
                    "error": str(e),
                    "batch_size": batch_size,
                    "categories": list(categories)
                },
                exc_info=e.original_exception
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred.",
            )
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            
            logger.error(
                "Unexpected error during batch product creation",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "batch_size": batch_size
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected internal server error occurred.",
            )


@router.patch("/", response_model=List[ProductResponse])
async def update_products_batch(
    batch_update: ProductBatchUpdate,
    container: ContainerProxy = Depends(get_products_container),
):
    try:
        return await update_products(container=container, batch_update=batch_update)
    except DatabaseError as e:
        logger.error(f"Database error: {e}", exc_info=e.original_exception)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during batch product update: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
        )


@router.delete("/", response_model=List[str])
async def delete_products_batch(
    batch_delete: ProductBatchDelete,
    container: ContainerProxy = Depends(get_products_container),
):
    try:
        return await delete_products(container=container, batch_delete=batch_delete)
    except DatabaseError as e:
        logger.error(f"Database error: {e}", exc_info=e.original_exception)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during batch product deletion: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
        )
