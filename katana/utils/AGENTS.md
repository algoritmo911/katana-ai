# Agent Instructions for Katana Utilities

This document provides guidance for AI agents working with the utilities in the `katana/utils/` directory, particularly concerning the command tracing and Supabase integration.

## Command Tracing with `@trace_command` and Supabase

A telemetry system is in place to capture detailed traces of command executions from various parts of the Katana application (CLI, Telegram bot, etc.). These traces are sent to a Supabase instance for storage and analysis.

### Decorator Usage

The primary mechanism for this is the `@trace_command` decorator located in `katana/utils/telemetry.py`.

- When applying this decorator to a function, ensure that the function can accept `user_id` and `context_id` as keyword arguments if you intend to provide specific user/context tracking.
- The decorator will automatically extract these from `kwargs` if present. If not provided, they will default to "N/A".
- Example:
  ```python
  from katana.utils.telemetry import trace_command

  @trace_command
  def my_traced_function(arg1, arg2, user_id="default_user", context_id="default_context", **other_kwargs):
      # ... function logic ...
      return "result"

  # Call it like this:
  my_traced_function("val1", "val2", user_id="specific_user_123", context_id="session_abc")
  ```

### Supabase Configuration

The `SupabaseMemoryClient` (in `katana/utils/supabase_client.py`) handles the communication with Supabase. It requires the following environment variables to be set:

- `SUPABASE_URL`: The URL of your Supabase project.
- `SUPABASE_KEY`: The anon key (or service role key, if appropriate permissions are set up) for your Supabase project.

If these variables are not set, the `SupabaseMemoryClient` will not be able to connect, and the `@trace_command` decorator will fall back to printing trace data to `stdout` and logging a warning.

### Supabase Table Structure

Traces are intended to be saved to a Supabase table, typically named `command_traces`. The structure of the data sent to this table includes (but is not limited to):

- `trace_id` (uuid, primary key): Unique ID for the trace.
- `name` (text): Name of the function/command that was traced.
- `user_id` (text): Identifier for the user who initiated the command (e.g., 'cli_user', Telegram user ID).
- `context_id` (text): Identifier for the context of the command (e.g., 'cli_session', Telegram chat ID).
- `time_start` (timestamp with timezone): Start time of the execution.
- `time_end` (timestamp with timezone): End time of the execution.
- `duration` (float): Duration of the execution in seconds.
- `args` (jsonb): Positional arguments passed to the function.
- `kwargs` (jsonb): Keyword arguments passed to thefunction (includes `user_id`, `context_id` if they were passed).
- `return_value` (jsonb): The value returned by the function (serialized to string if not JSON-compatible).
- `exception` (text, nullable): Information about any exception raised during execution.

Ensure your Supabase table schema matches these fields and their expected data types for successful data ingestion.

### Modifying Traced Functions

- When modifying a function that is already decorated with `@trace_command`, be mindful that its arguments, return value, and any exceptions it might raise are part of the telemetry.
- If you change the function signature (especially how `user_id` or `context_id` might be passed or inferred), update the call sites and potentially the decorator's logic if it relies on specific argument names not passed via `kwargs`. (Currently, it expects them in `kwargs`).

This telemetry system is crucial for monitoring and debugging command executions. Please ensure its integrity and proper functioning when making changes in related areas.
