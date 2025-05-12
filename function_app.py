import logging
from typing import List, Dict, Any, Optional

import azure.functions as func
from fastapi import (
    FastAPI, Depends, HTTPException, status, Query, Request, Header, Response
)
from fastapi.responses import JSONResponse
from azure.cosmos import exceptions as cosmos_exceptions


function_app = func.FunctionApp()

@function_app.route(route="{*route}", auth_level=func.AuthLevel.FUNCTION)
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Functions entry‑point routed through FastAPI."""
    return await func.AsgiMiddleware(app).handle_async(req)
