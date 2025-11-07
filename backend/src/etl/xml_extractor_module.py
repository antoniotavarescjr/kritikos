#!/usr/bin/env python3
"""
Módulo para extrair informações de XML da API da Câmara
"""

import requests
import json
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class XMLExtractor:
    """
    Extrator de informações de XML da API da Câmara dos Deputados
    """
    
    def __init__(self, timeout: int = 30, retries: int = 3):
        """
        Inicializa o extrator
        
        Args:
            timeout: Timeout para requests
            retries: Número de retentativas
        """
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        
        # Headers para simular navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/xml, text/xml, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def baixar_xml_proposicao(self, uri: str) -> Optional[str]:
        """
        Baixa o XML/JSON completo de uma proposição
        
        Args:
            uri: URI da API da proposição
            
        Returns:
            str: Conteúdo XML/JSON ou None se erro
        """
        for attempt in range(self.retries):
            try:
                logger.info(f"Baixando dados da URI: {uri} (tentativa {attempt + 1}/{self.retries})")
                
                response = self.session.get(uri, timeout=self.timeout)
                response.raise_for_status()
                
                # Verificar content-type
                content_type = response.headers.get('content-type', '').lower()
                
                content = response.text
                logger.info(f"Dados baixados com sucesso: {len(content)} caracteres (Content-Type: {content_type})")
                
                return content
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout na tentativa {attempt + 1}")
                if attempt < self.retries - 1:
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro na requisição: {e}")
                if attempt < self.retries - 1:
                    continue
                    
            except Exception as e:
                logger.error(f"Erro inesperado: {e}")
                break
        
        return None
    
    def extrair_url_inteiro_teor(self, xml_content: str) -> Optional[str]:
        """
        Extrai URL do inteiro teor do XML
        
        Args:
            xml_content: Conteúdo XML da proposição
            
        Returns:
            str: URL do inteiro teor ou None se não encontrar
        """
        try:
            # Parsear XML
            root = ET.fromstring(xml_content)
            
            # Namespace comum da API da Câmara
            namespaces = {
                'ns': 'https://dadosabertos.camara.leg.br/arquivos/schemas/'
            }
            
            # Estratégias para encontrar a URL do inteiro teor
            urls_encontradas = []
            
            # 1. Procurar em diferentes caminhos possíveis
            caminhos_para_tentar = [
                ".//ns:urlInteiroTeor",
                ".//ns:texto",
                ".//ns:documento",
                ".//ns:uriTexto",
                ".//ns:uriInteiroTeor",
                ".//urlInteiroTeor",  # Sem namespace
                ".//texto",  # Sem namespace
                ".//documento",  # Sem namespace
            ]
            
            for caminho in caminhos_para_tentar:
                try:
                    elementos = root.findall(caminho, namespaces)
                    for elem in elementos:
                        if elem.text and elem.text.strip():
                            url = elem.text.strip()
                            if url.startswith('http'):
                                urls_encontradas.append(url)
                                logger.info(f"URL encontrada em {caminho}: {url}")
                except:
                    continue
            
            # 2. Procurar por padrões de URL no texto do XML
            if not urls_encontradas:
                # Procurar por URLs que contenham padrões conhecidos
                padroes_url = [
                    r'https?://[^\s"\'<>]+(?:prop_mostrarintegra|texto-integral|inteiro-teor)[^\s"\'<>]*',
                    r'https?://www\.camara\.leg\.br/[^\s"\'<>]+',
                    r'https?://dadosabertos\.camara\.leg\.br/[^\s"\'<>]*texto[^\s"\'<>]*',
                ]
                
                for padrao in padroes_url:
                    matches = re.findall(padrao, xml_content, re.IGNORECASE)
                    for match in matches:
                        if match not in urls_encontradas:
                            urls_encontradas.append(match)
                            logger.info(f"URL encontrada por padrão: {match}")
            
            # 3. Escolher a melhor URL
            if urls_encontradas:
                # Priorizar URLs do site da Câmara
                urls_camara = [url for url in urls_encontradas if 'camara.leg.br' in url]
                if urls_camara:
                    melhor_url = urls_camara[0]
                else:
                    melhor_url = urls_encontradas[0]
                
                logger.info(f"Melhor URL selecionada: {melhor_url}")
                return melhor_url
            
            logger.warning("Nenhuma URL de inteiro teor encontrada no XML")
            return None
            
        except ET.ParseError as e:
            logger.error(f"Erro ao parsear XML: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair URL do XML: {e}")
            return None
    
    def extrair_informacoes_completas(self, content: str) -> Dict[str, Any]:
        """
        Extrai informações completas do XML/JSON
        
        Args:
            content: Conteúdo XML/JSON
            
        Returns:
            Dict: Informações extraídas
        """
        try:
            # Tentar parsear como JSON primeiro
            try:
                data = json.loads(content)
                logger.info("Conteúdo detectado como JSON")
                
                info = {}
                
                # Extrair dados principais
                if 'dados' in data:
                    dados = data['dados']
                    info['id'] = dados.get('id')
                    info['siglaTipo'] = dados.get('siglaTipo')
                    info['numero'] = dados.get('numero')
                    info['ano'] = dados.get('ano')
                    info['ementa'] = dados.get('ementa')
                    info['dataApresentacao'] = dados.get('dataApresentacao')
                    
                    # Extrair URL do inteiro teor diretamente do JSON
                    if 'urlInteiroTeor' in dados:
                        info['urlInteiroTeor'] = dados['urlInteiroTeor']
                        logger.info(f"URL do inteiro teor encontrada no JSON: {dados['urlInteiroTeor']}")
                    
                    logger.info(f"Dados JSON extraídos: {dados.get('siglaTipo')} {dados.get('numero')}/{dados.get('ano')}")
                
                # Extrair URL do inteiro teor
                url_inteiro_teor = self.extrair_url_inteiro_teor(content)
                if url_inteiro_teor and 'urlInteiroTeor' not in info:
                    info['urlInteiroTeor'] = url_inteiro_teor
                
                return info
                
            except json.JSONDecodeError:
                # Não é JSON, tentar XML
                logger.info("Conteúdo não é JSON, tentando XML...")
                pass
            
            # Tentar parsear como XML
            root = ET.fromstring(content)
            
            info = {}
            
            # Extrair campos básicos diretamente do XML (sem namespace)
            campos_basicos = ['id', 'siglaTipo', 'numero', 'ano', 'ementa', 'dataApresentacao', 'urlInteiroTeor']
            for campo in campos_basicos:
                try:
                    elem = root.find(f'.//{campo}')
                    if elem is not None and elem.text:
                        info[campo] = elem.text.strip()
                        logger.info(f"Campo {campo} encontrado: {elem.text.strip()[:50]}...")
                except:
                    continue
            
            # Se não encontrou com namespace direto, tentar com namespace
            if not info.get('id'):
                namespaces = {
                    'ns': 'https://dadosabertos.camara.leg.br/arquivos/schemas/'
                }
                
                for campo in campos_basicos:
                    try:
                        elem = root.find(f'.//ns:{campo}', namespaces)
                        if elem is not None and elem.text:
                            info[campo] = elem.text.strip()
                            logger.info(f"Campo {campo} encontrado com namespace: {elem.text.strip()[:50]}...")
                    except:
                        continue
            
            # Extrair URL do inteiro teor por padrão se não encontrou
            if not info.get('urlInteiroTeor'):
                url_inteiro_teor = self.extrair_url_inteiro_teor(content)
                if url_inteiro_teor:
                    info['urlInteiroTeor'] = url_inteiro_teor
            
            logger.info(f"Dados XML extraídos: {info.get('siglaTipo')} {info.get('numero')}/{info.get('ano')}")
            
            return info
            
        except Exception as e:
            logger.error(f"Erro ao extrair informações: {e}")
            return {}
    
    def processar_proposicao_completa(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Processa uma proposição completa: baixa XML e extrai informações
        
        Args:
            uri: URI da proposição
            
        Returns:
            Dict: Informações completas incluindo XML e URL do texto
        """
        logger.info(f"Processando proposição completa: {uri}")
        
        # Baixar XML
        xml_content = self.baixar_xml_proposicao(uri)
        if not xml_content:
            logger.error(f"Falha ao baixar XML de {uri}")
            return None
        
        # Extrair informações
        info_completas = self.extrair_informacoes_completas(xml_content)
        if not info_completas:
            logger.error(f"Falha ao extrair informações do XML de {uri}")
            return None
        
        # Adicionar conteúdo XML
        info_completas['xml_content'] = xml_content
        info_completas['xml_uri'] = uri
        
        return info_completas

# Função utilitária para uso fácil
def criar_extrator_xml() -> XMLExtractor:
    """
    Cria instância do extrator XML com configurações padrão
    
    Returns:
        XMLExtractor: Instância configurada
    """
    return XMLExtractor()

    if __name__ == "__main__":
        # Teste rápido
        extractor = criar_extrator_xml()
        
        # Testar com uma URI de exemplo
        uri_teste = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2482075"
        
        print(f"Testando com URI: {uri_teste}")
        
        resultado = extractor.processar_proposicao_completa(uri_teste)
        
        if resultado:
            print("✅ Sucesso!")
            print(f"ID: {resultado.get('id')}")
            print(f"Tipo: {resultado.get('siglaTipo')}")
            print(f"Número: {resultado.get('numero')}")
            print(f"Ano: {resultado.get('ano')}")
            print(f"URL Inteiro Teor: {resultado.get('urlInteiroTeor')}")
            print(f"Tamanho XML: {len(resultado.get('xml_content', ''))}")
        else:
            print("❌ Falha no processamento")
