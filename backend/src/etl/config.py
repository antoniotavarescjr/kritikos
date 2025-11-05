"""
Configurações do ETL de coleta de dados da Câmara dos Deputados
Este arquivo centraliza todas as configurações de limitação e parâmetros
para facilitar ajustes durante o hackathon e em produção.
"""

import os
from datetime import datetime
from typing import Dict, Any

# Configurações da API
API_CONFIG = {
    'base_url': 'https://dadosabertos.camara.leg.br/api/v2',
    'user_agent': 'KritikosETL/1.0 (Hackathon 2025)',
    'timeout': 15,
    'rate_limit_delay': 0.3,  # Reduzido para 0.3s para mais velocidade
    'max_retries': 3,
    'batch_size': 50  # Reduzido de 100 para 50 para processamento mais rápido
}

# Configurações do Google Cloud Storage
GCS_CONFIG = {
    'bucket_name': os.getenv('GCS_BUCKET_NAME', 'kritikos-emendas-prod'),
    'project_id': os.getenv('GCS_PROJECT_ID', 'kritikos-474618'),
    'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', './service-account-key.json'),
    'compress_files': True,  # Comprimir arquivos com gzip
    'cache_ttl_hours': 6,  # TTL para cache local
    'storage_class': 'Standard',  # Classe de armazenamento
    'location': 'southamerica-east1'  # Região (São Paulo)
}

# Configurações de coleta para Hackathon 2025
HACKATHON_CONFIG = {
    'ano_limite': 2025,  # Limitar coleta apenas a 2025
    'data_inicio_hackathon': '2025-07-01',  # Início do período do hackathon
    
    # Configurações de deputados
    'deputados': {
        'limite_total': 9999,  # Coletar todos os deputados
        'apenas_em_exercicio': True,
        'buscar_detalhes_completos': True,
        'periodo_inicio': '2025-07-01'  # Foco em dados recentes
    },
    
    # Configurações de gastos
    'gastos': {
        'meses_historico': 6,  # Apenas meses relevantes para hackathon
        'meses_para_coletar': [7, 8, 9, 10, 11, 12],  # Meses do hackathon em diante
        'limite_por_deputado': 200,  # Aumentar limite para capturar todos os gastos
        'valor_minimo': 0.01,  # Ignorar gastos muito pequenos
        'data_inicio': '2025-07-01'  # Início do período
    },
    
    # Configurações de proposições (HABILITADO - Integração Completa)
    'proposicoes': {
        'habilitado': True,  # HABILITADO - Integração com GCS
        'ano_coleta': 2025,  # Foco em dados de 2025
        'data_inicio': '2025-06-01',  # Período do hackathon
        'salvar_gcs': True,  # Garantir salvamento no storage
        'tipos_relevantes': ['PEC', 'PLP', 'PL', 'MPV', 'PLV', 'SUG'],
        'limite_deputados_api': 50,  # Limite para coleta por API
        'descricao': 'Proposições Legislativas com GCS'
    },
    
    # Configurações de votações (REMOVIDO - Evolução Futura)
    # MOVIDO PARA deprecated/ - será implementado em versão futura
    
    # Configurações de emendas (DESLIGADAS PARA FOCO EM DEPUTADOS)
    'emendas': {
        'habilitado': False,  # DESLIGADO - Foco em deputados primeiro
        'ano_coleta': 2025,
        'data_inicio': '2025-07-01',
        'limite_total': 0  # Desabilitado
    },
    
    # Configurações de partidos
    'partidos': {
        'apenas_ativos': True,
        'buscar_todos': False  # Limitar a partidos com deputados ativos
    }
}

# Configurações de deduplicação
DEDUPLICATION_CONFIG = {
    'estrategia': 'composite_key',  # 'composite_key' ou 'hash'
    'campos_unicos': {
        'deputados': ['api_camara_id', 'cpf'],
        'gastos': ['deputado_id', 'ano', 'mes', 'numero_documento', 'valor_liquido'],
        'proposicoes': ['api_camara_id'],
        'partidos': ['sigla']
    },
    'verificar_existencia': True,  # Sempre verificar se já existe antes de inserir
    'atualizar_existentes': True   # Atualizar registros existentes com dados mais recentes
}

