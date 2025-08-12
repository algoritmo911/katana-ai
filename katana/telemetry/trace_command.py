import functools
import time
import logging
from typing import Any, Callable, List, Optional
# Ensure this import path is correct based on your project structure.
# It might be katana.memory.core if memory is a direct submodule of katana.
from katana.memory.core import MemoryCore

# Initialize logger for this module
logger = logging.getLogger(__name__)

# Global Supabase client instance to avoid reinitialization on every call
# This assumes MemoryCore is cheap to instantiate if not fully initialized,
# or that it handles its own singleton/connection pooling if necessary.
# If MemoryCore manages a persistent connection, this might need adjustment
# for long-running applications or specific framework integrations.
supabase_memory_client_instance: Optional[MemoryCore] = None

def get_supabase_memory_client() -> Optional[MemoryCore]:
    """Initializes and returns a global MemoryCore instance."""
    global supabase_memory_client_instance
    if supabase_memory_client_instance is None:
        supabase_memory_client_instance = MemoryCore()
    return supabase_memory_client_instance

def trace_command(
    use_supabase: bool = False,
    tags: Optional[List[str]] = None,
    user_id_arg_name: str = "user_id" # Default arg name to look for user_id
):
    """
    A decorator to log command execution time, input, output, and success status.
    Optionally logs to Supabase if use_supabase is True.

    Args:
        use_supabase: If True, logs will be sent to Supabase.
        tags: A list of tags to associate with the log entry.
        user_id_arg_name: The name of the argument in the decorated function
                          that holds the user_id. If not found, 'unknown_user' is used.
    """
    if tags is None:
        tags = []

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            command_name = func.__name__
            logger.info(f"Executing command: {command_name} with tags: {tags}")

            # Attempt to find user_id from function arguments
            user_id = kwargs.get(user_id_arg_name)
            if user_id is None:
                try:
                    func_params = func.__code__.co_varnames
                    if user_id_arg_name in func_params:
                        user_id_idx = func_params.index(user_id_arg_name)
                        if user_id_idx < len(args):
                            user_id = args[user_id_idx]
                except AttributeError: # pragma: no cover
                    pass # func might not have __code__ (e.g. built-in)

            if user_id is None:
                user_id = "unknown_user" # Default if not found

            # Prepare input_data description
            # For simplicity, just logging kwargs. A more robust solution might inspect args too.
            input_data = {"args": args, "kwargs": kwargs}

            start_time = time.perf_counter()
            success = False
            output_data = None
            error_message = None

            try:
                output_data = func(*args, **kwargs)
                success = True
                logger.info(f"Command {command_name} executed successfully.")
            except Exception as e:
                error_message = str(e)
                logger.error(f"Command {command_name} failed: {e}", exc_info=True)
                # Re-raise the exception to maintain original behavior
                raise
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                logger.info(f"Command {command_name} finished in {duration:.4f} seconds.")

                if use_supabase:
                    client = get_supabase_memory_client()
                    if client and client.client: # Check if client is usable
                        # If there was an error, output_data might be None.
                        # Log the error message instead or in addition.
                        final_output_data = output_data
                        if not success and error_message:
                             final_output_data = {"error": error_message}

                        client.add_dialogue(
                            user_id=str(user_id), # Ensure user_id is a string
                            command_name=command_name,
                            input_data=input_data,
                            output_data=final_output_data,
                            duration=duration,
                            success=success,
                            tags=tags,
                        )
                        logger.info(f"Command {command_name} log sent to Supabase.")
                    elif client:
                        logger.warning(
                            f"Supabase client not fully initialized (URL/Key missing). "
                            f"Skipping Supabase log for command {command_name}."
                        )
                    else: # pragma: no cover
                        logger.error(
                            "Failed to get Supabase client instance. "
                            f"Skipping Supabase log for command {command_name}."
                        )
            return output_data

        return wrapper
    return decorator

# Example of how to use the decorator (for illustration)
if __name__ == "__main__": # pragma: no cover
    # This example assumes SUPABASE_URL and SUPABASE_KEY are set in environment
    # if you want to test the Supabase logging part.

    @trace_command(use_supabase=True, tags=["example", "test"], user_id_arg_name="user")
    def example_command(user: str, message: str, repeat: int = 1):
        """A simple example command."""
        logger.info(f"example_command called by {user} with message: '{message}' and repeat: {repeat}")
        if message == "fail":
            raise ValueError("Simulated failure")
        return {"response": f"{message} " * repeat}

    @trace_command(use_supabase=False, tags=["no_supabase"]) # Supabase logging disabled for this one
    def another_example_command(data: dict):
        logger.info(f"another_example_command called with data: {data}")
        return {"status": "processed", "input_data_keys": list(data.keys())}

    # Test calls
    try:
        # This call should log to Supabase if configured
        result1 = example_command(user="test_user_001", message="Hello", repeat=2)
        logger.info(f"Result 1: {result1}")

        # This call will also attempt to log to Supabase
        result_user_in_args = example_command("test_user_007", message="Positional User")
        logger.info(f"Result (user_in_args): {result_user_in_args}")

    except ValueError as e:
        logger.error(f"Caught expected error from example_command: {e}")

    try:
        # This call should also log to Supabase, demonstrating failure logging
        example_command(user="test_user_002", message="fail")
    except ValueError as e:
        logger.error(f"Caught expected failure from example_command: {e}")

    # This call should not log to Supabase
    result2 = another_example_command(data={"key1": "value1", "key2": 123})
    logger.info(f"Result 2: {result2}")

    # Example with no user_id argument (should default to "unknown_user")
    @trace_command(use_supabase=True, tags=["unknown_user_test"])
    def command_without_user_id(text: str):
        logger.info(f"Command without user_id called with text: {text}")
        return f"Processed: {text}"

    command_without_user_id(text="some_text")

    # Example to show that the global client instance is reused
    client1 = get_supabase_memory_client()
    client2 = get_supabase_memory_client()
    logger.info(f"Client1 is Client2: {client1 is client2}")
    if client1:
        logger.info(f"Client initialized: {client1.client is not None}")

    logger.info("Example usage finished.")
