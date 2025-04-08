"""
RabbitMQ consumer for processing messages from RabbitMQ.
"""

import json
import logging
import os
import sys
import threading
import time

import pika
from models import Segment
from utils.ffprobe import probe as get_ffprobe_output
from utils.hash import hash_file

from database import SessionLocal

logger = logging.getLogger(__name__)

try:
    # RabbitMQ configuration (these are passed in docker-compose.yml)
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST").strip()
    RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE").strip()
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE").strip()
except (ValueError, AttributeError, TypeError) as e:
    logger.error("Failed to load RabbitMQ environment variables: `%s`", e)
    sys.exit(1)


def _on_message(ch, method, _properties, body, archive_base):
    """
    Handle messages received from RabbitMQ.
    Note: archive_base is passed in to avoid using global state.
    """
    logger.debug("Received message from RabbitMQ with payload: %s", body)
    try:
        payload = json.loads(body)
        filename = payload.get("filename")
        timestamp = payload.get("timestamp", {})
        year = timestamp.get("year")
        month = timestamp.get("month")
        day = timestamp.get("day")
        hour = timestamp.get("hour")
        minute = timestamp.get("minute")
        second = timestamp.get("second")

        # Check that the filename matches the expected pattern
        expected = f"WBOR-{year}-{month}-{day}T{hour}:{minute}:{second}Z.mp3"
        if filename != expected:
            logger.error("Filename does not match expected format: %s", filename)
            return

        logger.info(
            "New file: WBOR-%s-%s-%sT%s:%s:%sZ", year, month, day, hour, minute, second
        )

        file_path = archive_base / year / month / day / filename
        sha256_hash = hash_file(str(file_path))
        ffprobe = get_ffprobe_output(str(file_path))

        db = SessionLocal()
        try:
            new_rec = Segment(
                filename=filename,
                archived_path=str(file_path),
                start_ts=timestamp,
                # end_ts=,
                sha256_hash=sha256_hash,
                bit_rate=ffprobe.get("bit_rate"),
                sample_rate=ffprobe.get("sample_rate"),
                icy_br=ffprobe.get("icy_br"),
                icy_genre=ffprobe.get("icy_genre"),
                icy_name=ffprobe.get("icy_name"),
                icy_url=ffprobe.get("icy_url"),
                encoder=ffprobe.get("encoder"),
            )
            db.add(new_rec)
            db.commit()
        except Exception as e:  # pylint: disable=broad-except
            db.rollback()
            logger.error("Error inserting record: %s", e)
        finally:
            db.close()

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Failed to process message: %s", e)
    finally:
        # NOTE: `finally` runs even if an exception is raised
        # Acknowledge the message, regardless of success/failure
        ch.basic_ack(delivery_tag=method.delivery_tag)


def _rabbitmq_consumer(stop_event: threading.Event, archive_base):
    """
    Connect to RabbitMQ and consume messages until stop_event is set.
    """
    while not stop_event.is_set():
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600)
            )
            channel = connection.channel()
            channel.exchange_declare(
                exchange=RABBITMQ_EXCHANGE, exchange_type="direct", durable=True
            )
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            channel.queue_bind(exchange=RABBITMQ_EXCHANGE, queue=RABBITMQ_QUEUE)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=lambda ch, method, props, body: _on_message(
                    ch, method, props, body, archive_base
                ),
                auto_ack=False,
            )

            logger.info("RabbitMQ consumer connected. Waiting for messages...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error("RabbitMQ connection error: %s. Retrying in 5 seconds...", e)
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info(
                "RabbitMQ consumer interrupted via KeyboardInterrupt; stopping."
            )
            break
        finally:
            try:
                connection.close()
            except Exception:  # pylint: disable=broad-except
                pass


def start_consumer_thread(archive_base):
    """
    Creates and returns a stop event and thread running the RabbitMQ consumer.
    The caller is responsible for stopping the consumer thread.
    """
    stop_event = threading.Event()
    consumer_thread = threading.Thread(
        target=_rabbitmq_consumer, args=(stop_event, archive_base), daemon=False
    )
    consumer_thread.start()
    logger.info("Started RabbitMQ consumer thread.")
    return stop_event, consumer_thread
