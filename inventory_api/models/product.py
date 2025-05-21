from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProductStatus(str, Enum):
    """
    Status options for products in the inventory system.
    ACTIVE: Product is available for sale
    INACTIVE: Product is not available (discontinued, seasonal, etc.)
    """

    ACTIVE = "active"
    INACTIVE = "inactive"


class Product(BaseModel):
    """
    Core product fields.
    """

    name: str  # Product display name
    description: Optional[str] = None  # Detailed product description
    category: str  # Product category - used as partition key in Cosmos DB
    price: float  # Current product price
    sku: str  # Stock keeping unit - unique product identifier
    quantity: int = 0  # Current inventory quantity

    model_config = ConfigDict(extra="forbid")


class ProductCreate(BaseModel):
    """
    Fields a client needs to provide to create a product.
    """

    name: str
    description: Optional[str] = None
    category: str
    price: float
    sku: str
    quantity: int = 0

    model_config = ConfigDict(extra="forbid")


class ProductUpdate(BaseModel):
    """
    Fields a client can provide to update a product.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    status: Optional[ProductStatus] = None

    model_config = ConfigDict(extra="forbid")


class ProductResponse(BaseModel):
    """
    All product fields plus system-generated fields.
    This is what clients receive when requesting product details.
    """

    id: str
    name: str
    description: Optional[str] = None
    category: str
    price: float
    sku: str
    quantity: int
    etag: str = Field(alias="_etag")  # Cosmos DB concurrency control token
    status: ProductStatus = ProductStatus.ACTIVE
    last_updated: datetime  # When the product was last modified

    # Add Cosmos DB system fields as optional
    _rid: Optional[str] = None
    _self: Optional[str] = None
    _attachments: Optional[str] = None
    _ts: Optional[int] = None

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        json_encoders={datetime: lambda dt: dt.isoformat()},
    )

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """
        Custom validation to handle datetime parsing and field mapping.
        """
        # If last_updated is not provided, use _ts to set it
        if "last_updated" not in obj and "_ts" in obj:
            obj["last_updated"] = datetime.fromtimestamp(obj["_ts"])

        return super().model_validate(obj, *args, **kwargs)


class ProductBatchCreate(BaseModel):
    """
    Request model for creating multiple products in a single operation.
    """

    items: List[ProductCreate]

    model_config = ConfigDict(extra="forbid")


class ProductBatchUpdateItem(BaseModel):
    """
    Represents a single product to update in a batch request.

    Each item contains the necessary identifiers (id, category, etag)
    and the specific changes to apply to that product.
    """

    id: str
    category: str
    etag: str = Field(alias="_etag")
    changes: ProductUpdate

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ProductBatchUpdate(BaseModel):
    """
    Request model for updating multiple products in a single operation.
    """

    items: List[ProductBatchUpdateItem]


class ProductBatchDeleteItem(BaseModel):
    """
    Represents a single product to delete in a batch request.
    """

    id: str  
    category: str 

    model_config = ConfigDict(extra="forbid")


class ProductBatchDelete(BaseModel):
    """
    Request model for deleting multiple products in a single operation.
    """

    items: List[ProductBatchDeleteItem] 


class ProductList(BaseModel):
    """
    Response model for product listing endpoints.

    Contains a paginated list of products and continuation token
    for retrieving the next set of results.
    """

    items: List[ProductResponse]  
    continuation_token: Optional[str] = None

    model_config = ConfigDict(extra="forbid")
