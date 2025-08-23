import asyncio
import nats
from nats.errors import ConnectionClosedError, TimeoutError, NoServersError
import time

async def main():
    """
    The main function for the Chronos daemon.
    Connects to NATS and publishes a heartbeat every second.
    """
    nc = None
    while True:
        try:
            if nc is None or not nc.is_connected:
                print("Connecting to NATS...")
                nc = await nats.connect("nats://localhost:4222")
                print("Connected to NATS.")

            while True:
                current_time = time.time()
                await nc.publish("chronos.tick.1s", str(current_time).encode())
                print(f"Published heartbeat at {current_time}")
                await asyncio.sleep(1)

        except (ConnectionClosedError, TimeoutError, NoServersError) as e:
            print(f"Connection error: {e}. Reconnecting in 5 seconds...")
            if nc and not nc.is_closed:
                await nc.close()
            nc = None
            await asyncio.sleep(5)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            if nc and not nc.is_closed:
                await nc.close()
            break

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Chronos daemon stopped.")
