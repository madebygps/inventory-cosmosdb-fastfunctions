from typing import Optional
from fastapi import APIRouter, Body, HTTPException, Header, Path, Query, status, Depends
from inventory_api.models.product import (
    ProductList,
    ProductResponse,
    ProductCreate,
    ProductUpdate,
)
from inventory_api.crud.product_crud import (
    get_product_by_id,
    list_products,
    create_product,
    delete_product,
    update_product,
)
from inventory_api.db import get_container, ContainerType
from azure.cosmos.aio import ContainerProxy

from inventory_api.exceptions import (
    PreconditionFailedError,
    ProductNotFoundError,
    ProductAlreadyExistsError,
    DatabaseError,
)

from inventory_api.logging_config import logger

router = APIRouter(prefix="/products", tags=["products"])


async def get_products_container() -> ContainerProxy:
    return await get_container(ContainerType.PRODUCTS)


@router.get("/", response_model=ProductList)
async def get_products(
    category: str = Query("electronics", title="The category to filter products by"),
    continuation_token: Optional[str] = Query(None, title="Token for pagination"),
    limit: int = Query(50, title="Maximum number of items to return"),
    container: ContainerProxy = Depends(get_products_container),
):
    try:
        return await list_products(
            container=container,
            category=category,
            max_items=limit,
            continuation_token=continuation_token,
        )
    except DatabaseError as e:
        logger.error(f"Database error: {e}", exc_info=e.original_exception)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )
    except Exception as e:
        logger.error(f"Unexpected error listing products: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
        )


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def add_new_product(
     product: ProductCreate = Body(..., description="Product information to create"),
    container: ContainerProxy = Depends(get_products_container),
):
    try:
        return await create_product(container=container, product=product)
    except ProductAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error: {e}", exc_info=e.original_exception)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during product creation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_product(
    category: str = Query(..., title="The category of the product (partition key)"),
    container: ContainerProxy = Depends(get_products_container),
    product_id: str = Path(..., title="The ID of the product to delete"),
):
    try:
        await delete_product(
            category=category, container=container, product_id=product_id
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error: {e}", exc_info=e.original_exception)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in DELETE /products/{product_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
        )


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_existing_product(
    updated_product: ProductUpdate,
    product_id: str = Path(..., title="The ID of the product to update"),
    category: str = Query(..., title="The category of the product (partition key)"),
    container: ContainerProxy = Depends(get_products_container),
    if_match_etag: str = Header(
        ...,
        alias="If-Match",
        description="ETag from the previous GET request for optimistic concurrency",
    ),
):
    try:
        return await update_product(
            container=container,
            product_id=product_id,
            category=category,
            updates=updated_product,
            etag=if_match_etag,
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PreconditionFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(e)
        )
    except DatabaseError as e:
        logger.error(
            f"Database error during product update: {e}", exc_info=e.original_exception
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during product update: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str = Path(..., title="The ID of the product to retrieve"),
    category: str = Query(..., title="The category of the product (partition key)"),
    container: ContainerProxy = Depends(get_products_container),
):
    try:
        return await get_product_by_id(
            container=container, product_id=product_id, category=category
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error: {e}", exc_info=e.original_exception)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error retrieving product {product_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
        )