# Configurações de logging
LOGGING_CONFIG = {
    'nivel': 'INFO',
    'mostrar_progresso': True,
    'detalhar_erros': True,
    'salvar_em_arquivo': False,
    'formato': '%(asctime)s - %(levelname)s - %(message)s'
}

# Configurações de performance
PERFORMANCE_CONFIG = {
    'usar_bulk_insert': True,
    'batch_commit_size': 50,
    'paralelizar_requisicoes': False,  # Manter False para não sobrecarregar API
    'cache_sessao': True,
    'timeout_por_lote': 300  # 5 minutos por lote
}

# Configurações de ambiente
AMBIENTE = 'hackathon'  # 'hackathon', 'desenvolvimento', 'producao'

# Configurações de Análise com Agents
ANALISE_CONFIG = {
    'limite_proposicoes': 10,  # Limite de proposições por execução (configurável)
    'habilitado': True,  # Habilitar/desabilitar análise
    'dias_para_reanalise': 7,  # Reanalisar após X dias
    'versao_analise': '1.0',  # Versão da metodologia
    'descricao': 'Análise de Proposições com Agents Kritikos',
    'tipos_prioritarios': ['PEC', 'PLP', 'PL', 'MPV'],  # Tipos com prioridade
    'ignorar_triviais': True,  # Ignorar proposições triviais em análises futuras
    'salvar_logs': True,  # Salvar logs detalhados de processamento
    'timeout_analise': 300,  # Timeout por proposição (segundos)
    'retry_attempts': 3  # Tentativas em caso de erro
}

def get_analise_config(chave: str = None) -> Any:
    """
    Obtém configurações de análise de forma centralizada
    
    Args:
        chave: Chave específica (opcional)
    
    Returns:
        Valor da configuração solicitada ou dicionário completo
    """
    if chave:
        return ANALISE_CONFIG.get(chave)
    
    return ANALISE_CONFIG

def get_limite_analise_proposicoes() -> int:
    """
    Retorna o limite configurado de proposições para análise
    
    Returns:
        int: Limite de proposições por execução
    """
    return ANALISE_CONFIG.get('limite_proposicoes', 10)

def analise_habilitada() -> bool:
    """
    Verifica se a análise com agents está habilitada
    
    Returns:
        bool: True se estiver habilitada
    """
    return ANALISE_CONFIG.get('habilitado', False)

def get_versao_analise() -> str:
    """
    Retorna a versão atual da análise
    
    Returns:
        str: Versão da metodologia de análise
    """
    return ANALISE_CONFIG.get('versao_analise', '1.0')

def get_config(tipo: str, chave: str = None) -> Any:
    """
    Função utilitária para obter configurações de forma centralizada
    
    Args:
        tipo: Tipo de configuração ('api', 'hackathon', 'deduplication', etc.)
        chave: Chave específica (opcional)
    
    Returns:
        Valor da configuração solicitada
    """
    configs = {
        'api': API_CONFIG,
        'hackathon': HACKATHON_CONFIG,
        'deduplication': DEDUPLICATION_CONFIG,
        'logging': LOGGING_CONFIG,
        'performance': PERFORMANCE_CONFIG
    }
    
    config = configs.get(tipo, {})
    
    if chave:
        return config.get(chave)
    
    return config

def get_meses_para_coletar() -> list:
    """
    Retorna a lista de meses para coleta de gastos baseada nas configurações
    """
    config = get_config('hackathon', 'gastos')
    return config['meses_para_coletar']

# Configurações de validação
VALIDATION_CONFIG = {
    'campos_obrigatorios': {
        'deputados': ['nome', 'api_camara_id'],
        'gastos': ['deputado_id', 'ano', 'mes', 'valor_liquido'],
        'proposicoes': ['tipo', 'numero', 'ano', 'ementa']
    },
    'validar_cnpj': True,
    'validar_datas': True,
    'ignorar_registros_invalidos': True
}

