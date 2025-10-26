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
    
    # Configurações de proposições (HABILITADO - ABORDAGEM JSON)
    'proposicoes': {
        'habilitado': True,  # HABILITADO - Nova abordagem JSON
        'data_inicio': '2025-07-01',  # Início do período do hackathon
        'data_fim': '2025-12-31',
        'meses_foco': [7, 8, 9, 10, 11, 12],  # Meses do hackathon
        'json_url': 'https://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-2025.json',
        'tipos_prioritarios': ['PL', 'PEC', 'PLP', 'MPV', 'PDC', 'PLV', 'PRC', 'SUG', 'REQ', 'RIC'],
        'tipos_para_coletar': ['PL', 'PEC', 'PLP', 'MPV', 'PDC', 'PLV', 'PRC', 'SUG', 'REQ', 'RIC'],
        'anos_para_coletar': [2025],
        'limite_total': 15000,  # Aumentado para capturar mais proposições
        'prioridade_tipos': {'PL': 1, 'PEC': 2, 'PLP': 3, 'MPV': 4, 'PDC': 5, 'PLV': 6, 'PRC': 7, 'SUG': 8, 'REQ': 9, 'RIC': 10},
        'baixar_documentos': True,  # Habilitar download de documentos
        'documentos_tipos_foco': ['PL', 'PEC', 'PLP', 'MPV'],  # Apenas tipos prioritários
        'gcs_estrutura': {
            'metadados': 'proposicoes/metadata/',
            'documents': 'proposicoes/documents/'
        },
        'json_download_timeout': 300,  # 5 minutos para download do JSON completo
        'document_download_timeout': 30,  # Timeout para cada documento
        'max_downloads_paralelos': 10,  # Downloads simultâneos de documentos
        'usar_abordagem_json': True,  # Nova abordagem JSON
        'dias_recentes': 30  # Mantido para compatibilidade
    },
    
    # Configurações de votações (NOVO - HABILITADO)
    'votacoes': {
        'habilitado': True,  # HABILITADO para hackathon
        'data_inicio': '2025-07-01',  # Início do período do hackathon
        'data_fim': '2025-12-31',
        'tipos_votacao': ['Plenário', 'Comissão'],  # Tipos de votação a coletar
        'limite_total': 5000,  # Limite de votações a coletar
        'buscar_votos_deputados': True,  # Coletar votos individuais dos deputados
        'apenas_votacoes_recentes': True  # Foco em votações recentes
    },
    
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

def get_data_inicio_fim() -> tuple:
    """
    Retorna as datas de início e fim para a coleta baseada nas configurações
    """
    config = get_config('hackathon', 'proposicoes')
    return config['data_inicio'], config['data_fim']

def get_meses_para_coletar() -> list:
    """
    Retorna a lista de meses para coleta de gastos baseada nas configurações
    """
    config = get_config('hackathon', 'gastos')
    return config['meses_para_coletar']

def get_tipos_proposicoes() -> list:
    """
    Retorna a lista de tipos de proposições para coletar
    """
    config = get_config('hackathon', 'proposicoes')
    return config['tipos_para_coletar']

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
        'descricao': 'Emendas Parlamentares'
    },
    
    'votacoes': {
        'habilitado': True,
        'respeitar_data_inicio': True,
        'descricao': 'Votações (Plenário e Comissões)'
    },
    
    # Proposições explicitamente desabilitadas conforme requisito
    'proposicoes': {
        'habilitado': False,
        'respeitar_data_inicio': True,
        'descricao': 'Proposições Legislativas (DESABILITADO)'
    }
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

# Configurações do Fallback de Votações
VOTACOES_FALLBACK_CONFIG = {
    'habilitado': True,  # Habilitar fallback quando API falhar
    'anos_para_coletar': [2024, 2023, 2022],  # Anos com dados completos
    'limite_registros': 10000,  # Limite de registros por arquivo
    'formato_preferido': 'json',  # Formato dos arquivos
    'base_url': 'http://dadosabertos.camara.leg.br/arquivos',
    'cache_dir': 'cache/votacoes',
    'tipos_arquivos': [
        'votacoes',           # Dados principais das votações
        'votacoesVotos',      # Votos individuais dos deputados
        'votacoesObjetos',    # Proposições objeto da votação
        'votacoesProposicoes', # Proposições afetadas
        'votacoesOrientacoes'  # Orientações de bancada
    ],
    'rate_limit_delay': 1.0,  # Delay entre downloads
    'timeout_download': 60,  # Timeout por download
    'usar_cache_local': True,  # Usar arquivos em cache
    'upload_gcs': True,  # Fazer upload dos dados completos
    'processar_relacionamentos': True,  # Processar todos os relacionamentos
    'validar_integridade': True  # Validar integridade dos dados
}

def get_votacoes_fallback_config(chave: str = None) -> Any:
    """
    Obtém configurações do fallback de votações
    
    Args:
        chave: Chave específica (opcional)
    
    Returns:
        Valor da configuração solicitada
    """
    if chave:
        return VOTACOES_FALLBACK_CONFIG.get(chave)
    
    return VOTACOES_FALLBACK_CONFIG

def deve_usar_fallback_votacoes() -> bool:
    """
    Verifica se deve usar fallback de votações
    
    Returns:
        bool: True se fallback está habilitado
    """
    return VOTACOES_FALLBACK_CONFIG.get('habilitado', False)

def get_anos_fallback_votacoes() -> list:
    """
    Retorna lista de anos para coleta fallback
    
    Returns:
        list: Anos configurados para coleta
    """
    return VOTACOES_FALLBACK_CONFIG.get('anos_para_coletar', [])

def get_tipos_arquivos_votacoes() -> list:
    """
    Retorna lista de tipos de arquivos para coleta
    
    Returns:
        list: Tipos de arquivos configurados
    """
    return VOTACOES_FALLBACK_CONFIG.get('tipos_arquivos', [])
