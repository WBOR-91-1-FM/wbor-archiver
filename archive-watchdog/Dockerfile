FROM python:3.12

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Working directory in the container
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
# (Done after installing dependencies to avoid re-installing dependencies on every code change)
COPY . .

# Run the recording service
CMD ["python", "file_watchdog.py"]
