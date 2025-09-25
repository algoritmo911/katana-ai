from supabase import Client
from collections import Counter

def decide_coder(supabase: Client) -> int | None:
    """
    Decides which coder should be assigned the next task based on current workload.
    The coder with the fewest active (non-completed) tasks is chosen.

    Args:
        supabase: The Supabase client instance.

    Returns:
        The ID of the selected coder, or None if no coders are available.
    """
    print("Strategist: Deciding on the best coder for the new task...")

    try:
        # 1. Fetch all coders
        coders_res = supabase.table('coders').select('id').execute()
        if not coders_res.data:
            print("Strategist: No coders found in the database.")
            return None

        coder_ids = [coder['id'] for coder in coders_res.data]
        print(f"Strategist: Found {len(coder_ids)} potential coders: {coder_ids}")

        # 2. Fetch all tasks that are not 'completed' to determine workload
        # We only need the coder_id for counting
        active_tasks_res = supabase.table('tasks').select('coder_id').neq('status', 'completed').execute()

        # This handles the case where there might be an error or no active tasks
        active_tasks = active_tasks_res.data if active_tasks_res.data else []

        # 3. Count active tasks for each coder
        # We only care about tasks that are actually assigned to a coder
        workload_counts = Counter(task['coder_id'] for task in active_tasks if task['coder_id'])
        print(f"Strategist: Current workload: {workload_counts}")

        # 4. Ensure all coders are in the workload count, with 0 if they have no tasks
        for coder_id in coder_ids:
            if coder_id not in workload_counts:
                workload_counts[coder_id] = 0

        # 5. Find the coder with the minimum number of active tasks
        # The Counter's most_common() method can't find the minimum directly,
        # so we find the minimum value and select a key with that value.
        if not workload_counts:
             # This case happens if there are coders but no tasks have ever been assigned.
             # We can just return the first coder.
             print("Strategist: No active tasks found. Assigning to the first available coder.")
             return coder_ids[0]

        # Find the coder with the minimum task count
        min_tasks = float('inf')
        best_coder_id = None

        # We iterate through all known coders to ensure we consider those with 0 tasks
        for coder_id in coder_ids:
            count = workload_counts.get(coder_id, 0)
            if count < min_tasks:
                min_tasks = count
                best_coder_id = coder_id

        print(f"Strategist: Best coder found: ID {best_coder_id} with {min_tasks} active tasks.")
        return best_coder_id

    except Exception as e:
        print(f"Strategist: An error occurred during decision making: {e}")
        # Fallback to a safe default: return the first coder if any exist
        if 'coders_res' in locals() and coders_res.data:
            print("Strategist: Falling back to assigning the first coder in the list.")
            return coders_res.data[0]['id']
        return None