# Configurações centralizadas de coleta com limitador de data
COLETA_CONFIG = {
    # Data limite principal para todas as coletas
    'data_inicio_padrao': '2025-06-01',  # Requisito principal: 06/2025 para cá
    'data_fim_padrao': None,  # None = data atual
    'limpar_dados_antigos': True,  # Limpar dados anteriores à data início
    
    # Configurações específicas por tipo de coleta
    'referencia': {
        'habilitado': True,
        'respeitar_data_inicio': True,  # Aplicar filtro mesmo em dados de referência
        'descricao': 'Dados de Referência (Deputados, Partidos)'
    },
    
    'gastos': {
        'habilitado': True,
        'respeitar_data_inicio': True,
        'descricao': 'Gastos Parlamentares (CEAP)'
    },
    
    
    'emendas': {
        'habilitado': True,
        'respeitar_data_inicio': True,
        'descricao': 'Emendas Parlamentares',
        'ano_inicio_legislatura': 2023,  # Início da legislatura atual
        'apenas_legislatura_atual': True,  # Filtro principal
        'descricao_filtro': 'Apenas legislatura atual (2023+)'
    },
    
    # Votações removidas - Evolução Futura
    # MOVIDO PARA deprecated/ - será implementado em versão futura
    
    # Proposições habilitadas com integração GCS
    'proposicoes': {
        'habilitado': True,
        'respeitar_data_inicio': True,
        'descricao': 'Proposições Legislativas com GCS',
        'ano_coleta': 2025,
        'data_inicio': '2025-06-01'
    },
}

def get_coleta_config(tipo_coleta: str = None) -> dict:
    """
    Obtém configurações de coleta de forma centralizada
    
    Args:
        tipo_coleta: Tipo específico de coleta (opcional)
    
    Returns:
        dict: Configurações solicitadas
    """
    if tipo_coleta:
        return COLETA_CONFIG.get(tipo_coleta, {})
    
    return COLETA_CONFIG

def get_data_inicio_coleta() -> str:
    """
    Retorna a data de início configurada para as coletas
    
    Returns:
        str: Data de início no formato YYYY-MM-DD
    """
    return COLETA_CONFIG['data_inicio_padrao']

def get_data_fim_coleta() -> str:
    """
    Retorna a data fim configurada para as coletas
    
    Returns:
        str: Data fim no formato YYYY-MM-DD (ou data atual se None)
    """
    data_fim = COLETA_CONFIG['data_fim_padrao']
    if data_fim is None:
        return datetime.now().strftime('%Y-%m-%d')
    return data_fim

def deve_respeitar_data_inicio(tipo_coleta: str) -> bool:
    """
    Verifica se um tipo de coleta deve respeitar a data de início
    
    Args:
        tipo_coleta: Tipo de coleta a verificar
    
    Returns:
        bool: True se deve respeitar a data de início
    """
    config = get_coleta_config(tipo_coleta)
    return config.get('respeitar_data_inicio', True)

def coleta_habilitada(tipo_coleta: str) -> bool:
    """
    Verifica se um tipo de coleta está habilitado
    
    Args:
        tipo_coleta: Tipo de coleta a verificar
    
    Returns:
        bool: True se a coleta está habilitada
    """
    config = get_coleta_config(tipo_coleta)
    return config.get('habilitado', False)

def get_tipos_coleta_habilitados() -> list:
    """
    Retorna lista com todos os tipos de coleta habilitados
    
    Returns:
        list: Lista de tipos de coleta habilitados
    """
    habilitados = []
    for tipo, config in COLETA_CONFIG.items():
        if isinstance(config, dict) and config.get('habilitado', False):
            habilitados.append(tipo)
    return habilitados

# Configurações do Fallback de Votações (REMOVIDO - Evolução Futura)
# MOVIDO PARA deprecated/ - será implementado em versão futura

def get_ano_inicio_legislatura_emendas() -> int:
    """
    Retorna o ano de início da legislatura para emendas
    
    Returns:
        int: Ano de início (2023 para legislatura atual)
    """
    config = get_coleta_config('emendas')
    return config.get('ano_inicio_legislatura', 2023)

