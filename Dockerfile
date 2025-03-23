# Use an official lightweight Python image.
FROM python:3.9-slim

# Set environment variables to prevent Python from writing .pyc files
# and to enable unbuffered output.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create and set the working directory inside the container
WORKDIR /app

# Install system dependencies and OpenCV dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (alternatively, you can use a requirements.txt file)
RUN pip install flask opencv-python-headless numpy

# Copy the image processing application code and templates into the container
COPY image_processing.py /app/image_processing.py
COPY templates /app/templates

# Expose port 5000 so that the container is accessible on that port
EXPOSE 5000

# Set the entrypoint to run the Flask app
CMD ["python", "image_processing.py"]


