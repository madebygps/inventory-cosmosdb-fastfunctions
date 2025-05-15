from fastapi import Depends
from azure.cosmos.exceptions import CosmosHttpResponseError
from inventory_api.db import get_container
from inventory_api.models.product import ProductRead, ProductCreate
import uuid
from typing import List

async def list_products(
    container=Depends(get_container),
    category: str = "electronics",
    skip: int = 0,
    limit: int = 50
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
    iterator = container.query_items(query=query, parameters=params)
    items = [item async for item in iterator]
    return [ProductRead.model_validate(i) for i in items]

async def create_product(
    product: ProductCreate,
    container=Depends(get_container)
) -> ProductRead:
    data = product.model_dump()
    data["id"] = data.get("id", str(uuid.uuid4()))
    try:
        result = await container.create_item(body=data)
        return ProductRead.model_validate(result)
    except CosmosHttpResponseError as e:
        if e.status_code == 409:
            raise ValueError(f"Product {data['id']} already exists")
        raise