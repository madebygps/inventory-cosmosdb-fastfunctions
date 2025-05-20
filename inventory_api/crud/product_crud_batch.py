import asyncio
from collections import defaultdict
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosBatchOperationError
from azure.cosmos.aio import ContainerProxy
import uuid
from typing import Any, Dict, List, Tuple
from datetime import datetime
import logging

from inventory_api.models.product import (
    ProductBatchCreate,
    ProductCreate,
    ProductResponse,
    ProductBatchUpdate,
    ProductBatchDelete,
    ProductStatus
)


logger = logging.getLogger(__name__)

async def create_products(
    container: ContainerProxy,
    batch_create: ProductBatchCreate,
) -> List[ProductResponse]:
    """
    Create multiple products in a batch operation with concurrent processing across categories.
    
    Args:
        container: Cosmos DB container client
        batch_create: Batch create request containing items to create
        
    Returns:
        List of successfully created products
    """
    if not batch_create.items:
        return []

    products_by_category: Dict[str, List[ProductCreate]] = defaultdict(list)
    for product_model in batch_create.items:
        products_by_category[product_model.category].append(product_model)

    async def process_category_creates(category_pk, product_list_for_category):
        if not product_list_for_category:
            return []
            
        successfully_created_products = []
        batch_operations_for_db: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []
        raw_product_data_in_batch = []

        for product_to_create in product_list_for_category:
            data = product_to_create.model_dump()
            data["id"] = str(uuid.uuid4())
            data["status"] = ProductStatus.ACTIVE.value
            data["last_updated"] = datetime.utcnow().isoformat()
            
            raw_product_data_in_batch.append(data)
            batch_operations_for_db.append(("create", (data,), {}))

        if not batch_operations_for_db:
            return []

        try:
            batch_results = await container.execute_item_batch(
                batch_operations=batch_operations_for_db, partition_key=category_pk
            )
            for result_item in batch_results:
                if isinstance(result_item, dict) and result_item.get("id"):
                    successfully_created_products.append(
                        ProductResponse.model_validate(result_item)
                    )
                else:
                    logger.warning(
                        f"Unexpected item in successful batch create result for category '{category_pk}': {result_item}"
                    )
        except CosmosBatchOperationError as e:
            logger.error(
                f"Cosmos DB Batch Create Error for category '{category_pk}': "
                f"First failed op index: {e.error_index}. Msg: {str(e)}",
                exc_info=True,
            )
            for i, op_response in enumerate(e.operation_responses):
                if i < len(raw_product_data_in_batch):
                    attempted_item_id = raw_product_data_in_batch[i].get(
                        "id", "unknown_id"
                    )
                    if op_response.get("statusCode", 200) >= 400:
                        logger.error(
                            f"  Failed create op in batch for item ID '{attempted_item_id}': {op_response}"
                        )
        except CosmosHttpResponseError as e_http:
            logger.error(
                f"Cosmos DB HTTP error during batch create for category '{category_pk}': {e_http}",
                exc_info=True,
            )
        except Exception as e_generic:
            logger.error(
                f"Unexpected error during batch create for category '{category_pk}': {e_generic}",
                exc_info=True,
            )
        return successfully_created_products

    tasks = [
        asyncio.create_task(process_category_creates(category, items))
        for category, items in products_by_category.items()
    ]
    
    results = await asyncio.gather(*tasks)
    
    all_successfully_created_products = [
        product for category_results in results for product in category_results
    ]
    
    return all_successfully_created_products


