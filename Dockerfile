# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY ./alg911.catana-ai/requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir makes the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire agent source code into the container at /app
COPY ./alg911.catana-ai .

# Set a default agent ID, which can be overridden at runtime.
# This will be crucial for giving each agent a unique identity.
ENV AGENT_ID="default_agent"

# Define the command to run the application
# This will execute the main control loop when the container starts.
CMD ["python3", "katana_mcp.py"]
