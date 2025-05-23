# Inventory CosmosDB Fast Functions

## Prerequisites

- Azure Functions Core Tools
- Python 3.11+ (if using Python)
- Azure CLI
- Azure Developer CLI (azd)

## Getting Started

### 1. Deploy to Azure First

Before running locally, you need to deploy the application to Azure to generate the necessary environment configuration:

```bash
# Deploy to Azure (this will create the .azure folder with environment settings)
azd up
```

### 2. Configure Azure CLI Authentication

Make sure you're logged into Azure CLI with the same account used to deploy the project:

```bash
# Login to Azure CLI
az login

# Verify you're using the correct account
az account show
```

### 3. Configure Cosmos DB Access

You need to grant your user account access to the Cosmos DB instance. Update the script with your actual values:

```bash
# Update the values in cosmosdb_access.sh with your account name and resource group
# Then run:
chmod +x cosmosdb_access.sh
./cosmosdb_access.sh
```

The script assigns the Cosmos DB Data Contributor role to your user principal:

```bash
az cosmosdb sql role assignment create \
  --account-name YOUR_COSMOSDB_ACCOUNT_NAME \
  --resource-group YOUR_RESOURCE_GROUP_NAME \
  --scope "/" \
  --principal-id $(az ad signed-in-user show --query id -o tsv) \
  --role-definition-id "00000000-0000-0000-0000-000000000002"
```

### 4. Configure Local Settings

After deployment, copy the environment values from the Azure deployment:

1. Navigate to `.azure/[environment-name]/.env`
2. Copy the required values to your `local.settings.json`

Your `local.settings.json` should include:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOSDB_ENDPOINT": "https://yourcosmosdbaccount.documents.azure.com:443/",
    "COSMOSDB_DATABASE": "inventory",
    "COSMOSDB_CONTAINER_PRODUCTS": "products",
    "APPLICATIONINSIGHTS_CONNECTION_STRING": "",
    "OTEL_LOGS_EXPORTER": "none",
    "PYTHON_ENABLE_DEBUG_LOGGING": "1",
    "APPLICATIONINSIGHTS_ENABLE_DEPENDENCY_CORRELATION": "true"
  }
}
```

**Required Environment Variables:**

- `COSMOSDB_ENDPOINT` - Your Cosmos DB endpoint URL (copy from `.azure/[environment-name]/.env`)
- `COSMOSDB_DATABASE` - The name of your Cosmos DB database
- `COSMOSDB_CONTAINER_PRODUCTS` - The name of your Cosmos DB container for products
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Your Application Insights connection string (optional)
- `OTEL_LOGS_EXPORTER` - Set to `none` for local development
- `PYTHON_ENABLE_DEBUG_LOGGING` - Set to `1` for local debugging
- `APPLICATIONINSIGHTS_ENABLE_DEPENDENCY_CORRELATION` - Set to `true` for local debugging

### 5. Run Locally

Start the function app:

```bash
func start
```

Access the API documentation:
Navigate to [http://localhost:7071/docs?code=apikey](http://localhost:7071/docs?code=apikey)

Click on the Authorize button and enter the apikey as the value. Locally an actual API key is not required, but it is needed for the deployed version.

## Project Structure

```txt
├── .azure/                    # Azure deployment configuration
│   └── [environment-name]/
│       └── .env              # Environment variables (copy values from here)
├── cosmosdb_access.sh        # Script to configure Cosmos DB access
├── local.settings.json       # Local development settings
└── [function files]
```

## Accessing the deployed API

Once the application is deployed to Azure, you can access the API endpoints directly from the Azure portal or using tools like Postman or curl.

You can also access the swagger UI for the deployed function app at:

```txt
https://<your-function-app-name>.azurewebsites.net/api/docs?code=apikey
```

Replace `<your-function-app-name>` with the name of your Azure Function App.
Replace `apikey` with the actual API key if required, this is the function key generated during deployment. You can find it in the Azure portal under the "Functions" section of your Function App.

## Development Workflow

1. **First time setup**: Run `azd up` to deploy and generate environment configuration
2. **Azure CLI setup**: Login with `az login` using the same account used for deployment
3. **Cosmos DB access**: Update and run `cosmosdb_access.sh` to grant your user access
4. **Local development**: Copy values from `.azure/[environment-name]/.env` to `local.settings.json`
5. **Run locally**: Use `func start` for local development
6. **Deploy changes**: Use `azd up` to redeploy

## Troubleshooting

- **Cosmos DB Access Issues**: Ensure you're logged into Azure CLI with the correct account and have run the `cosmosdb_access.sh` script
- **Missing Environment Variables**: Check that you've copied all required values from `.azure/[environment-name]/.env` to `local.settings.json`

## API Documentation

When running locally, the interactive API documentation is available at the `/docs` endpoint with the API key parameter.
