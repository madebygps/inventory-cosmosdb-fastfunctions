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
from inventory_api.logging_config import logger

router = APIRouter(prefix="/products/batch", tags=["product-batch"])


async def get_products_container() -> ContainerProxy:
    return await get_container(ContainerType.PRODUCTS)


@router.post("/", response_model=List[ProductResponse], status_code=status.HTTP_201_CREATED)
async def add_products_batch(
    batch_create: ProductBatchCreate,
    container: ContainerProxy = Depends(get_products_container),
):
    try:
        return await create_products(container=container, batch_create=batch_create)
    except DatabaseError as e:
        logger.error(f"Database error: {e}", exc_info=e.original_exception)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during batch product creation: {e}", exc_info=True
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