def deve_apenas_legislatura_atual_emendas() -> bool:
    """
    Verifica se deve coletar apenas emendas da legislatura atual
    
    Returns:
        bool: True se deve filtrar por legislatura atual
    """
    config = get_coleta_config('emendas')
    return config.get('apenas_legislatura_atual', True)

def get_descricao_filtro_emendas() -> str:
    """
    Retorna descrição do filtro temporal para emendas
    
    Returns:
        str: Descrição do filtro configurado
    """
    config = get_coleta_config('emendas')
    return config.get('descricao_filtro', 'Emendas Parlamentares')

# Configurações de Emendas Parlamentares (Portal da Transparência)
EMENDAS_CONFIG = {
    'ano_coleta': 2025,  # Ano principal para coleta (configurável)
    'habilitado': True,
    'data_inicio': '2025-01-01',  # Data início do ano configurado
    'data_fim': '2025-12-31',    # Data fim do ano configurado
    'descricao': 'Emendas Parlamentares - Portal da Transparência',
    'download_url': 'https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO',
    'temp_dir': 'backend/temp',
    'arquivo_csv_esperado': 'EmendasParlamentares.csv',
    'colunas_obrigatorias': ['Nome do Autor da Emenda', 'Ano da Emenda'],
    'valor_minimo': 0.01,  # Valor mínimo para considerar emenda
    'ignorar_bancadas': True,  # Ignorar emendas de "BANCADA"
    'normalizar_nomes': True,  # Aplicar normalização de nomes
    'gerar_ranking': True,  # Gerar ranking automático
    'batch_size': 50,  # Tamanho do lote para commits
    'mostrar_progresso': True  # Mostrar progresso detalhado
}

def get_emendas_config(chave: str = None) -> any:
    """
    Obtém configurações de emendas de forma centralizada
    
    Args:
        chave: Chave específica (opcional)
    
    Returns:
        Valor da configuração solicitada ou dicionário completo
    """
    if chave:
        return EMENDAS_CONFIG.get(chave)
    
    return EMENDAS_CONFIG

def get_ano_emendas() -> int:
    """
    Retorna o ano configurado para coleta de emendas
    
    Returns:
        int: Ano configurado para coleta
    """
    return EMENDAS_CONFIG.get('ano_coleta', 2025)

def get_descricao_emendas() -> str:
    """
    Retorna descrição configurada para emendas
    
    Returns:
        str: Descrição da coleta de emendas
    """
    return EMENDAS_CONFIG.get('descricao', 'Emendas Parlamentares')

def get_url_download_emendas() -> str:
    """
    Retorna URL de download configurada para emendas
    
    Returns:
        str: URL de download do arquivo de emendas
    """
    return EMENDAS_CONFIG.get('download_url')

def emendas_habilitadas() -> bool:
    """
    Verifica se coleta de emendas está habilitada
    
    Returns:
        bool: True se estiver habilitada
    """
    return EMENDAS_CONFIG.get('habilitado', False)

def get_periodo_emendas() -> tuple:
    """
    Retorna o período configurado para coleta de emendas
    
    Returns:
        tuple: (data_inicio, data_fim) no formato YYYY-MM-DD
    """
    ano = get_ano_emendas()
    data_inicio = EMENDAS_CONFIG.get('data_inicio', f'{ano}-01-01')
    data_fim = EMENDAS_CONFIG.get('data_fim', f'{ano}-12-31')
    
    return data_inicio, data_fim

def atualizar_ano_emendas(novo_ano: int) -> None:
    """
    Atualiza o ano de coleta de emendas e ajusta as datas
    
    Args:
        novo_ano: Novo ano para coleta
    """
    EMENDAS_CONFIG['ano_coleta'] = novo_ano
    EMENDAS_CONFIG['data_inicio'] = f'{novo_ano}-01-01'
    EMENDAS_CONFIG['data_fim'] = f'{novo_ano}-12-31'
