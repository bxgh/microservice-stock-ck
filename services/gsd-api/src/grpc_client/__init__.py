"""
gRPC Client for mootdx-source DataSource Service
"""
from .client import (
    DataSourceClient,
    get_datasource_client,
    close_datasource_client
)

__all__ = [
    "DataSourceClient",
    "get_datasource_client",
    "close_datasource_client"
]

