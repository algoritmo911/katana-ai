import pytest
import os
from nlp_mapper import interpret, basic_interpret, llm_interpret, get_interpreter
from unittest.mock import patch

# Tests for the 'interpret' function (which is dynamically chosen by get_interpreter)
# These will test basic_interpret by default, unless USE_LLM_NLP is set in the environment.

import json


def test_interpret_disk():
    assert json.loads(interpret("проверь диск")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "df -h"},
        "id": "nlp-disk",
    }
    assert json.loads(interpret("сколько места на диске")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "df -h"},
        "id": "nlp-disk",
    }
    assert json.loads(interpret("покажи место")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "df -h"},
        "id": "nlp-disk",
    }


def test_interpret_uptime():
    assert json.loads(interpret("как долго работает система")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "uptime"},
        "id": "nlp-uptime",
    }
    assert json.loads(interpret("аптайм сервера")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "uptime"},
        "id": "nlp-uptime",
    }
    assert json.loads(interpret("работает?")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "uptime"},
        "id": "nlp-uptime",
    }


def test_interpret_cpu():
    assert json.loads(interpret("какая загрузка")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "top -n1 | head -5"},
        "id": "nlp-cpu",
    }
    assert json.loads(interpret("загрузка cpu")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "top -n1 | head -5"},
        "id": "nlp-cpu",
    }
    assert json.loads(interpret("покажи загрузку процессора")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "top -n1 | head -5"},
        "id": "nlp-cpu",
    }


def test_interpret_ls():
    assert json.loads(interpret("покажи файлы")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ls -al"},
        "id": "nlp-ls",
    }
    assert json.loads(interpret("содержимое папки")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ls -al"},
        "id": "nlp-ls",
    }
    assert json.loads(interpret("список файлов и папок")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ls -al"},
        "id": "nlp-ls",
    }


def test_interpret_none():
    assert interpret("неизвестная команда") is None
    assert interpret("что ты умеешь?") is None
    assert interpret("") is None  # Empty string
    assert interpret("   ") is None  # String with only spaces


def test_interpret_case_insensitivity():
    # This relies on the currently selected interpreter (basic_interpret by default)
    # to handle case insensitivity.
    assert json.loads(interpret("Проверь Диск")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "df -h"},
        "id": "nlp-disk",
    }
    assert json.loads(interpret("КАКАЯ ЗАГРУЗКА")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "top -n1 | head -5"},
        "id": "nlp-cpu",
    }
    assert json.loads(interpret("ПоКаЖи ФаЙлЫ")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ls -al"},
        "id": "nlp-ls",
    }


def test_interpret_partial_keywords():
    # Relies on the currently selected interpreter.
    assert json.loads(interpret("эй, проверь диск пожалуйста")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "df -h"},
        "id": "nlp-disk",
    }
    assert json.loads(interpret("срочно, покажи мне загрузку cpu!")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "top -n1 | head -5"},
        "id": "nlp-cpu",
    }
    assert json.loads(interpret("какой аптайм у этого сервера?")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "uptime"},
        "id": "nlp-uptime",
    }
    assert json.loads(interpret("мне нужны все файлы в текущей папке")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ls -al"},
        "id": "nlp-ls",
    }


def test_interpret_memory():
    assert json.loads(interpret("сколько памяти используется")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "free -h"},
        "id": "nlp-ram",
    }
    assert json.loads(interpret("покажи ram")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "free -h"},
        "id": "nlp-ram",
    }
    assert json.loads(interpret("использование оперативки")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "free -h"},
        "id": "nlp-ram",
    }


def test_interpret_system_info():
    assert json.loads(interpret("дай инфо о системе")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "uname -a"},
        "id": "nlp-sysinfo",
    }
    assert json.loads(interpret("какое ядро?")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "uname -a"},
        "id": "nlp-sysinfo",
    }
    assert json.loads(interpret("версия ос какая")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "uname -a"},
        "id": "nlp-sysinfo",
    }
    assert json.loads(interpret("система инфо покажи")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "uname -a"},
        "id": "nlp-sysinfo",
    }


