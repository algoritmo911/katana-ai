import os

# This code will run when pytest loads conftest.py, which is very early.
# This should ensure environment variables are set before most test module imports.
print("Setting mock environment variables in conftest.py...")
os.environ["KATANA_TELEGRAM_TOKEN"] = "123456:ABCDEF_mock_token_conftest"
os.environ["OPENAI_API_KEY"] = "fake_openai_key_conftest"
os.environ["ANTHROPIC_API_KEY"] = "fake_anthropic_key_conftest"
os.environ["HUGGINGFACE_API_TOKEN"] = "fake_hf_token_conftest"
print(f"KATANA_TELEGRAM_TOKEN set to: {os.getenv('KATANA_TELEGRAM_TOKEN')}")

# No fixture needed if we just want to set env vars globally at import time of conftest.
# If finer control or setup/teardown is needed, fixtures are better.
# For this specific problem (module-level check in katana_bot.py during import),
# setting it directly like this is more likely to be effective immediately.
