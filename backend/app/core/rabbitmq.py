"""
Module to handle RabbitMQ message consumption and processing. This
module exists during the lifespan of the application and is responsible
for listening to messages from the RabbitMQ queue (new segments).
"""

import json
import threading
import time

import pika
from app.config import settings
from app.core.logging import configure_logging
from app.services.record_service import process_new_recording

logger = configure_logging(__name__)


def _on_message(ch, method, _properties, body):
    logger.debug("Received message: `%s`", body)
    try:
        payload = json.loads(body)

        # Business logic; may want to be decoupled in the future
        filename = payload.get("filename")
        timestamp = payload.get("timestamp", {})
        process_new_recording(filename, timestamp)

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Processing error: %s", e)
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


def _rabbitmq_consumer(stop_event: threading.Event):
    """
    RabbitMQ consumer that listens for messages on a specified queue.
    The consumer forwards messages to the `_on_message` function for
    processing.
    """
    while not stop_event.is_set():
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=settings.RABBITMQ_HOST, heartbeat=600)
            )
            channel = connection.channel()
            channel.exchange_declare(
                exchange=settings.RABBITMQ_EXCHANGE,
                exchange_type="direct",
                durable=True,
            )
            channel.queue_declare(queue=settings.RABBITMQ_QUEUE, durable=True)
            channel.queue_bind(
                exchange=settings.RABBITMQ_EXCHANGE, queue=settings.RABBITMQ_QUEUE
            )
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=settings.RABBITMQ_QUEUE,
                on_message_callback=_on_message,
                auto_ack=False,
            )
            logger.info("RabbitMQ consumer connected. Waiting for messages...")
            channel.start_consuming()
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Connection error: `%s`. Retrying in 5 seconds...", e)
            time.sleep(5)
        finally:
            try:
                connection.close()
            except Exception:  # pylint: disable=broad-except
                pass


def start_consumer_thread():
    """
    Start the RabbitMQ consumer thread. Runs in the background and can
    be stopped by setting the `stop_event`.
    """
    stop_event = threading.Event()
    consumer_thread = threading.Thread(
        target=_rabbitmq_consumer, args=(stop_event), daemon=False
    )
    consumer_thread.start()
    logger.info("Started RabbitMQ consumer thread.")
    return stop_event, consumer_thread
