"""
Utilitários compartilhados para os scripts ETL
Funções comuns para evitar duplicação de código
"""

import requests
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class RequestManager:
    """Gerenciador centralizado de requisições HTTP"""
    
    def __init__(self, base_url: str = "https://dadosabertos.camara.leg.br/api/v2", 
                 rate_limit_delay: float = 0.3, timeout: int = 15, max_retries: int = 3):
        self.base_url = base_url
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KritikosETL/1.0 (Hackathon 2025)'
        })
    
    def fazer_requisicao(self, endpoint: str, params: Optional[Dict] = None, 
                        use_cache: bool = True) -> Optional[Dict]:
        """
        Faz requisição HTTP com retry e rate limiting
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            use_cache: Se deve usar cache (implementado nos coletores específicos)
            
        Returns:
            Dict com resposta da API ou None se erro
        """
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
                data = response.json()
                
                if 'dados' in data:
                    return data
                
                return data
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"❌ Erro na requisição após {self.max_retries} tentativas: {e}")
                    return None
                
                print(f"⚠️ Tentativa {attempt + 1} falhou, retrying... ({e})")
                time.sleep(self.rate_limit_delay * (attempt + 1))
        
        return None


class DateParser:
    """Utilitário para parsing de datas"""
    
    @staticmethod
    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """
        Converte string de data para datetime
        
        Args:
            date_str: String de data no formato ISO
            
        Returns:
            datetime ou None se inválido
        """
        if not date_str:
            return None
        
        try:
            # Limpar timezone se presente
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            
            return datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError) as e:
            print(f"⚠️ Erro ao converter data '{date_str}': {e}")
            return None
    
    @staticmethod
    def parse_time(datetime_str: Optional[str]) -> Optional[str]:
        """
        Extrai hora de string datetime
        
        Args:
            datetime_str: String datetime no formato ISO
            
        Returns:
            String com hora ou None se inválido
        """
        if not datetime_str:
            return None
        
        try:
            if 'T' in datetime_str:
                return datetime_str.split('T')[1].split('-')[0][:8]  # HH:MM:SS
            return "00:00:00"
        except (ValueError, TypeError):
            return None


class TextProcessor:
    """Utilitário para processamento de texto"""
    
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """
        Limpa e normaliza texto
        
        Args:
            text: Texto para limpar
            
        Returns:
            Texto limpo
        """
        if not text:
            return ""
        
        # Remover espaços extras
        text = ' '.join(text.split())
        
        # Remover caracteres problemáticos
        text = text.replace('\x00', '').replace('\ufeff', '')
        
        return text.strip()
    
    @staticmethod
    def extract_value_from_text(text: str, keywords: list) -> Optional[float]:
        """
        Extrai valor numérico de texto baseado em keywords
        
        Args:
            text: Texto para analisar
            keywords: Lista de keywords para buscar
            
        Returns:
            Valor encontrado ou None
        """
        import re
        
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                # Procurar por valores monetários
                pattern = r'r?\$?\s*[\d.,]+'
                matches = re.findall(pattern, text)
                
                for match in matches:
                    try:
                        # Limpar e converter
                        value_str = match.replace('r$', '').replace('$', '').replace('.', '').replace(',', '.')
                        value = float(value_str)
                        
                        if value > 0:
                            return value
                    except ValueError:
                        continue
        
        return None


class CacheManager:
    """Gerenciador simples de cache em memória"""
    
    def __init__(self, ttl_hours: int = 6):
        self.cache = {}
        self.ttl_seconds = ttl_hours * 3600
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém valor do cache
        
        Args:
            key: Chave do cache
            
        Returns:
            Valor em cache ou None
        """
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                del self.cache[key]
        
        return None
    
    def set(self, key: str, value: Any):
        """
        Define valor no cache
        
        Args:
            key: Chave do cache
            value: Valor para armazenar
        """
        self.cache[key] = (time.time(), value)
    
    def clear(self):
        """Limpa todo o cache"""
        self.cache.clear()


class ValidationUtils:
    """Utilitários para validação de dados"""
    
    @staticmethod
    def validate_cpf(cpf: str) -> bool:
        """
        Validar CPF (simplificado)
        
        Args:
            cpf: CPF para validar
            
        Returns:
            True se válido
        """
        if not cpf:
            return False
        
        # Remover caracteres não numéricos
        cpf_clean = ''.join(filter(str.isdigit, cpf))
        
        # CPF deve ter 11 dígitos
        if len(cpf_clean) != 11:
            return False
        
        # Não pode ser todos os dígitos iguais
        if cpf_clean == cpf_clean[0] * 11:
            return False
        
        return True
    
    @staticmethod
    def validate_cnpj(cnpj: str) -> bool:
        """
        Validar CNPJ (simplificado)
        
        Args:
            cnpj: CNPJ para validar
            
        Returns:
            True se válido
        """
        if not cnpj:
            return False
        
        # Remover caracteres não numéricos
        cnpj_clean = ''.join(filter(str.isdigit, cnpj))
        
        # CNPJ deve ter 14 dígitos
        if len(cnpj_clean) != 14:
            return False
        
        # Não pode ser todos os dígitos iguais
        if cnpj_clean == cnpj_clean[0] * 14:
            return False
        
        return True
    
    @staticmethod
    def is_empty_or_null(value: Any) -> bool:
        """
        Verifica se valor é vazio ou nulo
        
        Args:
            value: Valor para verificar
            
        Returns:
            True se vazio/nulo
        """
        if value is None:
            return True
        
        if isinstance(value, str):
            return not value.strip()
        
        if isinstance(value, (list, dict)):
            return len(value) == 0
        
        return False


def setup_logging():
    """Configura logging básico"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def clear_screen():
    """Limpa tela do terminal"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

def exibir_menu():
    """Exibe menu de opções simplificado"""
    print("\n" + "=" * 60)
    print("     🚀 SISTEMA DE COLETA DE DADOS - KRIKTIKOS")
    print("=" * 60)
    print("1. Executar Pipeline ETL Automático")
    print("0. Sair")
    print("=" * 60)
    
    while True:
        try:
            opcao = int(input("\n🎯 Escolha uma opção: "))
            if 0 <= opcao <= 1:
                return opcao
            else:
                print("⚠️ Opção inválida. Digite 0 ou 1.")
        except ValueError:
            print("⚠️ Entrada inválida. Digite um número.")

# Instâncias globais para reuse
request_manager = RequestManager()
date_parser = DateParser()
text_processor = TextProcessor()
cache_manager = CacheManager()
validation_utils = ValidationUtils()
