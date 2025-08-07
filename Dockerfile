# Base Image
FROM python:3.11-slim

# Working Directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Expose the port
EXPOSE 5000

# Command to run the app
CMD ["python", "app.py"]
