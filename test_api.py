import httpx
import asyncio
import uuid

BASE_URL = "http://127.0.0.1:8000"

async def run_test():
    """
    Runs a simple test against the /agent/chat endpoint.
    """
    chat_id = f"test-chat-{uuid.uuid4()}"
    print(f"--- Starting Test for chat_id: {chat_id} ---")

    # --- First Message ---
    print("\n[1] Sending first message...")
    message1 = {
        "chat_id": chat_id,
        "message": "My name is Jules. What is your name?"
    }
    try:
        async with httpx.AsyncClient() as client:
            response1 = await client.post(f"{BASE_URL}/agent/chat", json=message1, timeout=10)
            response1.raise_for_status() # Raise an exception for bad status codes

            response_data1 = response1.json()
            print(f"Status Code: {response1.status_code}")
            print(f"Response: {response_data1}")

            # Basic check on the response content
            assert "Размышляю" in response_data1.get("response", "")
            assert message1["message"] in response_data1.get("response", "")

    except httpx.RequestError as e:
        print(f"ERROR: An error occurred while requesting {e.request.url!r}.")
        print("Please ensure the FastAPI server is running on localhost:8000.")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    print("\n[1] First message test PASSED.")


    # --- Second Message ---
    print("\n[2] Sending second message to test memory...")
    message2 = {
        "chat_id": chat_id,
        "message": "Do you remember my name?"
    }
    try:
        async with httpx.AsyncClient() as client:
            response2 = await client.post(f"{BASE_URL}/agent/chat", json=message2, timeout=10)
            response2.raise_for_status()

            response_data2 = response2.json()
            print(f"Status Code: {response2.status_code}")
            print(f"Response: {response_data2}")

            # The placeholder response should now include the second message
            assert "Размышляю" in response_data2.get("response", "")
            assert message2["message"] in response_data2.get("response", "")

    except httpx.RequestError as e:
        print(f"ERROR: An error occurred while requesting {e.request.url!r}.")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    print("\n[2] Second message test PASSED.")
    print(f"\n--- Test for chat_id: {chat_id} COMPLETED SUCCESSFULLY ---")


if __name__ == "__main__":
    print("Running API test script...")
    print("NOTE: This script requires the main FastAPI application to be running.")
    print("You can start it with: uvicorn main:app --reload")
    asyncio.run(run_test())
