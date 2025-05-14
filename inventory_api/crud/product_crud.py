from inventory_api.db import get_container
from inventory_api.models.product import ProductRead, ProductCreate
from azure.cosmos.exceptions import CosmosHttpResponseError
import uuid
from typing import List


async def list_products(category: str = 'electronics', skip: int = 0, limit: int = 50) -> List[ProductRead]:
    """List products with optional filtering by category."""
    container = get_container('products')
    
    if category:
        query = "SELECT * FROM c WHERE c.category = @category OFFSET @skip LIMIT @limit"
        parameters = [
            {"name": "@category", "value": category},
            {"name": "@skip", "value": skip},
            {"name": "@limit", "value": limit}
        ]
    else:
        query = "SELECT * FROM c OFFSET @skip LIMIT @limit"
        parameters = [
            {"name": "@skip", "value": skip},
            {"name": "@limit", "value": limit}
        ]
    
    items = list(container.query_items(
        query=query,
        parameters=parameters
      
    ))
    
    return [ProductRead.model_validate(item) for item in items]


async def create_product(product: ProductCreate) -> ProductRead:
    """Create a new product."""
    container = get_container('products')
    
    # Generate a unique ID if not provided
    product_dict = product.model_dump()
    product_dict["id"] = product_dict.get("id", str(uuid.uuid4()))
    
    try:
        # Let Cosmos DB handle duplication conflicts
        result = container.create_item(body=product_dict)
        return ProductRead.model_validate(result)
    except CosmosHttpResponseError as e:
        if e.status_code == 409:  # HTTP 409 Conflict
            raise ValueError(f"Product with ID {product_dict['id']} already exists.")
        raise  # Re-raise other exceptions for handling at a higher level