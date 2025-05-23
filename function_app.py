
import azure.functions as func
from fastapi import (
    FastAPI,
    HTTPException,
    Security,
    status,
    Request,
)
from fastapi.responses import HTMLResponse, JSONResponse
from azure.cosmos import exceptions as cosmos_exceptions
from fastapi.security import APIKeyHeader, APIKeyQuery
from fastapi.openapi.docs import get_swagger_ui_html

from inventory_api.logging_config import logger, tracer
from inventory_api.routes.product_route import router as product_router
from inventory_api.routes.product_route_batch import router as product_batch_router

API_KEY_NAME = "x-functions-key"
api_key_header_scheme = APIKeyHeader(
    name=API_KEY_NAME,
    auto_error=False,
    scheme_name="ApiKeyAuthHeader",
    description="API Key (x-functions-key) in header",
)
api_key_query_scheme = APIKeyQuery(
    name="code",
    auto_error=False,
    scheme_name="ApiKeyAuthQuery",
    description="API Key (code) in query string",
)


async def get_api_key(
    api_key_from_header: str = Security(api_key_header_scheme),
    api_key_from_query: str = Security(api_key_query_scheme),
    req: Request = None,
):
    """Validate API key from header or query against Azure Function key if available."""
    client_api_key = api_key_from_header or api_key_from_query
    azure_expected_key = _get_azure_function_key(req)

    if azure_expected_key:
        if not client_api_key or client_api_key != azure_expected_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key.",
            )
    elif not client_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required.",
        )
    return client_api_key


app = FastAPI(
    title="Inventory API",
    version="1.0.0",
    openapi_url="/api/openapi.json",  # Keep this, app.openapi() will use it
    docs_url=None,  # Disable default /docs
    redoc_url=None,  # Optionally disable /redoc
    openapi_components={
        "securitySchemes": {
            api_key_header_scheme.scheme_name: api_key_header_scheme.model.model_dump(
                exclude_none=True
            ),
            api_key_query_scheme.scheme_name: api_key_query_scheme.model.model_dump(
                exclude_none=True
            ),
        }
    },
    dependencies=[Security(get_api_key)],
)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(req: Request) -> HTMLResponse:
    cdn_swagger_js_url = (
        "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.js"
    )
    cdn_swagger_css_url = (
        "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui.css"
    )
    cdn_favicon_url = "https://fastapi.tiangolo.com/img/favicon.png"

    return get_swagger_ui_html(
        openapi_url="",
        title=app.title + " - Swagger UI",
        swagger_ui_parameters={"spec": app.openapi()},
        swagger_js_url=cdn_swagger_js_url,
        swagger_css_url=cdn_swagger_css_url,
        swagger_favicon_url=cdn_favicon_url,
    )


def _get_azure_function_key(request: Request) -> str | None:
    """
    Safely retrieves the Azure Function key from the request context.
    Uses try-except for cleaner attribute access.
    """
    try:
        if request.function_context and request.function_context.function_directory:
            return request.function_context.function_directory.get_function_key()
    except AttributeError:
        pass
    return None


@app.middleware("http")
async def check_api_key_for_docs(request: Request, call_next):
    """
    Middleware to protect documentation endpoints if running in Azure
    and an Azure Function key is configured.
    """
    path = request.url.path
    is_doc_path = path in [app.docs_url, app.redoc_url, app.openapi_url]

    if is_doc_path:
        azure_expected_key = _get_azure_function_key(request)
        if azure_expected_key:
            client_api_key = request.headers.get(
                API_KEY_NAME
            ) or request.query_params.get("code")

            if not client_api_key or client_api_key != azure_expected_key:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Access to documentation requires a valid API key."
                    },
                )
    response = await call_next(request)
    return response


@app.exception_handler(cosmos_exceptions.CosmosHttpResponseError)
async def handle_cosmos_http_error(
    request: Request, exc: cosmos_exceptions.CosmosHttpResponseError
):
    with tracer.start_as_current_span("handle_cosmos_error") as span:
        span.set_attribute("error", True)
        span.set_attribute("error.type", "cosmos_http_error")
        span.set_attribute("error.status_code", exc.status_code)
        
        if exc.status_code in (401, 403):
            logger.warning(
                "Cosmos DB authentication error", 
                extra={"status_code": exc.status_code, "path": request.url.path}
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "detail": "Unauthorized" if exc.status_code == 401 else "Forbidden"
                },
            )
        
        logger.error(
            "Cosmos DB HTTP error", 
            extra={
                "status_code": exc.status_code, 
                "message": str(exc),
                "path": request.url.path
            }
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
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
    with tracer.start_as_current_span("process_request") as span:
        # Add request details to span for better tracing
        span.set_attribute("http.method", req.method)
        span.set_attribute("http.url", str(req.url))
        span.set_attribute("http.route", req.route_params.get('route', ''))
        
        logger.info(
            f"Processing {req.method} request",
            extra={
                "method": req.method,
                "path": str(req.url),
                "query_params": dict(req.params),
                "route": req.route_params.get('route', '')
            }
        )
        
        try:
            response = await func.AsgiMiddleware(app).handle_async(req)
            span.set_attribute("http.status_code", response.status_code)
            return response
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            
            logger.error(
                f"Error processing request: {str(e)}",
                extra={"error_type": type(e).__name__}
            )
            return func.HttpResponse(
                body=str(e),
                status_code=500
            )