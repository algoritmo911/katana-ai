import functools
import time
import getpass
import uuid # For trace_id
from datetime import datetime, timezone
from katana.logging.telemetry_logger import log_command_telemetry

# Attempt to import telebot types for type checking, but don't make it a hard dependency
try:
    from telebot import types as telebot_types
except ImportError:
    telebot_types = None

def trace_command(_func=None, *, tags: dict = None):
    """
    A decorator to log command execution telemetry.
    Can be used as @trace_command or @trace_command(tags=...).
    """
    def decorator_trace_command(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace_id = str(uuid.uuid4())
            command_name = func.__name__
            is_method = False
            user_info = None
            actual_args = args

            # Determine command name and if it's a method
            if hasattr(func, '__qualname__') and '.' in func.__qualname__:
                command_name = func.__qualname__
                is_method = True

            # User information extraction and 'self'/'cls' argument removal
            if args:
                first_arg = args[0]
                # Check for telebot.types.Message (if telebot is available)
                if telebot_types and isinstance(first_arg, telebot_types.Message):
                    user_info = {
                        "id": first_arg.from_user.id,
                        "username": first_arg.from_user.username,
                        "source": "telegram"
                    }
                    # For bot commands, the first arg is 'message', not 'self'
                    # So, actual_args should include it for logging, unless it's also a method
                    # If it's a method AND a bot command, this logic might need refinement,
                    # but typically bot handlers are functions or methods where 'self' is distinct.
                    if is_method: # If it's a method of a class, and also a bot handler
                        # This case means first_arg is 'self', and message might be second.
                        # This needs careful checking of typical bot patterns.
                        # For now, assume if first_arg is Message, it's the primary context.
                        # If a method's first arg is 'self', and it *also* receives a 'message',
                        # the user_info would be from 'message', and 'self' would be skipped.
                        # Let's assume typical bot handlers:
                        # - func(message, ...)
                        # - Class.method(self, message, ...)
                        # The current logic handles func(message) and Class.method(self, regular_arg)
                        # Need to check Class.method(self, message, ...)
                        pass # Handled by user_info extraction
                    # actual_args remains args because 'message' is a relevant input

                elif is_method: # Standard method, first arg is 'self' or 'cls'
                    actual_args = args[1:]
                    # Fallback to getpass if no Telegram message object found
                    user_info = {"username": getpass.getuser(), "source": "system"}

                else: # Regular function, not a method, no Message object
                    user_info = {"username": getpass.getuser(), "source": "system"}
            else: # No args
                user_info = {"username": getpass.getuser(), "source": "system"}


            start_perf_counter = time.perf_counter()
            start_timestamp_iso = datetime.now(timezone.utc).isoformat()
            success = False
            result_val = None
            error_obj = None

            try:
                result_val = func(*args, **kwargs)
                success = True
                return result_val
            except Exception as e:
                error_obj = e
                raise
            finally:
                end_perf_counter = time.perf_counter()
                execution_time = end_perf_counter - start_perf_counter

                # If user_info wasn't determined from args (e.g. method with no args beyond self)
                if user_info is None:
                     user_info = {"username": getpass.getuser(), "source": "system_fallback"}


                log_command_telemetry(
                    trace_id=trace_id,
                    command_name=command_name,
                    args=actual_args,
                    kwargs=kwargs,
                    success=success,
                    result=result_val,
                    error=error_obj,
                    execution_time=execution_time,
                    user=user_info,
                    start_time_iso=start_timestamp_iso,
                    tags=tags
                )
        return wrapper

    if _func is None:
        return decorator_trace_command # Called as @trace_command(tags=...)
    else:
        return decorator_trace_command(_func) # Called as @trace_command


if __name__ == '__main__':
    # Example Usage
    print("Testing trace_command decorator...\n")

    # --- Mocking telebot.types.Message for testing ---
    class MockUser:
        def __init__(self, id, username):
            self.id = id
            self.username = username

    class MockMessage:
        def __init__(self, user_id, username, text="Default text"):
            self.from_user = MockUser(user_id, username)
            self.text = text
            # Add other attributes if your decorated functions expect them

    # Simulate telebot_types.Message being available for this test
    if telebot_types is None: # If actual telebot is not installed
        class MockTelebotTypes:
            Message = MockMessage
        telebot_types = MockTelebotTypes
    # --- End Mocking ---

    @trace_command
    def sample_successful_command(a, b, greet="hello"):
        print(f"Executing sample_successful_command with {a}, {b}, {greet}")
        return f"{greet} {a + b}"

    @trace_command(tags={"category": "math", "complexity": "low"})
    def sample_failing_command_with_tags(x):
        print(f"Executing sample_failing_command_with_tags with {x}")
        if x == 0:
            raise ValueError("Division by zero simulated with tags")
        return 10 / x

    @trace_command
    def bot_command_handler(message: telebot_types.Message, additional_param: str):
        print(f"Executing bot_command_handler for user {message.from_user.id} with text: '{message.text}', and param: '{additional_param}'")
        if message.text == "failme":
            raise RuntimeError("Bot command failed as requested")
        return f"Processed for {message.from_user.username}: {additional_param}"

    class TestCLI:
        def __init__(self, name):
            self.name = name

        @trace_command(tags={"cli_tool": "TestCLI"})
        def instance_method_command(self, value, option=None):
            print(f"Executing instance_method_command on {self.name} with {value}, {option}")
            if option == "fail":
                raise RuntimeError("Simulated failure in instance method with tags")
            return f"Instance {self.name} processed {value}"

    # Test 1: Successful simple command
    print("--- Test 1: Successful simple command ---")
    res_success = sample_successful_command(5, 10, greet="Result:")
    print(f"Result: {res_success}\n")

    # Test 2: Failing command with tags
    print("--- Test 2: Failing command with tags ---")
    try:
        sample_failing_command_with_tags(0)
    except ValueError as e:
        print(f"Caught expected error: {e}\n")

    # Test 3: Successful run of the failing command
    print("--- Test 3: Successful run of failing command ---")
    res_success_2 = sample_failing_command_with_tags(2)
    print(f"Result: {res_success_2}\n")

    # Test 4: Bot command handler - success
    print("--- Test 4: Bot command handler (success) ---")
    mock_msg_success = MockMessage(user_id=12345, username="testuser", text="Hello bot")
    res_bot_success = bot_command_handler(mock_msg_success, "param1")
    print(f"Result: {res_bot_success}\n")

    # Test 5: Bot command handler - failure
    print("--- Test 5: Bot command handler (failure) ---")
    mock_msg_fail = MockMessage(user_id=67890, username="anotheruser", text="failme")
    try:
        bot_command_handler(mock_msg_fail, "param_fail")
    except RuntimeError as e:
        print(f"Caught expected error: {e}\n")

    # Test 6: Instance method command (CLI-like) - success
    print("--- Test 6: Instance method command (success) ---")
    cli_instance = TestCLI("MyCLI")
    res_instance_success = cli_instance.instance_method_command("data123", option="ok")
    print(f"Result: {res_instance_success}\n")

    # Test 7: Instance method command (CLI-like) - failure
    print("--- Test 7: Instance method command (failure) ---")
    try:
        cli_instance.instance_method_command("data456", option="fail")
    except RuntimeError as e:
        print(f"Caught expected error from instance method: {e}\n")

    print("Decorator tests finished. Check 'logs/command_telemetry.log'.")
