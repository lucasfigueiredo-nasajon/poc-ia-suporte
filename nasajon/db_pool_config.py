from nasajon.settings import DATABASE_HOST
from nasajon.settings import DATABASE_PASS
from nasajon.settings import DATABASE_PORT
from nasajon.settings import DATABASE_NAME
from nasajon.settings import DATABASE_USER
from nasajon.settings import DATABASE_DRIVER

import sqlalchemy
# Importação explícita para evitar erros de versão
from sqlalchemy.engine import URL 

def create_url(
    username: str,
    password: str,
    host: str,
    port: str,
    database: str,
    db_dialect: str = "postgresql+pg8000",
):
    # CORREÇÃO: Adicionado o 'return'
    return URL.create(
        drivername=db_dialect,
        username=username,
        password=password,
        host=host,
        port=int(port), # Garante que porta seja inteiro
        database=database,
    )


def create_pool(database_conn_url):
    # Creating database connection pool
    db_pool = sqlalchemy.create_engine(
        database_conn_url,
        # Configurações comentadas mantidas como no original
        # pool_size=5,
        # max_overflow=2,
        # pool_timeout=30,
        # pool_recycle=1800,
        poolclass=sqlalchemy.pool.NullPool,
    )
    return db_pool


if DATABASE_DRIVER.upper() in ["SINGLE_STORE", "MYSQL"]:
    db_dialect = "mysql+pymysql"
else:
    # Nota: Certifique-se de ter 'pg8000' instalado (pip install pg8000)
    # Se der erro de driver, mude para "postgresql" (que usa psycopg2)
    db_dialect = "postgresql+pg8000"

database_conn_url = create_url(
    username=DATABASE_USER,
    password=DATABASE_PASS,
    host=DATABASE_HOST,
    port=DATABASE_PORT,
    database=DATABASE_NAME,
    db_dialect=db_dialect,
)

db_pool = create_pool(database_conn_url)