from src.etl.coleta_referencia import ColetorDadosCamara
from models.db_utils import get_db_session

db = get_db_session()
coletor = ColetorDadosCamara()
result = coletor.buscar_e_salvar_gastos(db, meses_historico=1)
print(f'Gastos validados: {result}')
db.close()
