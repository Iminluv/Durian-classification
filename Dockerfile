FROM python:3.11-slim

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and files
COPY workflow_app/ ./workflow_app/
COPY run_workflow.py .
COPY durian/test/ ./durian/test/

# Create directories for outputs and uploads
RUN mkdir -p output_images uploads/images uploads/labels && chmod -R 777 output_images uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CLOUD_MODE=true

# Expose port 7860 (Hugging Face Spaces default)
EXPOSE 7860

# Run uvicorn server on port 7860
CMD ["uvicorn", "workflow_app.app:app", "--host", "0.0.0.0", "--port", "7860"]
