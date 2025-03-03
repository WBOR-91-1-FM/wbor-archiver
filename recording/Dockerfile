FROM python:3.12

# Set the environment variable so tzdata won't prompt for input
ENV DEBIAN_FRONTEND=noninteractive

# Install ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Working directory in the container
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
# (Done after installing dependencies to avoid re-installing dependencies on every code change)
COPY . .

# Run the recording service
CMD ["python", "recording_driver.py"]