import datetime
import enum

from nsj_rest_lib.decorator.dto import DTO
from nsj_rest_lib.descriptor.dto_field import DTOField
from nsj_rest_lib.dto.dto_base import DTOBase


class RoleEnum(str, enum.Enum):
    USER = "user"
    AGENT = "agent"


@DTO()
class MessageDTO(DTOBase):

    text: str = DTOField(
        resume=True,
        not_null=True,
        strip=True,
        min=1,
        max=1024,
    )

    role: RoleEnum = DTOField(
        resume=True,
        not_null=True,
    )

    created_at: datetime.datetime = DTOField(
        resume=True, not_null=True, default_value=datetime.datetime.now
    )
