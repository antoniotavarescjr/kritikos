from src.etl.coleta_emendas import ColetorEmendas
from models.db_utils import get_db_session

db = get_db_session()
coletor = ColetorEmendas()
# Coletar emendas de 2025 (incluindo EMC que funcionam)
tipos_emenda = ['EMD', 'EMP', 'EMC']  # Incluir EMC
result = coletor.coletar_emendas_periodo(2025, tipos_emenda, db)
print(f'Emendas validadas: {result}')
db.close()
