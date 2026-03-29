"""All the order related dependencies"""

from typing import Annotated

from fastapi import Depends

from src.app.infrastructure.database.session import DbSession
from src.app.infrastructure.kafka.producer import get_kafka_producer
from src.app.infrastructure.redis.redis import redis_manager
from src.app.repositories.orders.order_creation_repository import OrderCreationRepository
from src.app.services.orders.order_service import OrderService


def get_order_service(session: DbSession) -> OrderService:
    repo = OrderCreationRepository(session)

    return OrderService(
        order_creation_repo=repo,
        redis_manager=redis_manager,
        kafka_producer=get_kafka_producer(),
    )


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
