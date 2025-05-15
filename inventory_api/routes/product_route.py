from fastapi import APIRouter, HTTPException, status, Depends
from inventory_api.models.product import ProductRead, ProductCreate
from inventory_api.crud.product_crud import list_products, create_product
from inventory_api.db import get_container

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=list[ProductRead])
async def get_products(
    category: str = 'electronics',
    skip: int = 0,
    limit: int = 50,
    container = Depends(get_container),
):
    return await list_products(container, category=category, skip=skip, limit=limit)

@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def add_new_product(
    product: ProductCreate,
    container = Depends(get_container),
):
    try:
        return await create_product(product, container)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating product: {e}"
        )