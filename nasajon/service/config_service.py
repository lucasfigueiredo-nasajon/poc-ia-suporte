from nasajon.dao.config_dao import ConfigDAO

class ConfigService:
    def __init__(self, config_dao: ConfigDAO):
        self.dao = config_dao

    def get_thresholds(self):
        # Tenta pegar do banco, se falhar ou estiver vazio, usa o padrão seguro
        data = self.dao.get_config('thresholds')
        if not data:
            return {"sniper": 0.88, "high": 0.85, "low": 0.60}
        return data

    def update_thresholds(self, sniper: float, high: float, low: float):
        # Regra de Negócio: Validação de consistência
        # Sniper deve ser o maior, Low o menor.
        if not (0 <= low < high < sniper <= 1.0):
            raise ValueError("Hierarquia de Thresholds inválida. Regra obrigatória: 0 <= Low < High < Sniper <= 1")

        payload = {
            "sniper": sniper,
            "high": high,
            "low": low
        }
        return self.dao.update_config('thresholds', payload)