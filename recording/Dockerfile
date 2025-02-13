FROM python:3.12

# Set the environment variable so tzdata won't prompt for input
ENV DEBIAN_FRONTEND=noninteractive

# Install tzdata and ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Optionally set a default TZ in the Dockerfile (you can override it later)
ENV TZ=America/New_York

# Symlink the container's localtime to the TZ value
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Working directory in the container
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
# (Done after installing dependencies to avoid re-installing dependencies on every code change)
COPY . .

# Copy healthcheck script and make it executable
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Run the recording service
CMD ["python", "driver.py"]