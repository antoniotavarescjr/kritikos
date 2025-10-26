from src.etl.coleta_referencia import ColetorDadosCamara
from models.db_utils import get_db_session

db = get_db_session()
coletor = ColetorDadosCamara()
coletor.config['deputados']['limite_total'] = 5
result = coletor.buscar_e_salvar_deputados(db)
print(f'Deputados validados: {result}')
db.close()
