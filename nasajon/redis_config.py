import os

from redis import Redis
from rq import Queue
from typing import Any

REDIS_URL = os.environ["REDIS_URL"]
REDIS_QUEUE_COMPILACAO_ENTITY = os.getenv(
    "REDIS_QUEUE_COMPILACAO_ENTITY", "queue_compilacao_entity"
)

redis_client = Redis.from_url(REDIS_URL)
compilacao_queue = Queue(REDIS_QUEUE_COMPILACAO_ENTITY, connection=redis_client)


def k(*parts: str) -> str:
    return ":".join(parts)


def get_redis(*args: str) -> Any:
    value = redis_client.get(k(*args))
    if value:
        return value.decode("utf-8")
    return None


def set_redis(*args) -> None:
    value = args[-1]
    redis_client.set(k(*args[:-1]), value)


if __name__ == "__main__":
    set_redis("ping", "pong")
    print(get_redis(("ping")))
