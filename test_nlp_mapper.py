import pytest
import os
from nlp_mapper import interpret, basic_interpret, llm_interpret, get_interpreter
from unittest.mock import patch

# Tests for the 'interpret' function (which is dynamically chosen by get_interpreter)
# These will test basic_interpret by default, unless USE_LLM_NLP is set in the environment.

def test_interpret_disk():
    assert interpret("проверь диск") == "df -h"
    assert interpret("сколько места на диске") == "df -h"
    assert interpret("покажи место") == "df -h"

def test_interpret_uptime():
    assert interpret("как долго работает система") == "uptime"
    assert interpret("аптайм сервера") == "uptime"
    assert interpret("работает?") == "uptime"

def test_interpret_cpu():
    assert interpret("какая загрузка") == "top -n1 | head -5"
    assert interpret("загрузка cpu") == "top -n1 | head -5"
    assert interpret("покажи загрузку процессора") == "top -n1 | head -5"

def test_interpret_ls():
    assert interpret("покажи файлы") == "ls -al"
    assert interpret("содержимое папки") == "ls -al"
    assert interpret("список файлов и папок") == "ls -al"

def test_interpret_none():
    assert interpret("неизвестная команда") is None
    assert interpret("что ты умеешь?") is None
    assert interpret("") is None # Empty string
    assert interpret("   ") is None # String with only spaces

def test_interpret_case_insensitivity():
    # This relies on the currently selected interpreter (basic_interpret by default)
    # to handle case insensitivity.
    assert interpret("Проверь Диск") == "df -h"
    assert interpret("КАКАЯ ЗАГРУЗКА") == "top -n1 | head -5"
    assert interpret("ПоКаЖи ФаЙлЫ") == "ls -al"

def test_interpret_partial_keywords():
    # Relies on the currently selected interpreter.
    assert interpret("эй, проверь диск пожалуйста") == "df -h"
    assert interpret("срочно, покажи мне загрузку cpu!") == "top -n1 | head -5"
    assert interpret("какой аптайм у этого сервера?") == "uptime"
    assert interpret("мне нужны все файлы в текущей папке") == "ls -al"

# --- Tests for specific interpreter functions and the selection logic ---

def test_basic_interpreter_direct():
    """Test basic_interpret directly."""
    assert basic_interpret("проверь диск") == "df -h"
    assert basic_interpret("неизвестная команда") is None

def test_llm_interpreter_direct():
    """Test llm_interpret directly (placeholder behavior)."""
    assert llm_interpret("some input") is None
    assert llm_interpret("example llm command for uptime") == "uptime" # Test the dummy command

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
    if os.environ.get('USE_LLM_NLP','false').lower() != 'true':
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
    env_val = os.environ.get('USE_LLM_NLP', 'false').lower()
    if env_val == 'true':
        assert interpret == llm_interpret
        print ("Module `interpret` is `llm_interpret` because USE_LLM_NLP is true.")
    else:
        assert interpret == basic_interpret
        print ("Module `interpret` is `basic_interpret` because USE_LLM_NLP is false or unset.")

# It might be useful to test combinations if logic becomes more complex,
# but for the current simple keyword checking, it's not strictly necessary.
# For example, if "диск" and "файлы" in the same query should prioritize one.
# For now, the first match wins.
# def test_interpret_multiple_keywords():
#     # Assuming 'диск' check comes before 'файлы' in interpret()
#     assert interpret("покажи файлы на диске") == "df -h" # or "ls -al" depending on order
#     pass

# --- Tests for /run syntax in basic_interpret ---
def test_basic_interpret_run_uptime():
    assert basic_interpret("/run uptime") == "uptime"
    assert basic_interpret("/run UPTIME") == "uptime" # Known command, so output is normalized
    assert basic_interpret("/RUN uptime") == "uptime" # /RUN prefix should also work

def test_basic_interpret_run_df():
    assert basic_interpret("/run df -h") == "df -h"
    assert basic_interpret("/run DF -H") == "df -h" # Known command

def test_basic_interpret_run_ls():
    assert basic_interpret("/run ls -al") == "ls -al"

def test_basic_interpret_run_passthrough_arbitrary_command():
    assert basic_interpret("/run echo hello world") == "echo hello world"
    assert basic_interpret("/run MyScript.sh --arg value") == "MyScript.sh --arg value"
    assert basic_interpret("/run /usr/bin/custom_tool --version") == "/usr/bin/custom_tool --version"

def test_basic_interpret_run_with_extra_spaces():
    assert basic_interpret("/run   uptime  ") == "uptime"
    assert basic_interpret("/run   echo hello  ") == "echo hello"

def test_basic_interpret_run_empty_command():
    assert basic_interpret("/run ") is None
    assert basic_interpret("/run    ") is None

def test_basic_interpret_run_no_passthrough_if_only_keyword_for_other_rule():
    # E.g. "/run диск" should not map to "df -h" via the /run rule,
    # but it also shouldn't map via the "диск" rule because /run implies direct command.
    # The current implementation will pass "диск" as the command.
    assert basic_interpret("/run диск") == "диск"
    # This is different from just "диск", which would be "df -h".

if __name__ == "__main__":
    pytest.main()
