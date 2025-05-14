from fastapi import APIRouter, HTTPException, status

from inventory_api.models.product import ProductRead, ProductCreate
from inventory_api.crud.product_crud import list_products, create_product


router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=list[ProductRead])
async def get_products(
    category: str = 'electronics', skip: int = 0, limit: int = 50
):
    return await list_products(category=category, skip=skip, limit=limit)

@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def add_new_product(product: ProductCreate):
    try:
        return await create_product(product)
    except ValueError as e:
        # Handle product already exists error
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the product: {str(e)}"
        )