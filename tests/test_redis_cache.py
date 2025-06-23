import pytest
import pytest_asyncio
import asyncio
import os
from katana_memory.short_term.redis_cache import RedisCache

# Use a different Redis DB for testing
TEST_REDIS_URL = "redis://localhost:6379/1"

@pytest.fixture(scope="module")
def event_loop():
    """Overrides pytest-asyncio default event_loop fixture to module scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="module")
async def redis_cache_module():
    """
    Module-scoped RedisCache fixture.
    Ensures Redis connection is opened and closed once per test module.
    """
    original_redis_url = os.environ.get("REDIS_URL")
    os.environ["REDIS_URL"] = TEST_REDIS_URL

    cache = RedisCache()
    # Ensure the client is connected (though from_url usually does this)
    # Forcing a ping to confirm connection early.
    try:
        await cache.redis_client.ping()
    except Exception as e:
        pytest.fail(f"Failed to connect to Redis at {TEST_REDIS_URL}: {e}. Ensure Redis server is running.")

    yield cache

    # Clean up keys used during tests
    async for key in cache.redis_client.scan_iter("chat:*"):
        await cache.redis_client.delete(key)

    await cache.close()

    if original_redis_url:
        os.environ["REDIS_URL"] = original_redis_url
    else:
        del os.environ["REDIS_URL"]


@pytest.mark.asyncio
async def test_store_and_retrieve(redis_cache_module: RedisCache):
    cache = redis_cache_module
    chat_id = 123
    text = "Hello, Redis!"
    await cache.store(chat_id, text)
    retrieved_text = await cache.retrieve(chat_id)
    assert retrieved_text == text

@pytest.mark.asyncio
async def test_retrieve_non_existent(redis_cache_module: RedisCache):
    cache = redis_cache_module
    chat_id = 999 # Non-existent
    retrieved_text = await cache.retrieve(chat_id)
    assert retrieved_text is None

@pytest.mark.asyncio
async def test_delete(redis_cache_module: RedisCache):
    cache = redis_cache_module
    chat_id = 456
    text = "Data to be deleted"
    await cache.store(chat_id, text)
    await cache.delete(chat_id)
    retrieved_text = await cache.retrieve(chat_id)
    assert retrieved_text is None

@pytest.mark.asyncio
async def test_ttl_expiration(redis_cache_module: RedisCache):
    cache = redis_cache_module
    chat_id = 789
    text = "This will expire soon"
    ttl_seconds = 1 # Expire after 1 second

    await cache.store(chat_id, text, ttl_seconds)

    # Check immediately that it's there
    retrieved_immediately = await cache.retrieve(chat_id)
    assert retrieved_immediately == text

    # Wait for longer than TTL
    await asyncio.sleep(ttl_seconds + 1)

    retrieved_after_ttl = await cache.retrieve(chat_id)
    assert retrieved_after_ttl is None

@pytest.mark.asyncio
async def test_store_overwrite(redis_cache_module: RedisCache):
    cache = redis_cache_module
    chat_id = 101
    text1 = "Initial text"
    text2 = "Overwritten text"

    await cache.store(chat_id, text1)
    retrieved_text1 = await cache.retrieve(chat_id)
    assert retrieved_text1 == text1

    await cache.store(chat_id, text2) # Overwrite with new text
    retrieved_text2 = await cache.retrieve(chat_id)
    assert retrieved_text2 == text2

@pytest.mark.asyncio
async def test_different_chat_ids(redis_cache_module: RedisCache):
    cache = redis_cache_module
    chat_id1 = 201
    text1 = "Text for chat 1"
    chat_id2 = 202
    text2 = "Text for chat 2"

    await cache.store(chat_id1, text1)
    await cache.store(chat_id2, text2)

    retrieved1 = await cache.retrieve(chat_id1)
    retrieved2 = await cache.retrieve(chat_id2)

    assert retrieved1 == text1
    assert retrieved2 == text2
    assert retrieved1 != retrieved2
