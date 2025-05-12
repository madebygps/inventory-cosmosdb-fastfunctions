from typing import Optional
from pydantic import BaseModel, Field

class Location(BaseModel):
    """
    Base schema for store location (shared fields).
    """
    name: str
    address: str
    manager: Optional[str] = None

    class Config:
        extra = "forbid"
       

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

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"
      
class LocationRead(Location):
    """
    Output model for reading location details from Cosmos DB.
    """
    id: str  # partition key
    _etag: Optional[str] = Field(default=None, alias="_etag")
    _ts: Optional[int] = Field(default=None, alias="_ts")

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"
       
