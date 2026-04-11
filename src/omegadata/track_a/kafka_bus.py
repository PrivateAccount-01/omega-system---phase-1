from __future__ import annotations

from confluent_kafka import Consumer, Producer

from omegadata.config import settings


class KafkaBus:
    def __init__(self) -> None:
        self.bootstrap = settings.kafka_bootstrap

    def producer(self) -> Producer:
        return Producer({"bootstrap.servers": self.bootstrap})

    def consumer(self, topic: str, group_id: str) -> Consumer:
        consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        consumer.subscribe([topic])
        return consumer
