from katana.praetor.agent import PraetorAgent
import time

def main():
    """
    Initializes and starts the PraetorAgent.
    """
    try:
        agent = PraetorAgent()
        agent.start()
    except ValueError as e:
        print(f"Error initializing PraetorAgent: {e}")
        print("Please ensure all required environment variables are set.")
    except Exception as e:
        # Catching broader exceptions to prevent the container from crash-looping
        # in case of unexpected errors during startup (e.g., network issues).
        print(f"An unexpected error occurred: {e}")
        # In a real-world scenario, you might want a more robust retry mechanism.
        print("Agent will not start. Exiting in 60 seconds.")
        time.sleep(60)

if __name__ == "__main__":
    main()
