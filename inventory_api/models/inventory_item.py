from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class InventoryItem(BaseModel):
    """
    Base schema for inventory items.
    """
    product_id: str = Field(..., alias="productId")
    location_id: str = Field(..., alias="locationId")  # partition key
    quantity: int = Field(..., ge=0)
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"
    )
    
class InventoryItemCreate(InventoryItem):
    """
    Input model for creating a new inventory item.
    """
    pass

class InventoryItemUpdate(BaseModel):
    """
    Input model for updating an inventory item with optimistic concurrency control.
    """
    product_id: Optional[str] = Field(None, alias="productId")
    location_id: Optional[str] = Field(None, alias="locationId")
    quantity: Optional[int] = Field(default=None, ge=0)

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"
    )
    
class InventoryItemRead(InventoryItem):
    """
    Output model for reading inventory item details from Cosmos DB.
    Includes Cosmos DB system properties.
    """
    id: str
    etag: Optional[str] = Field(default=None, alias="_etag")
    ts: Optional[int] = Field(default=None, alias="_ts")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"
    )