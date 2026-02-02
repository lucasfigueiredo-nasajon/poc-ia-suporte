import datetime
import uuid

from nasajon.dto.message_dto import MessageDTO

from nsj_rest_lib.decorator.dto import DTO
from nsj_rest_lib.descriptor.dto_one_to_one_field import (
    DTOOneToOneField,
    OTORelationType,
)
from nsj_rest_lib.descriptor.dto_field import DTOField
from nsj_rest_lib.descriptor.dto_list_field import DTOListField
from nsj_rest_lib.dto.dto_base import DTOBase


@DTO()
class ChatPostDTO(DTOBase):

    message: MessageDTO = DTOOneToOneField(
        not_null=True,
        entity_type=MessageDTO,
        relation_type=OTORelationType.COMPOSITION,
    )

    tenant: int = DTOField(
        resume=True,
        not_null=True,
        # partition_data=True,
        unique="escopo_tenant_grupo_codigo",
    )

    area_atendimento: uuid.UUID = DTOField(
        resume=True,
        not_null=True,
    )

    created_at: datetime.datetime = DTOField(
        resume=True,
        not_null=True,
        default_value=datetime.datetime.now,
    )

    history: list = DTOListField(
        not_null=True,
        dto_type=MessageDTO,
    )
