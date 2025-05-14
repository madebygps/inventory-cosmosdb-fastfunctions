from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional

class InventoryItem(BaseModel):
    """
    Base schema for inventory items.
    """
    product_id: str = Field(..., alias="productId")
    location_id: str = Field(..., alias="locationId")  # partition key
    quantity: int
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"
    )
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v

class InventoryItemCreate(InventoryItem):
    """
    Input model for creating a new inventory item.
    """
    pass

class InventoryItemUpdate(BaseModel):
    """
    Input model for updating an inventory item with optimistic concurrency control.
    """
    product_id: str = Field(..., alias="productId")
    location_id: str = Field(..., alias="locationId")
    quantity: int
    etag: str = Field(..., alias="_etag")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"
    )
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v

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