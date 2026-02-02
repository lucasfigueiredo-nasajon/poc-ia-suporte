import json
import hashlib
import uuid

from flask import request
from rq import Retry

from nsj_rest_lib.dto.after_insert_update_data import AfterInsertUpdateData
from nsj_rest_lib.dto.queued_data_dto import QueuedDataDTO

from nasajon.dto.entity_dto import EntityDTO
from nasajon.redis_config import compilacao_queue
from nasajon.settings import (
    logger,
    APP_NAME,
    WORKER_COMPILACAO_FAILURE_TTL,
    WORKER_COMPILACAO_RETRY_MAX,
    WORKER_COMPILACAO_RETRY_INTERVALS,
    WORKER_COMPILACAO_TIMEOUT,
    WORKER_COMPILACAO_TTL,
)
from nasajon.worker.compilacao_entity_worker import compilar_entity


class EntityCustomService:
    def __init__(self):
        super().__init__()

    @staticmethod
    def enfileirar_compilacao(entity_dto: EntityDTO) -> QueuedDataDTO:

        job_id = uuid.uuid4()
        job_id_str = str(job_id)
        job_description = f"Compilação da entidade: {entity_dto.escopo}.{entity_dto.codigo} (tenant: {entity_dto.tenant}, grupo_empresarial: {entity_dto.grupo_empresarial})"

        job = compilacao_queue.enqueue(
            compilar_entity,
            entity_dto,
            job_timeout=WORKER_COMPILACAO_TIMEOUT,
            result_ttl=WORKER_COMPILACAO_TTL,
            failure_ttl=WORKER_COMPILACAO_FAILURE_TTL,
            retry=Retry(
                max=WORKER_COMPILACAO_RETRY_MAX,
                interval=WORKER_COMPILACAO_RETRY_INTERVALS,
            ),
            job_id=job_id_str,
            description=job_description,
        )

        logger.info(
            f"Enfileirado job {job.id} para compilar Entity {entity_dto.codigo}."
        )

        return QueuedDataDTO(
            f"{request.host_url}{APP_NAME}/entity-compilations/status/{job_id_str}"
        )

    @staticmethod
    def before_insert_entity(db, new_dto: EntityDTO):
        edl_new = new_dto.json_schema
        edl_new_str = json.dumps(edl_new, sort_keys=True, ensure_ascii=True, indent=4)
        edl_new_hash = hashlib.sha256(edl_new_str.encode("utf-8")).hexdigest()
        new_dto.content_hash = edl_new_hash
        return new_dto

    @staticmethod
    def after_insert_entity(
        db, new_dto: EntityDTO, after_data: AfterInsertUpdateData
    ) -> QueuedDataDTO | None:
        return EntityCustomService.enfileirar_compilacao(new_dto)

    @staticmethod
    def before_update_entity(db, old_dto: EntityDTO, new_dto: EntityDTO):
        EntityCustomService.before_insert_entity(db, new_dto)
        new_dto.json_schema_old = old_dto.json_schema
        return new_dto

    @staticmethod
    def after_update_entity(
        db, old_dto: EntityDTO, new_dto: EntityDTO, after_data: AfterInsertUpdateData
    ) -> QueuedDataDTO | None:
        if new_dto.content_hash != old_dto.content_hash:
            return EntityCustomService.enfileirar_compilacao(new_dto)
