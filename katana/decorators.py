import functools
import logging
import time # Optional: for timing the command execution

# Configure basic logging if not already configured elsewhere at this level
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def trace_command(func):
    """
    A decorator to trace command execution, including user_id and other context.
    It logs the call, arguments, execution time, and any exceptions.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Attempt to extract user_id and other context from kwargs or args
        # This is a generic approach; specific extraction might be needed in the decorated function
        user_id = kwargs.get('user_id', None)
        if user_id is None: # Fallback: check if 'update' object is in args for bot commands
            try:
                # Example: update = args[1] for methods like handle_self_evolve(self, update, context)
                # This needs to be robust or handled by the caller passing user_id explicitly
                if len(args) > 1 and hasattr(args[1], 'message') and hasattr(args[1].message, 'from_user'):
                    user_id = args[1].message.from_user.id
            except Exception: # Broad exception to avoid breaking the decorator
                pass # user_id remains None

        func_name = func.__name__
        arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]

        # Prepare loggable arguments, avoiding overly verbose or sensitive data if necessary
        log_args = []
        # Log positional arguments
        for i, arg_val in enumerate(args):
            arg_name = arg_names[i] if i < len(arg_names) else f"arg_{i}"
            if isinstance(arg_val, (str, int, float, bool, list, dict, tuple)) or arg_val is None:
                 # Truncate long strings/collections if necessary
                if isinstance(arg_val, (str, list, dict, tuple)) and len(str(arg_val)) > 100:
                    log_args.append(f"{arg_name}=<Truncated {type(arg_val).__name__}>")
                else:
                    log_args.append(f"{arg_name}={arg_val!r}")
            else:
                log_args.append(f"{arg_name}=<{type(arg_val).__name__}>") # Log type for complex objects

        # Log keyword arguments
        for k, v in kwargs.items():
            if k == 'user_id': continue # Already captured
            if isinstance(v, (str, int, float, bool, list, dict, tuple)) or v is None:
                if isinstance(v, (str, list, dict, tuple)) and len(str(v)) > 100:
                    log_args.append(f"{k}=<Truncated {type(v).__name__}>")
                else:
                    log_args.append(f"{k}={v!r}")
            else:
                log_args.append(f"{k}=<{type(v).__name__}>")

        log_entry_start = f"TRACE: Executing command '{func_name}'"
        if user_id:
            log_entry_start += f" by user_id '{user_id}'"
        log_entry_start += f" with args: ({', '.join(log_args)})"

        logger.info(log_entry_start)
        print(log_entry_start) # Also print for visibility during CLI execution / testing

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"TRACE: Command '{func_name}' completed in {duration:.4f} seconds.")
            print(f"TRACE: Command '{func_name}' completed in {duration:.4f} seconds.")
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error(f"TRACE: Command '{func_name}' failed after {duration:.4f} seconds with error: {e}", exc_info=True)
            print(f"TRACE: Command '{func_name}' failed after {duration:.4f} seconds with error: {e}")
            raise # Re-raise the exception to not alter program flow
    return wrapper

# Example Usage (for testing the decorator itself):
# @trace_command
# def my_example_command(arg1, arg2="default", user_id=None):
#     print(f"Executing my_example_command with {arg1}, {arg2}")
#     if arg1 == "error":
#         raise ValueError("Simulated error")
#     return "Success"

# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
#     my_example_command("test_value1", user_id="user123")
#     my_example_command("another_value", arg2="custom_val", user_id="user456")
#     my_example_command(arg1={"complex": "data", "key": [1,2,3]}, arg2="custom_val", user_id="user789")
#     try:
#         my_example_command("error", user_id="user_error")
#     except ValueError:
#         print("Caught simulated error as expected.")
#     my_example_command("a_very_long_string_argument_that_should_be_truncated_if_it_exceeds_the_limit_set_in_the_decorator_otherwise_it_will_be_logged_as_is", user_id="user_long_string")
#     my_example_command(complex_object_arg=SimpleBot()) # Example with a complex object not directly serializable to log
#     # Test with a function that has `update` and `context`
#     class MockUpdate:
#         def __init__(self, user_id):
#             self.message = MockMessage(user_id)
#     class MockMessage:
#         def __init__(self, user_id):
#             self.from_user = MockFromUser(user_id)
#     class MockFromUser:
#         def __init__(self, id):
#             self.id = id

#     @trace_command
#     def bot_command_example(self_mock, update_mock, context_mock):
#         print(f"Executing bot_command_example with update from user {update_mock.message.from_user.id}")

#     bot_command_example("self_instance_mock", MockUpdate(user_id="bot_user_123"), "context_mock_data")
#     # Test case where user_id is explicitly passed via kwarg
#     bot_command_example("self_instance_mock", MockUpdate(user_id="bot_user_should_be_overridden"), "context_mock_data", user_id="explicit_user_id")

#     # Test without user_id
#     @trace_command
#     def cli_command_example(args_obj):
#         print(f"Executing CLI command with args: {args_obj}")

#     cli_command_example({"param1": "value1", "no_simulated_crash": True})
#     print("Decorator tests complete.")