async def update_products(
    container: ContainerProxy,
    batch_update: ProductBatchUpdate,
) -> List[ProductResponse]:
    """
    Update multiple products in a batch operation with concurrent processing across categories.
    
    Args:
        container: Cosmos DB container client
        batch_update: Batch update request containing items to update
        
    Returns:
        List of successfully updated products
    """
    if not batch_update.items:
        return []

    updates_by_category: Dict[str, List] = defaultdict(list)
    for update_item in batch_update.items:
        updates_by_category[update_item.category].append(update_item)
    
    async def process_category_updates(category_pk, update_items_for_category):
        if not update_items_for_category:
            return []
            
        successfully_updated_products = []
        batch_operations_for_db = []
        ids_in_current_batch_for_logging = []

        for update_item in update_items_for_category:
            update_dict = update_item.changes.model_dump(exclude_unset=True)
            
            update_dict["last_updated"] = datetime.utcnow().isoformat()
            
            json_patch_operations = []
            for key, value in update_dict.items():
                if key not in ["id", "category", "_etag"]:
                    json_patch_operations.append(
                        {"op": "set", "path": f"/{key}", "value": value}
                    )

            if not json_patch_operations:
                logger.warning(
                    f"No valid patch operations for product ID '{update_item.id}' in category '{category_pk}'. Skipping."
                )
                continue

            ids_in_current_batch_for_logging.append(update_item.id)
            batch_operations_for_db.append(
                (
                    "patch",
                    (update_item.id, json_patch_operations),
                    {"if_match_etag": update_item.etag},
                )
            )

        if not batch_operations_for_db:
            return []

        try:
            batch_results = await container.execute_item_batch(
                batch_operations=batch_operations_for_db, partition_key=category_pk
            )
            for result_item in batch_results:
                if isinstance(result_item, dict) and result_item.get("id"):
                    successfully_updated_products.append(
                        ProductResponse.model_validate(result_item)
                    )
                else:
                    logger.warning(
                        f"Unexpected item in successful batch update result for category '{category_pk}': {result_item}"
                    )
        except CosmosBatchOperationError as e:
            logger.error(
                f"Cosmos DB Batch Update Error for category '{category_pk}': "
                f"First failed op index: {e.error_index}. Msg: {str(e)}",
                exc_info=True,
            )
            for i, op_response in enumerate(e.operation_responses):
                if i < len(ids_in_current_batch_for_logging):
                    attempted_item_id = ids_in_current_batch_for_logging[i]
                    if op_response.get("statusCode", 200) >= 400:
                        logger.error(
                            f"  Failed patch op in batch for item ID '{attempted_item_id}': {op_response}"
                        )
        except CosmosHttpResponseError as e_http:
            logger.error(
                f"Cosmos DB HTTP error during batch update for category '{category_pk}': {e_http}",
                exc_info=True,
            )
        except Exception as e_generic:
            logger.error(
                f"Unexpected error during batch update for category '{category_pk}': {e_generic}",
                exc_info=True,
            )
        
        return successfully_updated_products

    tasks = [
        asyncio.create_task(process_category_updates(category, items))
        for category, items in updates_by_category.items()
    ]
    
    results = await asyncio.gather(*tasks)
    
    all_successfully_updated_products = [
        product for category_results in results for product in category_results
    ]
    
    return all_successfully_updated_products


async def delete_products(
    container: ContainerProxy,
    batch_delete: ProductBatchDelete,
) -> List[str]:
    """
    Delete multiple products in a batch operation with concurrent processing across categories.
    
    Args:
        container: Cosmos DB container client
        batch_delete: Batch delete request containing items to delete
        
    Returns:
        List of successfully deleted product IDs
    """
    if not batch_delete.items:
        return []

    deletes_by_category: Dict[str, List[str]] = defaultdict(list) 
    for delete_item in batch_delete.items:
        deletes_by_category[delete_item.category].append(delete_item.id)

    async def process_category_deletes(category_pk, product_ids_in_category):
        if not product_ids_in_category:
            return []
            
        successfully_deleted_ids = []
        batch_operations_for_db: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []
        
        for product_id in product_ids_in_category:
            batch_operations_for_db.append(("delete", (product_id,), {}))

        if not batch_operations_for_db:
            return []

        try:
            await container.execute_item_batch(
                batch_operations=batch_operations_for_db, partition_key=category_pk
            )
            successfully_deleted_ids.extend(product_ids_in_category)

        except CosmosBatchOperationError as e:
            logger.error(
                f"Cosmos DB Batch Delete Error for category '{category_pk}': "
                f"First failed op index: {e.error_index}. Msg: {str(e)}",
                exc_info=True,
            )
            for i, op_response in enumerate(e.operation_responses):
                if i < len(product_ids_in_category):
                    attempted_item_id = product_ids_in_category[i]
                    if op_response.get("statusCode", 200) >= 400:
                        logger.error(
                            f"  Failed delete op in batch for item ID '{attempted_item_id}': {op_response}"
                        )
        except CosmosHttpResponseError as e_http:
            logger.error(
                f"Cosmos DB HTTP error during batch delete for category '{category_pk}': {e_http}",
                exc_info=True,
            )
        except Exception as e_generic:
            logger.error(
                f"Unexpected error during batch delete for category '{category_pk}': {e_generic}",
                exc_info=True,
            )
        return successfully_deleted_ids

    tasks = [
        asyncio.create_task(process_category_deletes(category, ids))
        for category, ids in deletes_by_category.items()
    ]
    
    results = await asyncio.gather(*tasks)
    
    all_successfully_deleted_ids = [
        id for category_results in results for id in category_results
    ]
    
    return all_successfully_deleted_ids
