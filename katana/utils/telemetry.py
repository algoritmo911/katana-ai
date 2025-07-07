import time
import json
import uuid
from functools import wraps
from datetime import datetime, timezone

def trace_command(func):
    """
    A decorator to trace command execution, logging details in JSON format.

    Logs:
    - id: A unique identifier for the trace.
    - name: The name of the decorated function.
    - time_start: The start time of the function call (ISO 8601).
    - time_end: The end time of the function call (ISO 8601).
    - duration: The duration of the function call in seconds.
    - args: Positional arguments passed to the function.
    - kwargs: Keyword arguments passed to the function.
    - return_value: The value returned by the function.
    - exception: The exception raised by the function, if any.
    """
    # print(f"DECORATOR: trace_command called to decorate {getattr(func, '__name__', 'unknown_func')}") # DEBUG REMOVED
    @wraps(func)
    def wrapper(*args, **kwargs):
        time_start_dt = datetime.now(timezone.utc)
        time_start_ns = time.perf_counter_ns()

        # There was a duplicate assignment here, removing one.
        # time_start_dt = datetime.now(timezone.utc)
        # time_start_ns = time.perf_counter_ns() # For more precise duration

        return_value = None
        exception_info = None
        original_exception = None

        try:
            return_value = func(*args, **kwargs)
        except Exception as e:
            exception_info = f"{type(e).__name__}: {str(e)}"
            original_exception = e # Store the original exception
        finally:
            time_end_dt = datetime.now(timezone.utc)
            time_end_ns = time.perf_counter_ns()
            duration_seconds = (time_end_ns - time_start_ns) / 1e9

            serializable_args = []
            try:
                for arg in args:
                    try:
                        json.dumps(arg)
                        serializable_args.append(arg)
                    except TypeError:
                        serializable_args.append(str(arg))
            except Exception as e: # Catch potential errors during args processing
                serializable_args = [f"Error processing args: {type(e).__name__}: {str(e)}"]


            serializable_kwargs = {}
            try:
                for k, v in kwargs.items():
                    try:
                        json.dumps(v)
                        serializable_kwargs[k] = v
                    except TypeError:
                        serializable_kwargs[k] = str(v)
            except Exception as e: # Catch potential errors during kwargs processing
                serializable_kwargs = {f"Error processing kwargs": f"{type(e).__name__}: {str(e)}"}


            serializable_return_value = None
            if exception_info is None:
                try:
                    json.dumps(return_value)
                    serializable_return_value = return_value
                except TypeError:
                    serializable_return_value = str(return_value)
                except Exception as e: # Catch potential errors during return_value processing
                    serializable_return_value = f"Error processing return_value: {type(e).__name__}: {str(e)}"

            trace_data = {
                "id": str(uuid.uuid4()),
                "name": func.__name__,
                "time_start": time_start_dt.isoformat(),
                "time_end": time_end_dt.isoformat(),
                "duration": duration_seconds,
                "args": serializable_args,
                "kwargs": serializable_kwargs,
                "return_value": serializable_return_value,
                "exception": exception_info,
            }

            try:
                print(json.dumps(trace_data))
            except Exception as e:
                # Fallback if json.dumps itself fails (e.g. with the error messages)
                print(f'{{"id": "{str(uuid.uuid4())}", "name": "{func.__name__}", "error": "Failed to dump trace_data to JSON: {type(e).__name__}: {str(e)}" }}')

        if original_exception:
            raise original_exception

        return return_value

    # print(f"DECORATOR: trace_command returning wrapper for {getattr(func, '__name__', 'unknown_func')}") # DEBUG REMOVED
    return wrapper

if __name__ == '__main__':
    # Example Usage (for testing the decorator directly)

    @trace_command
    def sample_function(a, b, c="default"):
        print(f"Inside sample_function with a={a}, b={b}, c={c}")
        if a == 0:
            raise ValueError("Input 'a' cannot be zero.")
        return f"Result: {a + b}, {c}"

    @trace_command
    def simple_function():
        print("Inside simple_function")
        return "Simple!"

    @trace_command
    def function_with_non_serializable_arg(obj):
        print(f"Inside function_with_non_serializable_arg with obj={obj}")
        return {"status": "processed", "obj_type": str(type(obj))}

    class NonSerializableObject:
        def __init__(self, name):
            self.name = name
        def __str__(self):
            return f"<NonSerializableObject: {self.name}>"

    print("\nTesting sample_function (success case):")
    sample_function(1, 2, c="test")

    print("\nTesting sample_function (failure case):")
    try:
        sample_function(0, 2) # This will raise ValueError
    except ValueError as e:
        print(f"Caught expected error in test: {e}")

    print("\nTesting simple_function (no args, no kwargs):")
    simple_function()

    print("\nTesting with non-serializable arguments and return:")
    my_obj = NonSerializableObject("MyInstance")
    function_with_non_serializable_arg(my_obj)

    @trace_command
    def function_returning_non_serializable():
        print("Inside function_returning_non_serializable")
        return NonSerializableObject("ReturnedObj")

    function_returning_non_serializable()

    print("\nTesting decorator with a function that takes no args and returns None implicitly")
    @trace_command
    def no_args_returns_none():
        print("Running no_args_returns_none")
        # No explicit return, so returns None

    no_args_returns_none()
