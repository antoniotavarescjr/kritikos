#!/usr/bin/env python3
"""
Utilitários para processamento de textos de proposições
Implementa download de PDFs e extração de texto completo
"""

import os
import requests
import logging
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
import xml.etree.ElementTree as ET

# Tentar importar bibliotecas de PDF
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

logger = logging.getLogger(__name__)


class TextoProposicaoUtils:
    """
    Utilitários para processamento de textos de proposições legislativas.
    Implementa download de PDFs e extração de texto.
    """
    
    def __init__(self, timeout: int = 30, cache_dir: str = None):
        """
        Inicializa utilitário de texto.
        
        Args:
            timeout: Timeout para requisições HTTP
            cache_dir: Diretório para cache local
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KritikosETL/1.0 (Hackathon 2025)'
        })
        
        # Configurar cache
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / 'kritikos_textos'
        
        self.cache_dir.mkdir(exist_ok=True)
        
        logger.info(f"TextoUtils inicializado - Cache: {self.cache_dir}")
        logger.info(f"PyPDF2: {PYPDF2_AVAILABLE}, pdfplumber: {PDFPLUMBER_AVAILABLE}")
    
    def obter_url_inteiro_teor(self, uri_proposicao: str) -> Optional[str]:
        """
        Obtém a URL do texto completo a partir da URI da proposição.
        
        Args:
            uri_proposicao: URI da API da proposição ou URL direta do PDF
            
        Returns:
            URL do texto completo ou None
        """
        try:
            # Se já for uma URL do site da Câmara, retornar diretamente
            if 'camara.leg.br/proposicoesWeb/prop_mostrarintegra' in uri_proposicao:
                logger.debug(f"URL direta do inteiro teor detectada: {uri_proposicao}")
                return uri_proposicao
            
            logger.debug(f"Buscando URL inteiro teor para: {uri_proposicao}")
            
            response = self.session.get(uri_proposicao, timeout=self.timeout)
            response.raise_for_status()
            
            # Verificar se é JSON ou XML
            content_type = response.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                # Resposta JSON (API v2)
                dados = response.json()
                url_inteiro_teor = dados.get('dados', {}).get('urlInteiroTeor')
                if url_inteiro_teor:
                    logger.debug(f"URL inteiro teor encontrada (JSON): {url_inteiro_teor}")
                    return url_inteiro_teor
                else:
                    logger.warning(f"urlInteiroTeor não encontrado no JSON: {uri_proposicao}")
                    return None
            
            else:
                # Resposta XML (API antiga)
                # Parsear XML para extrair urlInteiroTeor
                root = ET.fromstring(response.content)
                
                # Buscar urlInteiroTeor sem namespace
                url_element = root.find('.//urlInteiroTeor')
                if url_element is not None:
                    url_inteiro_teor = url_element.text
                    logger.debug(f"URL inteiro teor encontrada (XML): {url_inteiro_teor}")
                    return url_inteiro_teor
                else:
                    logger.warning(f"urlInteiroTeor não encontrado no XML: {uri_proposicao}")
                    return None
                
        except Exception as e:
            logger.error(f"Erro ao obter URL inteiro teor: {e}")
            return None
    
    def baixar_pdf(self, url_pdf: str, proposicao_id: str) -> Optional[bytes]:
        """
        Baixa o PDF de uma proposição.
        
        Args:
            url_pdf: URL do PDF da proposição
            proposicao_id: ID da proposição para cache
            
        Returns:
            Conteúdo do PDF em bytes ou None
        """
        cache_file = self.cache_dir / f"proposicao_{proposicao_id}.pdf"
        
        # Verificar cache
        if cache_file.exists():
            logger.debug(f"PDF encontrado em cache: {cache_file}")
            return cache_file.read_bytes()
        
        try:
            logger.info(f"Baixando PDF: {url_pdf}")
            
            response = self.session.get(url_pdf, timeout=self.timeout)
            response.raise_for_status()
            
            # Verificar se é PDF
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' not in content_type:
                logger.warning(f"URL não retorna PDF: {content_type}")
                return None
            
            # Salvar em cache
            cache_file.write_bytes(response.content)
            logger.debug(f"PDF salvo em cache: {cache_file}")
            
            return response.content
            
        except Exception as e:
            logger.error(f"Erro ao baixar PDF {proposicao_id}: {e}")
            return None
    
    def extrair_texto_pdf(self, pdf_bytes: bytes, proposicao_id: str) -> Optional[str]:
        """
        Extrai texto de bytes de PDF.
        
        Args:
            pdf_bytes: Bytes do PDF
            proposicao_id: ID da proposição para logging
            
        Returns:
            Texto extraído ou None
        """
        if not pdf_bytes:
            return None
        
        texto = None
        
        # Tentar com pdfplumber (melhor qualidade)
        if PDFPLUMBER_AVAILABLE:
            texto = self._extrair_com_pdfplumber(pdf_bytes, proposicao_id)
        
        # Fallback para PyPDF2
        if not texto and PYPDF2_AVAILABLE:
            texto = self._extrair_com_pypdf2(pdf_bytes, proposicao_id)
        
        # Limpar texto
        if texto:
            texto = self._limpar_texto_extraido(texto)
            logger.debug(f"Texto extraído: {len(texto)} caracteres")
        
        return texto
    
    def _extrair_com_pdfplumber(self, pdf_bytes: bytes, proposicao_id: str) -> Optional[str]:
        """
        Extrai texto usando pdfplumber.
        
        Args:
            pdf_bytes: Bytes do PDF
            proposicao_id: ID da proposição
            
        Returns:
            Texto extraído ou None
        """
        try:
            import io
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                texto_completo = ""
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        texto_pagina = page.extract_text()
                        if texto_pagina:
                            texto_completo += f"\n--- Página {page_num} ---\n{texto_pagina}\n"
                    except Exception as e:
                        logger.warning(f"Erro na página {page_num}: {e}")
                        continue
                
                return texto_completo.strip()
                
        except Exception as e:
            logger.error(f"Erro ao extrair com pdfplumber {proposicao_id}: {e}")
            return None
    
    def _extrair_com_pypdf2(self, pdf_bytes: bytes, proposicao_id: str) -> Optional[str]:
        """
        Extrai texto usando PyPDF2.
        
        Args:
            pdf_bytes: Bytes do PDF
            proposicao_id: ID da proposição
            
        Returns:
            Texto extraído ou None
        """
        try:
            import io
            
            with io.BytesIO(pdf_bytes) as pdf_stream:
                reader = PyPDF2.PdfReader(pdf_stream)
                
                texto_completo = ""
                
                for page_num, page in enumerate(reader.pages, 1):
                    try:
                        texto_pagina = page.extract_text()
                        if texto_pagina:
                            texto_completo += f"\n--- Página {page_num} ---\n{texto_pagina}\n"
                    except Exception as e:
                        logger.warning(f"Erro na página {page_num}: {e}")
                        continue
                
                return texto_completo.strip()
                
        except Exception as e:
            logger.error(f"Erro ao extrair com PyPDF2 {proposicao_id}: {e}")
            return None
    
    def _limpar_texto_extraido(self, texto: str) -> str:
        """
        Limpa e normaliza texto extraído do PDF.
        
        Args:
            texto: Texto bruto do PDF
            
        Returns:
            Texto limpo e normalizado
        """
        if not texto:
            return ""
        
        # Remover quebras de linha excessivas
        texto = ' '.join(texto.split())
        
        # Remover caracteres especiais problemáticos
        texto = texto.replace('\x00', '')  # Null character
        texto = texto.replace('\x0b', '')  # Vertical tab
        
        # Normalizar espaços
        texto = ' '.join(texto.split())
        
        # Limitar tamanho (muito grande pode causar problemas)
        if len(texto) > 50000:
            texto = texto[:50000] + "...[texto truncado]"
        
        return texto.strip()
    
    def obter_texto_completo(self, uri_proposicao: str, proposicao_id: str) -> Optional[str]:
        """
        Obtém o texto completo de uma proposição.
        
        Args:
            uri_proposicao: URI da API da proposição
            proposicao_id: ID da proposição
            
        Returns:
            Texto completo ou None
        """
        try:
            # Passo 1: Obter URL do PDF
            url_pdf = self.obter_url_inteiro_teor(uri_proposicao)
            if not url_pdf:
                logger.warning(f"Não foi possível obter URL do PDF para {proposicao_id}")
                return None
            
            # Passo 2: Baixar PDF
            pdf_bytes = self.baixar_pdf(url_pdf, proposicao_id)
            if not pdf_bytes:
                logger.warning(f"Não foi possível baixar PDF para {proposicao_id}")
                return None
            
            # Passo 3: Extrair texto
            texto = self.extrair_texto_pdf(pdf_bytes, proposicao_id)
            if not texto:
                logger.warning(f"Não foi possível extrair texto do PDF para {proposicao_id}")
                return None
            
            logger.info(f"Texto completo obtido para {proposicao_id}: {len(texto)} caracteres")
            return texto
            
        except Exception as e:
            logger.error(f"Erro ao obter texto completo {proposicao_id}: {e}")
            return None
    
    def limpar_cache(self):
        """
        Limpa todos os arquivos do cache.
        """
        try:
            for file in self.cache_dir.glob("*.pdf"):
                file.unlink()
            logger.info(f"Cache limpo: {self.cache_dir}")
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")


# Função de conveniência para uso em outros módulos
def get_texto_proposicao(uri_proposicao: str, proposicao_id: str, 
                        timeout: int = 30, cache_dir: str = None) -> Optional[str]:
    """
    Função de conveniência para obter texto completo de uma proposição.
    
    Args:
        uri_proposicao: URI da API da proposição
        proposicao_id: ID da proposição
        timeout: Timeout para requisições
        cache_dir: Diretório para cache
        
    Returns:
        Texto completo ou None
    """
    utils = TextoProposicaoUtils(timeout=timeout, cache_dir=cache_dir)
    return utils.obter_texto_completo(uri_proposicao, proposicao_id)


def verificar_dependencias_pdf() -> Dict[str, bool]:
    """
    Verifica quais bibliotecas de PDF estão disponíveis.
    
    Returns:
        Dicionário com status das dependências
    """
    return {
        'pypdf2': PYPDF2_AVAILABLE,
        'pdfplumber': PDFPLUMBER_AVAILABLE,
        'alguma_disponivel': PYPDF2_AVAILABLE or PDFPLUMBER_AVAILABLE
    }


if __name__ == "__main__":
    # Teste do utilitário
    logging.basicConfig(level=logging.INFO)
    
    # Exemplo de teste
    uri_teste = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2482075"
    prop_id_teste = "2482075"
    
    print("Testando utilitário de texto...")
    print(f"URI: {uri_teste}")
    print(f"Proposição ID: {prop_id_teste}")
    
    # Verificar dependências
    deps = verificar_dependencias_pdf()
    print(f"Dependências: {deps}")
    
    if not deps['alguma_disponivel']:
        print("❌ Nenhuma biblioteca de PDF disponível!")
        print("Instale com: pip install PyPDF2 pdfplumber")
        exit(1)
    
    # Testar obtenção de texto
    utils = TextoProposicaoUtils()
    texto = utils.obter_texto_completo(uri_teste, prop_id_teste)
    
    if texto:
        print(f"✅ Texto obtido: {len(texto)} caracteres")
        print(f"Primeiros 200 caracteres: {texto[:200]}...")
    else:
        print("❌ Falha ao obter texto")
