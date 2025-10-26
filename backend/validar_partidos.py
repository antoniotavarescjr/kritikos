from src.etl.coleta_referencia import ColetorDadosCamara
from models.db_utils import get_db_session

db = get_db_session()
coletor = ColetorDadosCamara()
result = coletor.buscar_e_salvar_partidos(db)
print(f'Partidos validados: {result}')
db.close()
