FROM python:3.12

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Port passed in as a build argument and set it as an environment variable.
ARG BACKEND_PORT
ENV BACKEND_PORT=${BACKEND_PORT}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE $BACKEND_PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT"]
