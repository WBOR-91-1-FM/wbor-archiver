"""
Client for sending messages to RabbitMQ over a persistent connection.
"""

import json
import os
import sys
import logging
import pika
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d in %(funcName)s()] - %(message)s",
)

logging.getLogger("pika").setLevel(logging.WARNING)

# Load environment variables from .env file if present
load_dotenv()

try:
    # RabbitMQ configuration - passed in from docker-compose.yml
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST").strip()
    RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE").strip()
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE").strip()
except (ValueError, AttributeError, TypeError) as e:
    logging.error("Failed to load environment variables: `%s`", e)
    sys.exit(1)


class RabbitMQClient:
    """Handles a persistent connection to RabbitMQ for sending messages."""

    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        """Establish a persistent connection to RabbitMQ."""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    heartbeat=600,
                )
            )
            self.channel = self.connection.channel()

            # Ensure the exchange and queue are declared
            self.channel.exchange_declare(
                exchange=RABBITMQ_EXCHANGE, exchange_type="direct", durable=True
            )
            self.channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            self.channel.queue_bind(exchange=RABBITMQ_EXCHANGE, queue=RABBITMQ_QUEUE)

            logging.debug("RabbitMQ connection established.")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error("Failed to connect to RabbitMQ: `%s`", e)
            self.connection = None
            self.channel = None

    def send_message(self, payload):
        """
        Publish a message to RabbitMQ.

        Parameters:
        - payload: dict, the message to send
        """
        if not self.channel or self.connection.is_closed:
            logging.warning("RabbitMQ connection lost. Reconnecting...")
            self.connect()

        if self.channel:
            try:
                message = json.dumps(payload)
                self.channel.basic_publish(
                    exchange=RABBITMQ_EXCHANGE,
                    routing_key=RABBITMQ_QUEUE,
                    body=message,
                    properties=pika.BasicProperties(delivery_mode=2),
                )
                logging.info("Sent message to RabbitMQ: `%s`", message)
            except pika.exceptions.AMQPError as e:
                logging.error("Failed to send message to RabbitMQ: `%s`", e)

    def close(self):
        """Close the RabbitMQ connection gracefully."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.debug("RabbitMQ connection closed.")
