import functools
import time
import getpass
from datetime import datetime, timezone
from katana.logging.telemetry_logger import log_command_telemetry

def trace_command(func):
    """
    A decorator to log command execution telemetry.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        command_name = func.__name__
        # If the function is a method of a class, try to get the class name
        # and prepend it to the command name for better context.
        # This is a simple approach; more sophisticated methods might be needed
        # if commands are deeply nested or part of complex class hierarchies.
        is_method = False
        if hasattr(func, '__qualname__') and '.' in func.__qualname__:
            # Example: <class_name>.<method_name>
            command_name = func.__qualname__
            is_method = True # Likely a method if __qualname__ has a dot

        # If it's identified as a method and args exist, assume args[0] is 'self'
        # and exclude it from logged arguments.
        actual_args = args
        if is_method and args:
            actual_args = args[1:] # Get elements from index 1 to end

        start_perf_counter = time.perf_counter()
        start_timestamp_iso = datetime.now(timezone.utc).isoformat()
        username = getpass.getuser() # Get username
        success = False
        result = None
        error_obj = None

        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            error_obj = e
            # Re-raise the exception so the command behaves as it normally would
            raise
        finally:
            end_perf_counter = time.perf_counter()
            execution_time = end_perf_counter - start_perf_counter
            log_command_telemetry(
                command_name=command_name,
                args=actual_args, # Log actual user-provided args
                kwargs=kwargs,
                success=success,
                result=result,
                error=error_obj,
                execution_time=execution_time,
                user=username,
                start_time_iso=start_timestamp_iso
            )
    return wrapper

if __name__ == '__main__':
    # Example Usage (for testing the decorator directly)
    # This requires the logger to be working.

    # Mock logger for direct testing if needed, or ensure LOG_FILE_PATH is accessible
    # For now, we assume katana.logging.telemetry_logger is importable and works.

    @trace_command
    def sample_successful_command(a, b, greet="hello"):
        print(f"Executing sample_successful_command with {a}, {b}, {greet}")
        return f"{greet} {a + b}"

    @trace_command
    def sample_failing_command(x):
        print(f"Executing sample_failing_command with {x}")
        if x == 0:
            raise ValueError("Division by zero simulated")
        return 10 / x

    class TestCLI:
        def __init__(self, name):
            self.name = name

        @trace_command
        def instance_method_command(self, value, option=None):
            print(f"Executing instance_method_command on {self.name} with {value}, {option}")
            if option == "fail":
                raise RuntimeError("Simulated failure in instance method")
            return f"Instance {self.name} processed {value}"

    print("Testing trace_command decorator...")

    # Test successful command
    print("\nTesting successful command:")
    res_success = sample_successful_command(5, 10, greet="Result:")
    print(f"Result: {res_success}")

    # Test failing command
    print("\nTesting failing command:")
    try:
        sample_failing_command(0)
    except ValueError as e:
        print(f"Caught expected error: {e}")

    print("\nTesting successful command (another case):")
    res_success_2 = sample_failing_command(2)
    print(f"Result: {res_success_2}")

    # Test instance method
    print("\nTesting instance method command (success):")
    cli_instance = TestCLI("MyCLI")
    res_instance_success = cli_instance.instance_method_command("data123", option="ok")
    print(f"Result: {res_instance_success}")

    print("\nTesting instance method command (failure):")
    try:
        cli_instance.instance_method_command("data456", option="fail")
    except RuntimeError as e:
        print(f"Caught expected error from instance method: {e}")

    print("\nDecorator tests finished. Check 'logs/command_telemetry.log'.")
