from nsj_multi_database_lib.injector_factory import InjectorFactory
from nasajon.settings import ENV


class InjectorFactoryMultibanco(InjectorFactory):
    def __init__(self) -> None:
        super().__init__(
            use_external_db=(ENV == "piloto" or ENV == "production" or ENV == "homol"),
            use_external_db_with_default_credentials=(
                ENV != "piloto"
                and ENV != "production"
                and ENV != "homol"
                and ENV != "local"
            ),
        )
