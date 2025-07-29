def get_queue():
    """
    Returns a mock command queue.
    """
    return [
        {"command": "train_model", "priority": 1},
        {"command": "run_analysis", "priority": 2},
    ]
