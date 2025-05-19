from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class Product(BaseModel):
    name: str
    description: Optional[str] = None
    category: str # partition key
    price: float
    
    model_config = ConfigDict(extra="forbid")

class ProductCreate(Product):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    
    model_config = ConfigDict(
        extra="forbid",
    )

class ProductRead(Product):
    id: str
    etag: Optional[str] = Field(default=None, alias="_etag")
    ts: Optional[int] = Field(default=None, alias="_ts")
    rid: Optional[str] = Field(default=None, alias="_rid")
    self_link: Optional[str] = Field(default=None, alias="_self")
    attachments: Optional[str] = Field(default=None, alias="_attachments")
    
    
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True
    )