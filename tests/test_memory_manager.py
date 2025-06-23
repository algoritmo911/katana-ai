import pytest
import pytest_asyncio
import asyncio
import os
from unittest.mock import AsyncMock, patch

from katana_memory.memory_api import MemoryManager
from katana_memory.short_term.redis_cache import RedisCache

# Use a different Redis DB for testing, consistent with test_redis_cache
TEST_REDIS_URL = "redis://localhost:6379/1"

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def memory_manager_with_real_cache():
    """
    Provides a MemoryManager instance with a real RedisCache,
    pointing to the test Redis DB.
    This fixture ensures that the Redis connection is managed per test.
    """
    original_redis_url = os.environ.get("REDIS_URL")
    os.environ["REDIS_URL"] = TEST_REDIS_URL

    mm = MemoryManager()
    # Ensure connection for the underlying cache
    try:
        await mm.short_term_memory.redis_client.ping()
    except Exception as e:
        pytest.fail(f"Failed to connect to Redis at {TEST_REDIS_URL} for MemoryManager test: {e}")

    yield mm

    # Clean up keys used by this MemoryManager instance
    async for key in mm.short_term_memory.redis_client.scan_iter("chat:*"):
        await mm.short_term_memory.redis_client.delete(key)

    await mm.close_connections()

    if original_redis_url:
        os.environ["REDIS_URL"] = original_redis_url
    else:
        if "REDIS_URL" in os.environ: # Ensure key exists before deleting
            del os.environ["REDIS_URL"]


@pytest.mark.asyncio
async def test_remember_and_recall(memory_manager_with_real_cache: MemoryManager):
    mm = memory_manager_with_real_cache
    chat_id = 321
    text = "Remember this!"

    await mm.remember(chat_id, text)
    recalled_text = await mm.recall(chat_id)

    assert recalled_text == text

@pytest.mark.asyncio
async def test_recall_non_existent(memory_manager_with_real_cache: MemoryManager):
    mm = memory_manager_with_real_cache
    chat_id = 888 # Non-existent
    recalled_text = await mm.recall(chat_id)
    assert recalled_text is None

@pytest.mark.asyncio
async def test_forget(memory_manager_with_real_cache: MemoryManager):
    mm = memory_manager_with_real_cache
    chat_id = 654
    text = "This memory will be forgotten."

    await mm.remember(chat_id, text)
    await mm.forget(chat_id)
    recalled_text = await mm.recall(chat_id)

    assert recalled_text is None

@pytest.mark.asyncio
async def test_remember_with_ttl(memory_manager_with_real_cache: MemoryManager):
    mm = memory_manager_with_real_cache
    chat_id = 987
    text = "This memory has a short TTL"
    ttl_seconds = 1

    await mm.remember(chat_id, text, ttl_seconds=ttl_seconds)

    # Check immediately
    assert await mm.recall(chat_id) == text

    # Wait for TTL to expire
    await asyncio.sleep(ttl_seconds + 1)

    assert await mm.recall(chat_id) is None

# --- Mocked Tests for MemoryManager ---
# These tests verify that MemoryManager calls the correct RedisCache methods
# without needing a live Redis instance, by mocking RedisCache.

@pytest.fixture
def mock_redis_cache():
    # Create an AsyncMock instance that mimics RedisCache
    mock = AsyncMock(spec=RedisCache)
    mock.store = AsyncMock()
    mock.retrieve = AsyncMock()
    mock.delete = AsyncMock()
    mock.close = AsyncMock()
    mock.store = AsyncMock(return_value=None)
    mock.retrieve = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=None)
    mock.close = AsyncMock(return_value=None)

    # Mock the internal redis_client as well to prevent any real calls
    mock.redis_client = AsyncMock()
    mock.redis_client.setex = AsyncMock()
    mock.redis_client.get = AsyncMock()
    mock.redis_client.delete = AsyncMock()
    mock.redis_client.ping = AsyncMock()
    mock.redis_client.close = AsyncMock() # or aclose if that's what RedisCache calls
    return mock

@pytest_asyncio.fixture
async def memory_manager_with_mocked_cache(mock_redis_cache: RedisCache):
    # Create MemoryManager instance and then replace its cache with the mock
    mm = MemoryManager()
    # We need to prevent the real RedisCache in MemoryManager's __init__ from connecting.
    # This is tricky if MemoryManager() itself initializes a real RedisCache that connects.
    # The ideal way is to patch RedisCache at the class level *before* MemoryManager is instantiated.
    # Let's revert to the @patch method but ensure the patch target is absolutely correct.
    # The original patch target '@patch('katana_memory.memory_api.RedisCache')' should be correct.

    # Re-attempting the patch method, ensuring mock_redis_cache fixture is well-defined.
    with patch('katana_memory.memory_api.RedisCache', return_value=mock_redis_cache) as PatchedRedisCache:
        mm_instance = MemoryManager() # This should now use the mock_redis_cache
        yield mm_instance
    # No explicit close needed for the manager if its cache is mocked,
    # but if MemoryManager.close_connections() is called, mock_redis_cache.close() will be checked.


@pytest.mark.asyncio
async def test_remember_calls_cache_store(memory_manager_with_mocked_cache: MemoryManager):
    mm = memory_manager_with_mocked_cache # The fixture yields the instance directly
    mock_cache = mm.short_term_memory
    chat_id = 111
    text = "test remember"
    ttl = 1234

    await mm.remember(chat_id, text, ttl_seconds=ttl)

    mock_cache.store.assert_called_once_with(chat_id, text, ttl)

@pytest.mark.asyncio
async def test_recall_calls_cache_retrieve(memory_manager_with_mocked_cache: MemoryManager):
    mm = memory_manager_with_mocked_cache # The fixture yields the instance directly
    mock_cache = mm.short_term_memory
    chat_id = 222
    # Set return_value on the mock's method
    mock_cache.retrieve.return_value = "mocked text"

    result = await mm.recall(chat_id)

    mock_cache.retrieve.assert_called_once_with(chat_id)
    assert result == "mocked text"

@pytest.mark.asyncio
async def test_forget_calls_cache_delete(memory_manager_with_mocked_cache: MemoryManager):
    mm = memory_manager_with_mocked_cache # The fixture yields the instance directly
    mock_cache = mm.short_term_memory
    chat_id = 333

    await mm.forget(chat_id)

    mock_cache.delete.assert_called_once_with(chat_id)

@pytest.mark.asyncio
async def test_close_connections_calls_cache_close(memory_manager_with_mocked_cache: MemoryManager):
    mm = memory_manager_with_mocked_cache # The fixture yields the instance directly
    mock_cache = mm.short_term_memory

    await mm.close_connections()

    # mock_cache.close is the AsyncMock object representing the method
    mock_cache.close.assert_called_once()
