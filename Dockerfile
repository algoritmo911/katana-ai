# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application code into the container
# We copy the entire katana directory because the agent needs access to it as a module
COPY katana/ /app/katana/
COPY run_praetor.py /app/

# Install any needed packages specified in requirements.txt
# Note: We use the requirements file from the katana directory
RUN pip install --no-cache-dir -r /app/katana/requirements.txt

# Define environment variables (placeholders, to be set in docker-compose.yml)
ENV SUPABASE_URL=""
ENV SUPABASE_KEY=""
ENV PRAETOR_TELEGRAM_TOKEN=""
ENV PRAETOR_ADMIN_CHAT_ID=""
ENV KATANA_API_URL="http://katana-bot:8080/healthcheck"

# Run run_praetor.py when the container launches
CMD ["python", "run_praetor.py"]
