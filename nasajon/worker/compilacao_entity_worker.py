import inspect
import json
import uuid

from rq import get_current_job

from nsj_rest_lib.dao.dao_base import DAOBase
from nsj_rest_lib.service.service_base import ServiceBase
from nsj_rest_lib.util.db_adapter2 import DBAdapter2

from nsj_rest_lib2.compiler.compiler import EDLCompiler
from nsj_rest_lib2.compiler.edl_model.entity_model import EntityModel
from nsj_rest_lib2.compiler.edl_model.entity_model_base import EntityModelBase
from nsj_rest_lib2.dto.escopo_dto import EscopoDTO
from nsj_rest_lib2.entity.escopo_entity import EscopoEntity
from nsj_rest_lib2.service.entity_config_writer import EntityConfigWriter

from nasajon.dto.entity_dto import EntityDTO, StatusEntityEnum
from nasajon.entity.entity_entity import EntityEntity
from nasajon.injector_factory import InjectorFactory
from nasajon.settings import logger


def compilar_entity(entity_dto: EntityDTO):
    logger.debug(f"Iniciando compilação de entidade.")

    try:
        escopo_codigo = entity_dto.escopo
        codigo_entity = entity_dto.codigo
        edl_hash = entity_dto.content_hash
        tenant = entity_dto.tenant
        grupo_empresarial = entity_dto.grupo_empresarial

        logger.debug(f"Compilando Entity {codigo_entity}, e salvando no Redis.")

        # Recuperando as dependências diretas do modelo (e já convertendo para o objeto de compilação)
        compiler = EDLCompiler()

        # Recuperando, recursivamente, as dependências do banco de dados
        with InjectorFactory() as injector:
            db_adapter = injector.db_adapter()

            edl_service = ServiceBase.construtor1(
                db_adapter=db_adapter,
                dao=DAOBase(db=db_adapter, entity_class=EntityEntity),
                dto_class=EntityDTO,
                entity_class=EntityEntity,
            )

            escopo_service = ServiceBase.construtor1(
                db_adapter=db_adapter,
                dao=DAOBase(db=db_adapter, entity_class=EscopoEntity),
                dto_class=EscopoDTO,
                entity_class=EscopoEntity,
            )

            dependencies, entity_model = retrieve_dependencies(
                db_adapter, entity_dto, compiler, edl_service, tenant, grupo_empresarial
            )

            escopo_dto = retrieve_escopo(
                escopo_service=escopo_service, escopo_codigo=escopo_codigo
            )

        # Compilando o EDL
        compiler_result = compiler.compile_model(
            entity_model, dependencies, escopo=escopo_dto
        )

        # Se retornou None, é porque é um mixin, e não deve ser compilado
        if compiler_result is None:
            msg = f"Entity '{codigo_entity}' é um mixin, e não será compilada."
            logger.debug(msg)
            return msg

        writer = EntityConfigWriter(escopo=escopo_dto.codigo)
        entity_config = writer.publish(
            entity_model, compiler_result, entity_hash=edl_hash
        )

        # Serializando em json para o retorno/log
        entity_config_str = json.dumps(
            entity_config, sort_keys=True, ensure_ascii=True, indent=4
        )

        # TODO Atualizando o status no BD

        return entity_config_str
    except Exception as e:
        error_msg = f"Erro ao compilar Entity {entity_dto.id}: {e}"
        logger.exception(
            error_msg,
            exc_info=True,
            stack_info=True,
        )

        job = get_current_job()
        if job:
            job.meta["error_code"] = "500"
            job.meta["error_message"] = error_msg
            job.meta["error_http_status"] = 500

        raise


def retrieve_dependencies(
    db_adapter: DBAdapter2,
    entity_dto: EntityDTO,
    compiler: EDLCompiler,
    edl_service: ServiceBase,
    tenant: int,
    grupo_empresarial: uuid.UUID,
    deepth: int = 0,
) -> tuple[list[tuple[str, EntityModelBase]], EntityModelBase]:

    dependencies = []

    if deepth <= 0 or entity_dto.status == StatusEntityEnum.ATIVO:
        dependencies_list_str, entity_model = compiler.list_dependencies(
            entity_dto.json_schema
        )
    else:
        dependencies_list_str, entity_model = compiler.list_dependencies(
            entity_dto.json_schema_old
        )

    if deepth > 0:
        dependencies.append([f"{entity_dto.escopo}/{entity_dto.codigo}", entity_model])

    for dependency_str in dependencies_list_str:
        parts = dependency_str.split("/")
        escopo = parts[0]
        codigo = parts[1]

        dependencies_dto = edl_service.list(
            after=None,
            limit=None,
            fields={"root": set(["json_schema", "json_schema_old"])},
            order_fields=None,
            filters={
                "escopo": escopo,
                "codigo": codigo,
                "tenant": tenant,
                "grupo_empresarial": grupo_empresarial,
            },
        )

        if not dependencies_dto or len(dependencies_dto) <= 0:
            raise RuntimeError(
                f"Não encontrado entidade com o código, escopo, tenant e grupo empresarial: {codigo}, {escopo}, {tenant}, {grupo_empresarial}"
            )

        if len(dependencies_dto) > 1:
            raise RuntimeError(
                f"Encontrado mais de uma entidade com o mesmo código, escopo, tenant e grupo empresarial: {codigo}, {escopo}, {tenant}, {grupo_empresarial}"
            )

        sub_dependencies, _ = retrieve_dependencies(
            db_adapter,
            dependencies_dto[0],
            compiler,
            edl_service,
            tenant,
            grupo_empresarial,
            deepth + 1,
        )

        dependencies.extend(sub_dependencies)

    if deepth > 0:
        return (dependencies, None)
    else:
        return (dependencies, entity_model)


def retrieve_escopo(escopo_service: ServiceBase, escopo_codigo: str) -> EscopoDTO:
    escopo_list = escopo_service.list(
        after=None,
        limit=None,
        fields={"root": set(["id", "codigo", "service_account"])},
        order_fields=None,
        filters={
            "codigo": escopo_codigo,
        },
    )

    if not escopo_list or len(escopo_list) <= 0:
        # raise RuntimeError(f"Escopo não encontrado: {escopo_codigo}")
        return EscopoDTO(codigo=escopo_codigo)

    if len(escopo_list) > 1:
        raise RuntimeError(
            f"Encontrado mais de um escopo com o código: {escopo_codigo}"
        )

    return escopo_list[0]


if __name__ == "__main__":
    import redis
    from rq import Worker, Queue

    # Configura tua conexão Redis e o nome da fila
    redis_conn = redis.Redis(host="localhost", port=6379, db=0)
    queue_name = "queue_compilacao_entity"

    # Cria a fila explicitando a conexão
    q = Queue(queue_name, connection=redis_conn)

    # Cria o worker e roda com o scheduler habilitado
    worker = Worker([q], connection=redis_conn)
    worker.work(with_scheduler=True)
