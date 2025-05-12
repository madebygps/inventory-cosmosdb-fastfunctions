# Models

## Product

```json
{
  "id": "prod_123",
  "name": "Wireless Mouse",
  "description": "Ergonomic wireless mouse",
  "category": "electronics", # pk
  "price": 24.99
}
```

## Location

```json
{
  "id": "loc_nyc_001", # pk
  "name": "Manhattan Store",
  "address": "123 5th Ave, New York, NY",
  "manager": "Alex Rivera"
}
```

## InventoryItem

```json
{
  "id": "prod_123:loc_nyc_001", 
  "productId": "prod_123",
  "locationId": "loc_nyc_001", # pk
  "quantity": 42
}
```
