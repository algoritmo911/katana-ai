import datetime
import functools
import json
import logging
import time

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def _get_user_id(func, args, kwargs):
    """
    Tries to extract user_id.
    1. From kwargs['user_id'].
    2. From args[0].user_id if args[0] seems to be 'self' for the method 'func'.
    """
    if 'user_id' in kwargs:
        return kwargs['user_id']

    if args:
        first_arg = args[0]
        # Heuristic: if func is a method of first_arg's class and first_arg has user_id
        try:
            # Check if func is a method bound to first_arg or a function that could be a method of first_arg's class
            # This is tricky because at this point `func` is the original unwrapped function.
            # A common pattern is that `args[0]` is an instance of a class, and `func` is a method of that class.
            is_method_like = hasattr(first_arg, func.__name__) and callable(getattr(first_arg, func.__name__))
            if is_method_like and hasattr(first_arg, 'user_id'):
                return getattr(first_arg, 'user_id')
        except AttributeError:
            # getattr(first_arg, func.__name__) could fail if func.__name__ is not an attr
            pass
        except Exception:
            # Catch any other unexpected errors during heuristic check
            pass # Best effort
    return None

def trace_command(func):
    """
    A decorator to log command execution details in JSON format.
    It captures input arguments, output, errors, execution time, and user_id.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        timestamp_start = datetime.datetime.now(datetime.timezone.utc)

        user_id = _get_user_id(func, args, kwargs)

        actual_args = list(args) # Keep all args for logging, including 'self'

        start_time = time.perf_counter()
        result = None
        error_info = None

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            error_info = str(e)
            # Optionally, re-raise the exception if you don't want to suppress it
            # raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            log_data = {
                "timestamp": timestamp_start.isoformat().replace("+00:00", "Z"),
                "command": func.__name__, # Using actual function name
                "user_id": user_id,
                "args": actual_args, # Log potentially modified args list
                "kwargs": kwargs,
                "result": result,
                "duration_ms": round(duration_ms, 2),
                "error": error_info,
            }

            # To handle non-serializable items in args/kwargs/result for JSON
            try:
                logging.info(json.dumps(log_data, default=str))
            except TypeError as te:
                logging.error(f"Error serializing log data for command {func.__name__}: {te}")
                # Fallback logging with potentially problematic fields stringified
                fallback_log_data = {
                    k: str(v) if isinstance(v, (list, dict, tuple)) or not isinstance(v, (str, int, float, bool, type(None))) else v
                    for k, v in log_data.items()
                }
                logging.info(json.dumps(fallback_log_data, default=str))


        if error_info: # Re-raise after logging if an error occurred
            # This depends on desired behavior: suppress, log and return None, or log and re-raise.
            # For now, let's assume we want to know an error happened but not crash the logger caller.
            # The original exception 'e' can be re-raised if needed: raise e
            pass

        return result # Return the original result or None if error (and not re-raised)

    return wrapper

if __name__ == "__main__":
    class TestClass:
        def __init__(self, user_id=None):
            self.user_id = user_id

        @trace_command
        def my_method(self, a, b, user_id=None): # user_id can also be a kwarg
            """A sample method."""
            print(f"Executing my_method with {a}, {b}")
            if b == 0:
                raise ValueError("Division by zero")
            time.sleep(0.05) # Simulate work
            return a / b

        @trace_command
        def method_with_user_id_in_self(self, x):
            """Method where user_id is in self."""
            print(f"Executing method_with_user_id_in_self with {x}")
            time.sleep(0.02)
            return f"Processed {x} for user {self.user_id}"

    @trace_command
    def my_function(x, y, user_id="global_user"):
        """A sample function."""
        print(f"Executing my_function with {x}, {y}")
        time.sleep(0.03)
        return x + y

    @trace_command
    def function_no_user_id(data):
        print(f"Executing function_no_user_id with {data}")
        return f"Processed: {data}"

    @trace_command
    def function_with_error():
        raise RuntimeError("This is a test error")

    print("\n--- Testing method call ---")
    test_obj = TestClass()
    try:
        test_obj.my_method(10, 2) # user_id from self if TestClass("u123") or from kwarg
    except ValueError as e:
        print(f"Caught expected error: {e}")

    print("\n--- Testing method call with explicit user_id kwarg ---")
    test_obj.my_method(10, 5, user_id="user_explicit_kwarg")

    print("\n--- Testing method call with error ---")
    try:
        test_obj.my_method(10, 0)
    except ValueError as e:
        print(f"Caught expected error from my_method(10,0): {e}")

    print("\n--- Testing method with user_id in self ---")
    test_obj_with_id = TestClass(user_id="self_user_id_123")
    test_obj_with_id.method_with_user_id_in_self("data_for_self_user")


    print("\n--- Testing standalone function call with user_id kwarg ---")
    my_function(5, 3, user_id="user_from_kwarg")

    print("\n--- Testing standalone function call with default user_id in signature ---")
    my_function(7, 8) # Uses default user_id from function signature

    print("\n--- Testing function without user_id ---")
    function_no_user_id("some_data")

    print("\n--- Testing function that raises an error ---")
    try:
        function_with_error()
    except RuntimeError as e:
        print(f"Caught expected error from function_with_error: {e}")

    print("\n--- Testing with non-serializable data (simulated) ---")
    class NonSerializable:
        def __str__(self):
            return "<NonSerializable object>"

    @trace_command
    def function_with_non_serializable(arg1, kwarg1=None):
        print(f"Running with {arg1}, {kwarg1}")
        return {"data": arg1, "extra": kwarg1}

    non_serializable_obj = NonSerializable()
    function_with_non_serializable(non_serializable_obj, kwarg1=[non_serializable_obj, 123])
    function_with_non_serializable({"key": non_serializable_obj})

    print("\n--- Testing command name (using a valid Python function name) ---")
    @trace_command
    def command_reset_simulation(param1, user_id="reset_user"): # Simulating a command-like name
        """Simulates a command like /reset"""
        print(f"Executing command_reset_simulation with {param1}")
        return f"Reset OK for {param1}"

    command_reset_simulation("--force")
    command_reset_simulation(param1="--soft", user_id="another_user")

    print("\nDecorator tests complete.")
