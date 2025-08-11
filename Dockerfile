# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy the dependency files to leverage Docker's layer caching
COPY pyproject.toml poetry.lock ./

# Install project dependencies
RUN poetry install --no-interaction --no-ansi

# Copy the rest of the application code
COPY . .

# Command to run the application
# We don't have an entrypoint yet, so we'll just keep the container running.
CMD ["tail", "-f", "/dev/null"]
