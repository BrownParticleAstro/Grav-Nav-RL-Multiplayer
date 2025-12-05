# Use a slim Python image to keep the container lightweight
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
# This is done in a separate step to leverage Docker's layer caching.
# Dependencies are only re-installed if requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the application will run on
# Cloud Run will provide PORT env var, default to 8080
EXPOSE 8080

# Command to run the application
# Cloud Run requires binding to PORT environment variable
CMD ["python", "start.py"]