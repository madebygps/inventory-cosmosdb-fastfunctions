import logging
import os
import opentelemetry.trace
from azure.monitor.opentelemetry import configure_azure_monitor

# Configure Azure Monitor (this automatically sets up connection to Application Insights)
# Only configure if running in Azure (determined by FUNCTIONS_WORKER_RUNTIME environment variable)
if os.environ.get("FUNCTIONS_WORKER_RUNTIME"):
    try:
        configure_azure_monitor()
        logging.info("Azure Monitor OpenTelemetry configured successfully")
    except Exception as e:
        logging.error(f"Error configuring Azure Monitor: {str(e)}")

# Get a tracer for the current module (for distributed tracing)
tracer = opentelemetry.trace.get_tracer("inventory_api")

# Configure the logger
logger = logging.getLogger("inventory_api")

# Set to INFO level for more useful logging
logger.setLevel(logging.INFO)

if not logger.handlers:
    # Console handler for local development and Azure Functions console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Add formatter to handler
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)

# Helper function to create child loggers
def get_child_logger(name):
    """Get a child logger with the given name."""
    return logger.getChild(name)