import time
import json
import uuid
from functools import wraps
from datetime import datetime, timezone
from katana.utils.supabase_client import SupabaseMemoryClient # Import Supabase client
from katana.logger import get_logger # For logging within the decorator if needed

# Initialize logger for this module, though primarily Supabase client will log
logger = get_logger(__name__)

# Global instance of SupabaseMemoryClient, initialized once.
# This avoids re-initializing the client (and re-checking env vars) on every decorated function call.
# However, it means env vars are read at module load time.
# If dynamic changes to SUPABASE_URL/KEY are needed without restarting, a different approach would be required.
supabase_client_instance = SupabaseMemoryClient()

# import inspect # No longer needed for sync-only decorator

def trace_command(func):
    """
    A decorator to trace command execution, logging details to Supabase.
    This is a synchronous decorator; it does not await async functions.
    For async functions, 'return_value' in trace will be the coroutine object.
    Exceptions from awaiting the coroutine outside this decorator won't be caught here.

    Logs:
    - trace_id: A unique identifier for the trace.
    - name: The name of the decorated function.
    - user_id: Identifier for the user initiating the command.
    - context_id: Identifier for the context (e.g., chat session).
    - time_start: The start time of the function call (ISO 8601).
    - time_end: The end time of the function call (ISO 8601).
    - duration: The duration of the function call in seconds.
    - args: Positional arguments passed to the function.
    - kwargs: Keyword arguments passed to the function.
    - return_value: The value returned by the function. For async, this is the coroutine.
    - exception: The exception raised by the function call itself (not from awaiting).
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        time_start_dt = datetime.now(timezone.utc)
        time_start_ns = time.perf_counter_ns()

        return_value = None
        exception_info = None
        original_exception = None

        user_id = kwargs.get('user_id', 'N/A')
        context_id = kwargs.get('context_id', 'N/A')

        try:
            return_value = func(*args, **kwargs) # This will be a coroutine for async funcs
        except Exception as e:
            exception_info = f"{type(e).__name__}: {str(e)}"
            original_exception = e
        finally:
            time_end_dt = datetime.now(timezone.utc)
            time_end_ns = time.perf_counter_ns()
            duration_seconds = (time_end_ns - time_start_ns) / 1e9

            serializable_args = _serialize_args(args)
            serializable_kwargs = _serialize_kwargs(kwargs)

            s_return_value = None
            if exception_info is None: # Only process return value if no exception from func call itself
                try:
                    json.dumps(return_value)
                    s_return_value = return_value
                except TypeError:
                    s_return_value = str(return_value)
                except Exception as e_ser:
                    s_return_value = f"Error serializing return_value: {e_ser}"
            # If func call raised exception, return_value might not be meaningful or set
            # and s_return_value remains None.

            trace_data = {
                "trace_id": str(uuid.uuid4()), "name": func.__name__, "user_id": user_id,
                "context_id": context_id, "time_start": time_start_dt.isoformat(),
                "time_end": time_end_dt.isoformat(), "duration": duration_seconds,
                "args": serializable_args, "kwargs": serializable_kwargs,
                "return_value": s_return_value, # For async, this will be str(coroutine)
                "exception": exception_info, # Only if func() call itself failed
            }
            _save_trace_data(trace_data, user_id, context_id)

        if original_exception:
            raise original_exception
        return return_value # Returns coroutine for async funcs

    return wrapper # Return the single sync wrapper

def _serialize_args(args):
    serializable_args = []
    try:
        for arg in args:
            if arg.__class__.__name__ == 'Update' and arg.__module__ == 'telegram.update':
                serializable_args.append(f"<Telegram Update object id:{getattr(arg, 'update_id', 'unknown')}>")
            # Add specific handling for KatanaCore instance if it appears in args for CLI methods
            elif arg.__class__.__name__ == 'KatanaCore' and 'katana.core.cli_agent.katana' in str(arg.__class__):
                 serializable_args.append(f"<KatanaCore instance>")
            else:
                try:
                    json.dumps(arg) # Test serializability
                    serializable_args.append(arg)
                except TypeError:
                    serializable_args.append(str(arg)) # Fallback to string
    except Exception as e:
        serializable_args = [f"Error processing args: {type(e).__name__}: {str(e)}"]
    return serializable_args

def _serialize_kwargs(kwargs):
    serializable_kwargs = {}
    try:
        for k, v in kwargs.items():
            if k == 'context' and v.__class__.__name__ == 'CallbackContext' and 'telegram.ext.callbackcontext' in str(v.__class__):
                 serializable_kwargs[k] = f"<Telegram CallbackContext object>"
                 continue
            try:
                json.dumps(v) # Test serializability
                serializable_kwargs[k] = v
            except TypeError:
                serializable_kwargs[k] = str(v) # Fallback to string
    except Exception as e:
        serializable_kwargs = {f"Error processing kwargs": f"{type(e).__name__}: {str(e)}"}
    return serializable_kwargs

def _save_trace_data(trace_data, user_id, context_id):
    try:
        if supabase_client_instance and supabase_client_instance.client:
            supabase_client_instance.save_trace(trace_data)
        else:
            logger.warning("Supabase client not configured. Printing trace data instead.", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': trace_data.get('trace_id', 'unknown')})
            print(json.dumps(trace_data))
    except Exception as e:
        logger.error(f"Failed to save or print trace data: {e}. Trace Data: {str(trace_data)[:500]}", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': trace_data.get('trace_id', 'unknown')})
        # Fallback if json.dumps itself fails with the full trace_data
        try:
            print(f'{{"trace_id": "{trace_data.get("trace_id", "unknown")}", "name": "{trace_data.get("name", "unknown_func")}", "error": "Failed to dump full trace_data to JSON for printing: {type(e).__name__}" }}')
        except: # Final fallback
            print(f'{{"error": "Critical failure in trace data serialization/printing."}}')

# Old single wrapper, preserved for reference during refactor if needed, then remove.
# @wraps(func)
# def wrapper(*args, **kwargs):
#     time_start_dt = datetime.now(timezone.utc)
#     time_start_ns = time.perf_counter_ns()

#     return_value = None
#     exception_info = None
#     original_exception = None

    # Extract user_id and context_id from kwargs if provided
        # These are expected to be passed by the calling code to the decorated function
        user_id = kwargs.get('user_id', 'N/A')
        context_id = kwargs.get('context_id', 'N/A')

        # To prevent user_id and context_id from being passed to the actual function
        # if they are not part of its signature, we can create a copy of kwargs
        # or rely on the decorated function to handle unexpected kwargs (e.g. with **kwargs).
        # For now, we assume the decorated function can handle them or they are named uniquely.
        # If the decorated function does *not* expect user_id/context_id, this could cause errors.
        # A safer approach might be to pop them:
        # actual_kwargs = kwargs.copy()
        # user_id = actual_kwargs.pop('user_id', 'N/A')
        # context_id = actual_kwargs.pop('context_id', 'N/A')
        # Then call func(*args, **actual_kwargs)
        # For this iteration, let's assume they are either expected or handled.

        try:
            return_value = func(*args, **kwargs)
        except Exception as e:
            exception_info = f"{type(e).__name__}: {str(e)}"
            original_exception = e
        finally:
            time_end_dt = datetime.now(timezone.utc)
            time_end_ns = time.perf_counter_ns()
            duration_seconds = (time_end_ns - time_start_ns) / 1e9

            serializable_args = []
            try:
                # Avoid serializing the Update object if it's too complex or large
                for arg in args:
                    if arg.__class__.__name__ == 'Update' and arg.__module__ == 'telegram.update':
                        serializable_args.append(f"<Telegram Update object id:{arg.update_id}>")
                    else:
                        try:
                            json.dumps(arg) # Test serializability
                            serializable_args.append(arg)
                        except TypeError:
                            serializable_args.append(str(arg)) # Fallback to string
            except Exception as e:
                serializable_args = [f"Error processing args: {type(e).__name__}: {str(e)}"]

            serializable_kwargs = {}
            try:
                for k, v in kwargs.items():
                    # Avoid logging potentially sensitive or overly verbose kwargs like context itself
                    if k == 'context' and v.__class__.__name__ == 'CallbackContext':
                         serializable_kwargs[k] = f"<Telegram CallbackContext object>"
                         continue
                    try:
                        json.dumps(v) # Test serializability
                        serializable_kwargs[k] = v
                    except TypeError:
                        serializable_kwargs[k] = str(v) # Fallback to string
            except Exception as e:
                serializable_kwargs = {f"Error processing kwargs": f"{type(e).__name__}: {str(e)}"}

            serializable_return_value = None
            if exception_info is None: # Only process return value if no exception
                try:
                    # If return_value is a coroutine, its result is already captured by `await func`
                    # or it would have raised an exception.
                    # For non-async functions, return_value is the direct result.
                    json.dumps(return_value) # Test serializability
                    serializable_return_value = return_value
                except TypeError:
                    serializable_return_value = str(return_value) # Fallback to string
                except Exception as e:
                     serializable_return_value = f"Error processing return_value: {type(e).__name__}: {str(e)}"
            # Ensure if an exception occurred, serializable_return_value is None for the trace
            else: # exception_info is not None
                serializable_return_value = None

            trace_data = {
                "trace_id": str(uuid.uuid4()), # Changed from "id"
                "name": func.__name__,
                "user_id": user_id,
                "context_id": context_id,
                "time_start": time_start_dt.isoformat(),
                "time_end": time_end_dt.isoformat(),
                "duration": duration_seconds,
                "args": serializable_args,
                "kwargs": serializable_kwargs, # These are the original kwargs including user_id/context_id
                "return_value": serializable_return_value,
                "exception": exception_info,
            }

            try:
                # Use the global Supabase client instance
                if supabase_client_instance and supabase_client_instance.client: # Check if client is configured
                    supabase_client_instance.save_trace(trace_data)
                else:
                    # Fallback to printing if Supabase is not configured
                    logger.warning("Supabase client not configured. Printing trace data instead.", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': trace_data['trace_id']})
                    print(json.dumps(trace_data))
            except Exception as e:
                # Log error during trace saving and fallback to print
                logger.error(f"Failed to save trace to Supabase: {e}. Printing trace data.", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': trace_data['trace_id']})
                try:
                    print(json.dumps(trace_data))
                except Exception as dump_e:
                     logger.error(f"Failed to even dump trace_data to JSON for printing: {dump_e}", extra={'user_id': user_id, 'chat_id': context_id, 'message_id': trace_data['trace_id']})


        if original_exception:
            raise original_exception

        return return_value
    return wrapper

if __name__ == '__main__':
    # Example Usage (for testing the decorator directly)
    # Ensure SUPABASE_URL and SUPABASE_KEY are set in environment for Supabase logging
    # or it will fall back to printing.
    from katana.logger import setup_logging
    import logging as py_logging
    setup_logging(log_level=py_logging.DEBUG)


    logger.info("--- Testing @trace_command decorator ---")
    logger.info("NOTE: Set SUPABASE_URL and SUPABASE_KEY env vars to test Supabase integration.")
    logger.info("If not set, traces will be printed to stdout by the decorator as a fallback.")


    @trace_command
    def sample_function_cli(command, user_id="cli_user", context_id="cli_session", **cli_kwargs):
        # cli_kwargs might contain other specific params for the command
        print(f"Inside sample_function_cli with command='{command}', user_id='{user_id}', context_id='{context_id}', extras={cli_kwargs}")
        if command == "error":
            raise ValueError("Simulated command error.")
        return f"CLI Result: {command} executed by {user_id}"

    @trace_command
    def sample_function_telegram(message_text, user_id, context_id, **tg_kwargs):
        # tg_kwargs might contain other specific params for the command
        print(f"Inside sample_function_telegram with message='{message_text}', user_id='{user_id}', context_id='{context_id}', extras={tg_kwargs}")
        return f"TG Reply: Processed '{message_text}' for {user_id} in chat {context_id}"


    @trace_command
    def simple_function_no_ids(): # No user_id/context_id passed in kwargs
        print("Inside simple_function_no_ids")
        return "Simple!"

    class NonSerializableObject:
        def __init__(self, name):
            self.name = name
        def __str__(self):
            return f"<NonSerializableObject: {self.name}>"

    @trace_command
    def function_with_non_serializable_arg(obj, user_id="test_user", context_id="test_ctx"):
        print(f"Inside function_with_non_serializable_arg with obj={obj}")
        return {"status": "processed", "obj_type": str(type(obj))}


    print("\nTesting sample_function_cli (success case):")
    sample_function_cli("list_files", user_id="user123", context_id="session_abc", detail=True)

    print("\nTesting sample_function_cli (failure case):")
    try:
        sample_function_cli("error", user_id="user456", context_id="session_xyz")
    except ValueError as e:
        print(f"Caught expected error in test: {e}")

    print("\nTesting sample_function_telegram:")
    sample_function_telegram("Hello bot", user_id="telegram_user_789", context_id="telegram_chat_123", client_type="mobile")

    print("\nTesting simple_function_no_ids (user_id/context_id will be N/A in trace):")
    simple_function_no_ids() # user_id and context_id will be 'N/A'

    print("\nTesting with non-serializable arguments and return:")
    my_obj = NonSerializableObject("MyInstance")
    function_with_non_serializable_arg(my_obj, user_id="user_non_serial", context_id="ctx_non_serial")

    @trace_command
    def function_returning_non_serializable(user_id="test_user", context_id="test_ctx"):
        print("Inside function_returning_non_serializable")
        return NonSerializableObject("ReturnedObj")

    function_returning_non_serializable(user_id="user_ret_non_serial", context_id="ctx_ret_non_serial")

    logger.info("--- End of @trace_command decorator Test ---")
    logger.info("Check console output for trace data (either logged by SupabaseClient or printed by decorator).")
