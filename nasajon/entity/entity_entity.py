import datetime
import uuid

from nsj_rest_lib.entity.entity_base import EntityBase
from nsj_rest_lib.decorator.entity import Entity


@Entity(
    table_name="restlib2.entity",
    pk_field="id",
    default_order_fields=["escopo", "codigo", "id"],
)
class EntityEntity(EntityBase):
    id: uuid.UUID = None
    tenant: int = None
    grupo_empresarial: uuid.UUID = None
    escopo: str = None
    codigo: str = None
    descricao: str = None
    json_schema: dict = None
    json_schema_old: dict = None
    content_hash: str = None
    created_at: datetime.datetime = None
    status: str = None
