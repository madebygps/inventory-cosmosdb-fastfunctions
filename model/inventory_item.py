from pydantic import BaseModel, Field
from typing import Optional

class InventoryItem(BaseModel):
    productId: str
    locationId: str  # partition key
    quantity: int

class InventoryItemCreate(InventoryItem):
    """
    Input model for creating a new inventory item.
    """
    pass

class InventoryItemUpdate(BaseModel):
    """
    Input model for updating an inventory item with concurrency check.
    """
    productId: str
    locationId: str
    quantity: int
    etag: str = Field(..., alias="_etag")

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"

class InventoryItemRead(InventoryItem):
    """
    Output model for reading inventory item details.
    """
    id: str
    etag: Optional[str] = Field(default=None, alias="_etag")
    ts: Optional[int] = Field(default=None, alias="_ts")

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"

