import logging

import azure.functions as func
from fastapi import (
    FastAPI, status, Request
)
from fastapi.responses import JSONResponse
from azure.cosmos import exceptions as cosmos_exceptions

from inventory_api.routes.product_route import router as product_router
from inventory_api.routes.product_route_batch import router as product_batch_router

app = FastAPI(
    title="Inventory API",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/docs",
)

@app.exception_handler(cosmos_exceptions.CosmosHttpResponseError)
async def handle_cosmos_http_error(
    _: Request, exc: cosmos_exceptions.CosmosHttpResponseError
):
    if exc.status_code in (401, 403):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": "Unauthorized" if exc.status_code == 401 else "Forbidden"},
        )
    logging.error(f"Cosmos DB HTTP error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
    )

@app.exception_handler(ValueError)
async def handle_value_error(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

app.include_router(product_router)
app.include_router(product_batch_router)

function_app = func.FunctionApp()

@function_app.route(route="{*route}", auth_level=func.AuthLevel.FUNCTION)
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Functions entry‑point routed through FastAPI."""
    return await func.AsgiMiddleware(app).handle_async(req)