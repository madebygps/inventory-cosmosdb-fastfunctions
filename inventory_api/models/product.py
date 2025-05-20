from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProductStatus(str, Enum):
    """
    Status options for products in the inventory system.
    
    ACTIVE: Product is available for use
    INACTIVE: Product is not currently available (discontinued, seasonal, etc.)
    """
    ACTIVE = "active"
    INACTIVE = "inactive"


class Product(BaseModel):
    """
    Core product attributes shared across creation and reading.
    
    Contains the essential fields that define a product in the inventory system.
    This is the base model that other product-related models extend.
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
    Request model for creating a new product.
    
    Contains all required fields to create a product in the system.
    The server will generate an ID and other system fields.
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
    Fields that can be modified when updating a product.
    
    All fields are optional since this is used for partial updates.
    Only include the fields you want to change.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    status: Optional[ProductStatus] = None
    
    model_config = ConfigDict(extra="forbid")


class ProductResponse(BaseModel):
    """
    Complete product information returned by the API.
    
    Includes all product fields plus system-generated fields like ID and ETag.
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
        extra="ignore",  # Ignore extra fields from Cosmos DB
        populate_by_name=True,  # Allow both alias and actual field names
        json_encoders={datetime: lambda dt: dt.isoformat()}  # Handle datetime serialization
    )
    
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """
        Custom validation to handle datetime parsing and field mapping.
        """
        # If last_updated is a string, it will be parsed automatically
        # If it's missing, use current time as fallback
        if "last_updated" not in obj and "_ts" in obj:
            # Convert Cosmos DB timestamp (seconds since epoch) to datetime
            obj["last_updated"] = datetime.fromtimestamp(obj["_ts"])
        
        return super().model_validate(obj, *args, **kwargs)

class ProductBatchCreate(BaseModel):
    """
    Request model for creating multiple products in a single operation.
    
    Use this for efficient bulk creation when adding multiple products at once.
    """
    items: List[ProductCreate]  # List of products to create
    
    model_config = ConfigDict(extra="forbid")


class ProductBatchUpdateItem(BaseModel):
    """
    Represents a single product to update in a batch request.
    
    Each item contains the necessary identifiers (id, category, etag)
    and the specific changes to apply to that product.
    """
    id: str  # Product ID to update
    category: str  # Category is required for Cosmos DB operations
    etag: str = Field(alias="_etag")  # Ensures no conflicting updates
    changes: ProductUpdate  # The specific fields to update
    
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ProductBatchUpdate(BaseModel):
    """
    Request model for updating multiple products in a single operation.
    
    Use this for efficient bulk updates when modifying multiple products at once.
    """
    items: List[ProductBatchUpdateItem]  # List of products to update


class ProductBatchDeleteItem(BaseModel):
    """
    Represents a single product to delete in a batch request.
    
    Contains the minimum fields needed to identify a product for deletion.
    """
    id: str  # Product ID to delete
    category: str  # Category is required for Cosmos DB operations
    
    model_config = ConfigDict(extra="forbid")


class ProductBatchDelete(BaseModel):
    """
    Request model for deleting multiple products in a single operation.
    
    Use this for efficient bulk deletion when removing multiple products at once.
    """
    items: List[ProductBatchDeleteItem]  # List of products to delete


class ProductList(BaseModel):
    """
    Response model for product listing endpoints.
    
    Contains a paginated list of products and continuation token
    for retrieving the next set of results.
    """
    items: List[ProductResponse]  # The products in this page of results
    continuation_token: Optional[str] = None  # Token for fetching the next page
    
    model_config = ConfigDict(extra="forbid")
