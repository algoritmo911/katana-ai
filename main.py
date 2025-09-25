import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import telebot
from strategist import decide_coder # Import the new strategist function

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- Initialize clients ---
app = FastAPI(title="Swarm Dispatcher API")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Successfully connected to Supabase.")
except Exception as e:
    print(f"Error connecting to Supabase: {e}")
    supabase = None

try:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    print("Telegram bot initialized.")
except Exception as e:
    print(f"Error initializing Telegram bot: {e}")
    bot = None

# --- Pydantic Models ---
class TaskCreate(BaseModel):
    task_description: str
    repo_url: str

# --- API Endpoint ---
@app.post("/create_task")
def create_task(task: TaskCreate):
    """
    Receives a task, saves it to Supabase, assigns the first available coder,
    and sends a notification via Telegram.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized.")
    if not bot:
        raise HTTPException(status_code=500, detail="Telegram bot not initialized.")

    # 1. Insert the task into the 'tasks' table
    try:
        print(f"Inserting task: {task.task_description}")
        task_data = {
            'description': task.task_description,
            'repo_url': task.repo_url,
            'status': 'new'
        }
        insert_res = supabase.table('tasks').insert(task_data).execute()

        if not insert_res.data:
            raise HTTPException(status_code=500, detail="Failed to insert task into Supabase.")

        new_task_id = insert_res.data[0]['id']
        print(f"Task created with ID: {new_task_id}")

    except Exception as e:
        print(f"Error inserting task: {e}")
        raise HTTPException(status_code=500, detail=f"Database error during task insertion: {e}")

    # 2. Let the strategist decide which coder to assign
    coder_id = decide_coder(supabase)

    if not coder_id:
        print("Strategist could not decide on a coder. Task will be unassigned.")
        return {"message": "Task created but no available coders to assign.", "task_id": new_task_id}

    print(f"Strategist has chosen Coder ID: {coder_id}")

    # Fetch the chosen coder's details for notification
    try:
        coder_details_res = supabase.table('coders').select('telegram_id').eq('id', coder_id).single().execute()
        coder_telegram_id = coder_details_res.data.get('telegram_id') if coder_details_res.data else None
    except Exception as e:
        print(f"Warning: Could not fetch details for coder {coder_id}. {e}")
        coder_telegram_id = None

    # 3. Assign the coder to the task
    try:
        print(f"Assigning coder {coder_id} to task {new_task_id}...")
        update_res = supabase.table('tasks').update({'coder_id': coder_id}).eq('id', new_task_id).execute()

        if not update_res.data:
             # Log the error but don't fail the request, notification is best-effort
            print(f"Warning: Failed to update task {new_task_id} with coder_id {coder_id}.")

    except Exception as e:
        # Log the error but proceed to notification if possible
        print(f"Warning: Database error during task assignment: {e}")

    # 4. Send a notification to the coder via Telegram
    if coder_telegram_id:
        try:
            message = (
                f"Назначена задача #{new_task_id}: {task.task_description}.\n"
                f"Репозиторий: {task.repo_url}"
            )
            print(f"Sending Telegram message to {coder_telegram_id}...")
            bot.send_message(coder_telegram_id, message)
            print("Telegram message sent.")
        except Exception as e:
            # If Telegram fails, the core task is still done. Log it.
            print(f"Warning: Failed to send Telegram notification to {coder_telegram_id}: {e}")
    else:
        print(f"Warning: Coder {coder_id} has no telegram_id. Cannot send notification.")


    return {
        "message": "Task created and assigned successfully.",
        "task_id": new_task_id,
        "assigned_coder_id": coder_id
    }

if __name__ == "__main__":
    import uvicorn
    # This will run the FastAPI app on http://127.0.0.1:8000
    # The .env file must be present in the same directory.
    print("Starting Swarm Dispatcher API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)