# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# This includes the 'data' folder with your vector store
COPY . .

# Set environment variables
ENV ENVIRONMENT=production
ENV PORT=8080

# Run the web service on container startup.
# 0.0.0.0 + reading $PORT from the environment is required by Render (see
# render.yaml) - it assigns and injects the port at runtime.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}