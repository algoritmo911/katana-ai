import pytest
from unittest.mock import patch, MagicMock

from katana.self_heal import health_check

@pytest.fixture
def mock_dependencies():
    """Fixture to mock all external dependencies of the health_check module."""
    with patch('katana.self_heal.health_check.time.sleep', return_value=None) as mock_sleep, \
         patch('katana.self_heal.health_check.check_openai', return_value=True) as mock_openai, \
         patch('katana.self_heal.health_check.check_supabase', return_value=True) as mock_supabase, \
         patch('katana.self_heal.health_check.check_n8n', return_value=True) as mock_n8n:
        yield {
            "sleep": mock_sleep,
            "openai": mock_openai,
            "supabase": mock_supabase,
            "n8n": mock_n8n
        }

def test_run_health_check_all_systems_go(capsys, mock_dependencies):
    """
    Test that run_health_check reports success when all services are operational.
    """
    health_check.run_health_check()
    captured = capsys.readouterr()

    assert "✅ All systems are nominal." in captured.out
    assert "🚨" not in captured.out
    mock_dependencies['openai'].assert_called_once()
    mock_dependencies['supabase'].assert_called_once()
    mock_dependencies['n8n'].assert_called_once()

def test_run_health_check_one_service_fails(capsys, mock_dependencies):
    """
    Test that run_health_check reports failure when one service is down.
    """
    mock_dependencies['supabase'].return_value = False

    health_check.run_health_check()
    captured = capsys.readouterr()

    assert "🚨 One or more systems are experiencing issues." in captured.out
    assert "💔 Health check failed for: Supabase" in captured.out
    assert "✅ All systems are nominal." not in captured.out

def test_run_health_check_all_services_fail(capsys, mock_dependencies):
    """
    Test that run_health_check reports failure when all services are down.
    """
    mock_dependencies['openai'].return_value = False
    mock_dependencies['supabase'].return_value = False
    mock_dependencies['n8n'].return_value = False

    health_check.run_health_check()
    captured = capsys.readouterr()

    assert "🚨 One or more systems are experiencing issues." in captured.out
    assert "💔 Health check failed for: OpenAI" in captured.out
    assert "💔 Health check failed for: Supabase" in captured.out
    assert "💔 Health check failed for: n8n" in captured.out

@patch('katana.self_heal.health_check.time.sleep', return_value=None)
def test_retry_logic_succeeds_on_last_try(mock_sleep, capsys):
    """
    Test the _check_service_with_retry function to ensure it retries and eventually succeeds.
    """
    service_name = "TestService"
    # Mock a check function that fails twice then succeeds.
    check_func = MagicMock(side_effect=[False, False, True])

    result = health_check._check_service_with_retry(check_func, service_name)
    captured = capsys.readouterr()

    assert result is True
    assert check_func.call_count == 3
    # Called with 1s and 2s delays
    assert mock_sleep.call_count == 2
    assert f"✅ {service_name} is operational." in captured.out
    assert "Retrying in 1s" in captured.out
    assert "Retrying in 2s" in captured.out

@patch('katana.self_heal.health_check.time.sleep', return_value=None)
def test_retry_logic_fails_after_max_retries(mock_sleep, capsys):
    """
    Test the _check_service_with_retry function to ensure it fails after all retries.
    """
    service_name = "FailingService"
    check_func = MagicMock(return_value=False)

    result = health_check._check_service_with_retry(check_func, service_name)
    captured = capsys.readouterr()

    assert result is False
    assert check_func.call_count == health_check.MAX_RETRIES
    assert mock_sleep.call_count == health_check.MAX_RETRIES - 1
    assert f"🚨 CRITICAL: {service_name} is unreachable after {health_check.MAX_RETRIES} attempts." in captured.out
