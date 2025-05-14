"""
Database Package

This package contains database connection utilities.
"""

from db.cosmosdb_client import get_cosmos_client

__all__ = ['get_cosmos_client']
