The `pos_api_items` endpoint fetches all active items from the `inventoy_items` and `inventory_price_recod` tables, formats them into a JSON string, and returns it. This API is queried frequently by POS terminals, and since the item catalog can be large, this operation can cause significant CPU and DB load.

My plan is to introduce an in-memory caching mechanism specifically for this endpoint, using a dictionary to store the serialized JSON response with a Time-To-Live (TTL) of 5 minutes (or another suitable duration).

The caching logic should consider the current active tenant database because this application is multi-tenant (`get_session_db_name()`). We will cache the item list per database name.

If a new item is added or a price is updated, we could ideally clear the cache, but a simple TTL cache (e.g. 5 minutes) is usually perfectly acceptable for a POS system syncing an entire catalog, or we can expose a cache clearing function. I will add a cache clear call in functions that modify `inventoy_items` or `inventory_price_recod` (like `add_inventory_item`, `add_new_price_tier`, `inventory_price_editing`, `update_inventory_prices`) to ensure the cache stays fresh immediately when prices/items change, avoiding stale data entirely.

Plan:
1.  **Define global cache variables**:
    Add `_pos_items_cache = {}` near the other caches at the top of `app.py`.
2.  **Define cache clearing helper**:
    Add `def clear_pos_items_cache(): global _pos_items_cache; _pos_items_cache.pop(get_session_db_name(), None)`
3.  **Implement caching in `pos_api_items`**:
    *   Get `db_name = get_session_db_name()`.
    *   Check if `db_name` is in `_pos_items_cache` and if the cache is valid (not expired based on a TTL like 1 hour or 5 mins).
    *   If cache hit, return the cached JSON string.
    *   If cache miss, execute the query, build the list, dump to JSON, and store it in the cache with the current timestamp.
4.  **Invalidate cache on updates**:
    Call `clear_pos_items_cache()` in:
    *   `add_inventory_item` (when a new item is added)
    *   `add_new_price_tier` (when a new price is added)
    *   `inventory_price_editing` / `update_inventory_prices` (when prices are updated in bulk)
5.  **Run Tests**:
    Run `python tests/run_tests.py` to ensure no functionality is broken.
6.  **Pre-commit**: Complete pre commit steps to ensure proper testing, verification, review, and reflection are done.
