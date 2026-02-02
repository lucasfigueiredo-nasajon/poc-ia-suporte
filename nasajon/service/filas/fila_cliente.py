
import uuid
from nsj_queue_lib.queue_client import QueueClient
from nsj_queue_lib.settings import (QUEUE_TABLE)

class FilaCliente(QueueClient):

    _origem: str = 'teste.cliente'
    _destino: str = 'faturamento.pessoa'
    _processo: str = 'sinc_faturamento_pessoas'

    def __init__(
        self,
        bd_conn
    ) -> None:
      super().__init__(bd_conn, QUEUE_TABLE)

    def enfileira(self, cliente: uuid.UUID):
        self._insert_task(
            self._origem,
            self._destino,
            self._processo,
            None,
            str(cliente),
            pub_sub=True
        )
