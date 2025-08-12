import time
from typing import List

class TemporalSensor:
    """
    Analyzes the timing and rhythm of operator requests to infer state.
    This sensor is stateful and should be managed as a singleton per user session.
    """
    def __init__(self):
        self.request_timestamps: List[float] = []

    def log_request(self):
        """Adds a timestamp for a new request."""
        self.request_timestamps.append(time.time())

    def analyze(self):
        """
        Calculates temporal features based on the history of requests.
        """
        from ..contracts import TemporalFeatures

        if not self.request_timestamps:
            return TemporalFeatures(
                requests_per_minute=0.0,
                session_duration_seconds=0,
                time_since_last_request_seconds=0
            )

        now = time.time()

        # Requests per minute
        one_minute_ago = now - 60
        recent_requests = [t for t in self.request_timestamps if t > one_minute_ago]
        requests_per_minute = len(recent_requests)

        # Session duration
        session_start_time = self.request_timestamps[0]
        session_duration_seconds = int(now - session_start_time)

        # Time since last request
        time_since_last_request_seconds = int(now - self.request_timestamps[-1])

        return TemporalFeatures(
            requests_per_minute=requests_per_minute,
            session_duration_seconds=session_duration_seconds,
            time_since_last_request_seconds=time_since_last_request_seconds
        )

if __name__ == '__main__':
    import asyncio

    async def run_simulation():
        print("--- Temporal Sensor Simulation ---")
        sensor = TemporalSensor()

        print("Logging first request...")
        sensor.log_request()
        await asyncio.sleep(1)
        print(f"Analysis 1: {sensor.analyze().model_dump_json(indent=2)}")

        print("\nLogging second request...")
        sensor.log_request()
        await asyncio.sleep(2)
        print(f"Analysis 2: {sensor.analyze().model_dump_json(indent=2)}")

        print("\n--- Simulation Complete ---")

    asyncio.run(run_simulation())
