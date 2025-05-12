from pydantic import BaseModel, Field
from typing import Optional

class Product(BaseModel):
    name: str
    description: Optional[str] = None
    category: str  # partition key
    price: float

    class Config:
        extra = "forbid"

class ProductCreate(Product):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    etag: str = Field(..., alias="_etag")

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"

class ProductRead(Product):
    id: str
    etag: Optional[str] = Field(default=None, alias="_etag")
    ts: Optional[int] = Field(default=None, alias="_ts")

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"
        