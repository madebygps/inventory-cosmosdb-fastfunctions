from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class Location(BaseModel):
    """
    Base schema for store location (shared fields).
    """
    name: str
    address: str
    manager: Optional[str] = None

    model_config = ConfigDict(extra="forbid")
       

class LocationCreate(Location):
    """
    Input model for creating a new location.
    """
    pass

class LocationUpdate(BaseModel):
    """
    Input model for updating a location with optimistic concurrency.
    """
    name: Optional[str] = None
    address: Optional[str] = None
    manager: Optional[str] = None
    etag: str = Field(..., alias="_etag")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"
    )
      
class LocationRead(Location):
    """
    Output model for reading location details from Cosmos DB.
    Includes Cosmos DB system properties.
    """
    id: str  # primary key
    etag: Optional[str] = Field(default=None, alias="_etag") 
    ts: Optional[int] = Field(default=None, alias="_ts")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"
    )