def test_interpret_network_connections():
    assert json.loads(interpret("активные сетевые подключения")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ss -tulnp"},
        "id": "nlp-net",
    }
    assert json.loads(interpret("открытые порты")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ss -tulnp"},
        "id": "nlp-net",
    }
    assert json.loads(interpret("покажи соединения")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ss -tulnp"},
        "id": "nlp-net",
    }


def test_interpret_ping_google():
    assert json.loads(interpret("пинг google сейчас")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ping -c 3 google.com"},
        "id": "nlp-ping",
    }
    assert json.loads(interpret("проверь связь с google")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "ping -c 3 google.com"},
        "id": "nlp-ping",
    }


# --- Tests for specific interpreter functions and the selection logic ---


def test_basic_interpreter_direct():
    """Test basic_interpret directly."""
    assert json.loads(basic_interpret("проверь диск")) == {
        "type": "exec",
        "module": "system",
        "args": {"command": "df -h"},
        "id": "nlp-disk",
    }
    assert basic_interpret("неизвестная команда") is None


def test_llm_interpreter_direct():
    """Test llm_interpret directly (placeholder behavior)."""
    assert llm_interpret("some input") is None
    assert (
        llm_interpret("example llm command for uptime") == "uptime"
    )  # Test the dummy command


@patch.dict(os.environ, {"USE_LLM_NLP": "false"})
def test_get_interpreter_selects_basic_when_env_false(monkeypatch):
    # Must reload nlp_mapper to re-evaluate USE_LLM_NLP at import time
    # This is a bit tricky; for simplicity, we'll test the instance returned by get_interpreter()
    # rather than trying to force a reload of the module for `nlp_mapper.interpret`.
    # The `interpret` at the module level is set once at import.
    # A better way might be to make `interpret` a function that calls `get_interpreter().interpret_text(text)`
    # or nlp_mapper.interpret itself calls get_interpreter() on each call.
    # For now, we test the factory function.
    interpreter_func = get_interpreter()
    assert interpreter_func == basic_interpret
    # Test that the module's default `interpret` is basic_interpret if USE_LLM_NLP was false during initial import
    # This assumes tests are run in an environment where USE_LLM_NLP is not 'true' by default
    if os.environ.get("USE_LLM_NLP", "false").lower() != "true":
        assert interpret == basic_interpret


@patch.dict(os.environ, {"USE_LLM_NLP": "true"})
def test_get_interpreter_selects_llm_when_env_true(monkeypatch):
    # As above, get_interpreter() will reflect the patched env var.
    # The module-level `interpret` variable in nlp_mapper itself won't change post-import
    # without a reload.
    interpreter_func = get_interpreter()
    assert interpreter_func == llm_interpret


# Test that the module's `interpret` is set according to USE_LLM_NLP at import time
# This test is sensitive to the environment when tests are run.
def test_module_interpret_respects_initial_env():
    env_val = os.environ.get("USE_LLM_NLP", "false").lower()
    if env_val == "true":
        assert interpret == llm_interpret
        print("Module `interpret` is `llm_interpret` because USE_LLM_NLP is true.")
    else:
        assert interpret == basic_interpret
        print(
            "Module `interpret` is `basic_interpret` because USE_LLM_NLP is false or unset."
        )


# It might be useful to test combinations if logic becomes more complex,
# but for the current simple keyword checking, it's not strictly necessary.
# For example, if "диск" and "файлы" in the same query should prioritize one.
# For now, the first match wins.
# def test_interpret_multiple_keywords():
#     # Assuming 'диск' check comes before 'файлы' in interpret()
#     assert interpret("покажи файлы на диске") == "df -h" # or "ls -al" depending on order
#     pass

if __name__ == "__main__":
    pytest.main()
