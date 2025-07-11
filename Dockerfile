# Base image with Python and essential libraries
FROM python:3.8-slim

# Install system-level dependencies
RUN apt-get update && \
    apt-get install -y espeak && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy your files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 7860

# Run your app
CMD ["python", "app.py"]