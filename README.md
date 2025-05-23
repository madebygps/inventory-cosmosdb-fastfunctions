# Inventory System with Cosmos DB, FastAPI on Azure Functions

## Overview

This project implements an inventory management system using Azure Cosmos DB as the database backend, FastAPI for API development, and deployed as serverless Azure Functions.

## Features

- **Product Management**: Create, read, update, and delete product information
- **Batch Operations**: Perform operations on multiple products simultaneously
- **Pagination**: Retrieve products in manageable chunks with continuation tokens
- **Optimistic Concurrency**: Prevent conflicts using ETags for updates
- **Partition-aware Operations**: Efficient database access with category-based partitioning

## Architecture

- **Azure Functions**: Serverless compute for hosting the API endpoints
- **FastAPI**: Modern, fast web framework for building APIs
- **Azure Cosmos DB**: NoSQL database for storing product data
- **Azure Identity**: Secure access using DefaultAzureCredential
- **Python**: Primary programming language (3.8+)

## Prerequisites

- Azure subscription
- Python 3.8+
- Azure Functions Core Tools v4+
- Azure CLI
- Azure Developer CLI (azd) for simplified deployment
- Azure Cosmos DB account or Cosmos DB Emulator for local development
- Visual Studio Code with Azure Functions extension (recommended)

## Setup and Development

### 1. Clone the repository

```bash
git clone https://github.com/your-username/inventory-cosmosdb-fastfunctions.git
cd inventory-cosmosdb-fastfunctions
```

### 2. Deploy Azure Resources with AZD

```bash
# Login to Azure
azd auth login

# Deploy the application infrastructure
azd up
```

### 3. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Grant your user principal access to the Cosmos DB account

```bash
az cosmosdb sql role assignment create \
  --account-name <your-deployed-cosmos-account-name> \
  --resource-group <your-resource-group> \
  --scope "/" \
  --principal-id $(az ad signed-in-user show --query id -o tsv) \
  --role-definition-id "00000000-0000-0000-0000-000000000002"
```

### 5. Configure local settings

```bash
cp local.settings.sample.json local.settings.json
```

Update `local.settings.json` with your Azure Cosmos DB information:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsFeatureFlags": "EnableWorkerIndexing",
    "COSMOSDB_ENDPOINT": "YOUR_DEPLOYED_COSMOS_DB_ENDPOINT",
    "COSMOSDB_DATABASE": "inventory",
    "COSMOSDB_CONTAINER_PRODUCTS": "products"
  }
}
```

### 6. Run the function locally

```bash
func start
```

## API Endpoints

### Product Management

- **GET /products/**
  - List products by category with pagination
  - Query parameters:
    - `category`: Category to filter by (required)
    - `continuation_token`: Token for pagination (optional)
    - `limit`: Maximum items to return (default: 50)

- **GET /products/{product_id}**
  - Get a specific product
  - Query parameters:
    - `category`: Category of the product (required)

- **POST /products/**
  - Create a new product
  - Body: Product details

- **PATCH /products/{product_id}**
  - Update a product
  - Query parameters:
    - `category`: Category of the product (required)
  - Headers:
    - `If-Match`: ETag for optimistic concurrency
  - Body: Fields to update

- **DELETE /products/{product_id}**
  - Delete a product
  - Query parameters:
    - `category`: Category of the product (required)

### Batch Operations

- **POST /products/batch/**
  - Create multiple products in a single operation
  - Body: List of products to create

- **PATCH /products/batch/**
  - Update multiple products in a single operation
  - Body: List of products with their ETags and changes

- **DELETE /products/batch/**
  - Delete multiple products in a single operation
  - Body: List of product IDs and categories to delete

## Data Model

### Product

```python
{
    "id": "string",  # UUID, auto-generated
    "name": "string",  # Required
    "description": "string",  # Optional
    "category": "string",  # Required - Used as partition key
    "price": float,  # Required
    "sku": "string",  # Required - Stock keeping unit
    "quantity": int,  # Default: 0
    "status": "string",  # "active" or "inactive"
    "last_updated": "datetime"  # Auto-updated timestamp
}
```

## API Documentation

The API includes Swagger documentation available at the `/docs` endpoint when running locally or in Azure.

## Security

- API authentication is implemented using Azure Functions authentication
- API keys can be provided via:
  - Header: `x-functions-key`
  - Query parameter: `code`
