from src.etl.coleta_remuneracao import ColetorRemuneracao
from models.db_utils import get_db_session

db = get_db_session()
coletor = ColetorRemuneracao()
result = coletor.coletar_remuneracoes_periodo(2025, [10], db)
print(f'Remuneração validada: {result}')
db.close()
