#!/usr/bin/env python3
"""
Coletor de Emendas Orçamentárias do Portal da Transparência via Download
Abordagem robusta usando download do arquivo CSV oficial em vez da API limitada
Garante acesso a dados de 2025 e informações completas
"""

import sys
import os
import zipfile
import requests
import pandas as pd
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from difflib import SequenceMatcher
import unicodedata

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar configurações
sys.path.append(str(Path(__file__).parent))
from config import get_config

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado
from models.emenda_models import EmendaParlamentar, DetalheEmenda, RankingEmendas

# Importar utilitários
from utils.gcs_utils import get_gcs_manager

# Importar ETL utils
from etl_utils import ETLBase, DateParser, GCSUploader

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

class ColetorEmendasDownload(ETLBase):
    """
    Classe responsável por coletar emendas orçamentárias via download oficial
    Herda de ETLBase para usar funcionalidades comuns
    """

    def __init__(self):
        """Inicializa o coletor usando ETLBase"""
        super().__init__()
        
        # Configurações do download
        self.download_url = "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares"
        self.temp_dir = Path("temp_emendas")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Inicializar GCS Manager
        self.gcs_manager = get_gcs_manager()
        self.gcs_disponivel = self.gcs_manager.is_available()
        
        print(f"✅ Coletor de emendas (Download CSV) inicializado")
        print(f"   📁 Diretório temporário: {self.temp_dir}")
        print(f"   📁 GCS disponível: {self.gcs_disponivel}")

    def normalizar_texto(self, texto: str) -> str:
        """
        Normaliza texto para comparação robusta
        Remove acentos, converte para minúsculo, remove espaços extras
        """
        if not texto:
            return ""
        
        # Remover acentos
        texto = unicodedata.normalize('NFKD', texto)
        texto = ''.join(c for c in texto if not unicodedata.combining(c))
        
        # Converter para minúsculo e remover espaços
        texto = texto.lower().strip()
        
        # Remover caracteres especiais extras
        texto = ''.join(c for c in texto if c.isalnum() or c.isspace())
        
        return texto

    def calcular_similaridade(self, texto1: str, texto2: str) -> float:
        """
        Calcula similaridade entre dois textos usando SequenceMatcher
        """
        if not texto1 or not texto2:
            return 0.0
        
        norm1 = self.normalizar_texto(texto1)
        norm2 = self.normalizar_texto(texto2)
        
        return SequenceMatcher(None, norm1, norm2).ratio()

    def buscar_deputado_por_nome_robusto(self, nome_autor: str, db: Session) -> Optional[int]:
        """
        Busca ID do deputado pelo nome com estratégia robusta e fuzzy matching
        """
        if not nome_autor or 'bancada' in nome_autor.lower():
            return None
        
        nome_normalizado = self.normalizar_texto(nome_autor)
        
        # Estratégia 1: Match exato (case-insensitive)
        deputado = db.query(Deputado).filter(
            func.upper(Deputado.nome) == func.upper(nome_autor.strip())
        ).first()
        
        if deputado:
            print(f"      ✅ Match exato: {deputado.nome}")
            return deputado.id
        
        # Estratégia 2: Match parcial (contém)
        deputado = db.query(Deputado).filter(
            Deputado.nome.ilike(f"%{nome_autor.strip()}%")
        ).first()
        
        if deputado:
            print(f"      ✅ Match parcial: {deputado.nome}")
            return deputado.id
        
        # Estratégia 3: Match por partes do nome
        partes_nome = nome_autor.strip().split()
        if len(partes_nome) >= 2:
            # Tentar combinações de partes
            for i in range(len(partes_nome)):
                for j in range(i+1, min(i+3, len(partes_nome)+1)):
                    parte_combinada = ' '.join(partes_nome[i:j])
                    deputado = db.query(Deputado).filter(
                        Deputado.nome.ilike(f"%{parte_combinada}%")
                    ).first()
                    
                    if deputado:
                        print(f"      ✅ Match por partes: {deputado.nome}")
                        return deputado.id
        
        # Estratégia 4: Fuzzy matching com todos os deputados
        todos_deputados = db.query(Deputado).all()
        melhor_match = None
        melhor_score = 0.0
        
        for deputado in todos_deputados:
            score = self.calcular_similaridade(nome_autor, deputado.nome)
            if score > melhor_score and score > 0.7:  # Threshold de 70%
                melhor_score = score
                melhor_match = deputado
        
        if melhor_match:
            print(f"      ✅ Fuzzy match: {melhor_match.nome} (score: {melhor_score:.2f})")
            return melhor_match.id
        
        # Estratégia 5: Primeiro nome apenas
        if len(partes_nome) >= 1:
            primeiro_nome = partes_nome[0]
            deputado = db.query(Deputado).filter(
                Deputado.nome.ilike(f"{primeiro_nome}%")
            ).first()
            
            if deputado:
                print(f"      ✅ Match primeiro nome: {deputado.nome}")
                return deputado.id
        
        print(f"      ⚠️ Nenhum deputado encontrado para: {nome_autor}")
        return None

    def baixar_arquivo_emendas(self) -> Optional[Path]:
        """
        Baixa o arquivo ZIP de emendas do Portal da Transparência
        Tenta múltiplas abordagens para obter o arquivo
        """
        print(f"📥 Baixando arquivo de emendas de: {self.download_url}")
        
        # Estratégia 1: Tentar download direto
        zip_path = self._tentar_download_direto()
        if zip_path:
            return zip_path
        
        # Estratégia 2: Usar arquivo existente se houver
        zip_path = self._usar_arquivo_existente()
        if zip_path:
            return zip_path
        
        # Estratégia 3: Tentar abordagem alternativa
        zip_path = self._tentar_download_alternativo()
        if zip_path:
            return zip_path
        
        print("❌ Todas as estratégias de download falharam")
        return None

    def _tentar_download_direto(self) -> Optional[Path]:
        """Tenta download direto com headers de navegador"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(self.download_url, headers=headers, timeout=300, allow_redirects=True)
            response.raise_for_status()
            
            # Verificar se é HTML
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                print(f"   ⚠️ Download direto retornou HTML")
                return None
            
            # Verificar tamanho mínimo
            if len(response.content) < 1000000:
                print(f"   ⚠️ Arquivo muito pequeno ({len(response.content)} bytes)")
                return None
            
            # Salvar arquivo
            zip_path = self.temp_dir / f"emendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Download direto funcionou: {zip_path} ({len(response.content)} bytes)")
            return zip_path
            
        except Exception as e:
            print(f"   ⚠️ Download direto falhou: {e}")
            return None

    def _usar_arquivo_existente(self) -> Optional[Path]:
        """Verifica se existe um arquivo ZIP válido já baixado"""
        try:
            # Procurar arquivos ZIP existentes
            zip_files = list(self.temp_dir.glob("*.zip"))
            
            for zip_file in zip_files:
                # Verificar tamanho mínimo (arquivos válidos têm > 20MB)
                if zip_file.stat().st_size > 20000000:  # 20MB
                    # Verificar se é um ZIP válido
                    try:
                        with zipfile.ZipFile(zip_file, 'r') as test_zip:
                            test_zip.testzip()
                        print(f"✅ Usando arquivo existente: {zip_file}")
                        return zip_file
                    except:
                        continue
            
            print("   ⚠️ Nenhum arquivo ZIP válido encontrado")
            return None
            
        except Exception as e:
            print(f"   ⚠️ Erro ao verificar arquivos existentes: {e}")
            return None

    def _tentar_download_alternativo(self) -> Optional[Path]:
        """Tenta abordagem alternativa de download"""
        try:
            # URLs alternativas que podem funcionar
            urls_alternativas = [
                "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO",
                "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/2025",
                "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/csv"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/zip,application/octet-stream,*/*',
            }
            
            for url in urls_alternativas:
                try:
                    print(f"   🔄 Tentando URL alternativa: {url}")
                    response = requests.get(url, headers=headers, timeout=60)
                    response.raise_for_status()
                    
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' in content_type:
                        continue
                    
                    if len(response.content) < 1000000:
                        continue
                    
                    zip_path = self.temp_dir / f"emendas_alt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    with open(zip_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ Download alternativo funcionou: {zip_path}")
                    return zip_path
                    
                except:
                    continue
            
            print("   ⚠️ URLs alternativas também falharam")
            return None
            
        except Exception as e:
            print(f"   ⚠️ Download alternativo falhou: {e}")
            return None

    def extrair_csv_do_zip(self, zip_path: Path) -> Optional[Path]:
        """
        Extrai o arquivo CSV do ZIP baixado
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Listar arquivos no ZIP
                arquivos = zip_ref.namelist()
                print(f"📁 Arquivos no ZIP: {arquivos}")
                
                # Procurar arquivo CSV
                csv_file = None
                for arquivo in arquivos:
                    if arquivo.lower().endswith('.csv'):
                        csv_file = arquivo
                        break
                
                if not csv_file:
                    print("❌ Nenhum arquivo CSV encontrado no ZIP")
                    return None
                
                # Extrair CSV
                zip_ref.extract(csv_file, self.temp_dir)
                csv_path = self.temp_dir / csv_file
                
                print(f"✅ CSV extraído: {csv_path}")
                return csv_path
                
        except Exception as e:
            print(f"❌ Erro ao extrair CSV: {e}")
            return None

    def ler_csv_emendas(self, csv_path: Path, ano_filtro: int = None) -> pd.DataFrame:
        """
        Lê o arquivo CSV de emendas com tratamento robusto
        """
        try:
            print(f"📊 Lendo CSV: {csv_path}")
            
            # Ler CSV com diferentes encodings e separadores
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            separators = [';', ',', '\t']
            df = None
            
            for encoding in encodings:
                for sep in separators:
                    try:
                        df = pd.read_csv(csv_path, encoding=encoding, sep=sep, decimal=',', thousands='.')
                        print(f"✅ CSV lido com encoding: {encoding}, separador: {sep}")
                        break
                    except Exception as e:
                        continue
                if df is not None:
                    break
            
            if df is None:
                raise Exception("Não foi possível ler o CSV com nenhum encoding/separador")
            
            print(f"📊 Dimensões do CSV: {df.shape}")
            print(f"📋 Colunas: {list(df.columns)}")
            
            # Padronizar nomes de colunas (remover espaços e caracteres especiais)
            df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace(r'[^\w_]', '', regex=True)
            print(f"📋 Colunas padronizadas: {list(df.columns)}")
            
            # Mapeamento flexível de colunas para diferentes formatos do CSV
            column_mapping = self._mapear_colunas_csv(df.columns)
            if column_mapping:
                df = df.rename(columns=column_mapping)
                print(f"📋 Colunas mapeadas: {list(df.columns)}")
            
            # Filtrar por ano se especificado
            if ano_filtro:
                # Tentar diferentes nomes de coluna de ano
                ano_col = None
                for col in ['ano', 'Ano', 'Ano_da_Emenda', 'Ano Emenda']:
                    if col in df.columns:
                        ano_col = col
                        break
                
                if ano_col:
                    df = df[df[ano_col] == ano_filtro]
                    print(f"📊 Filtrado por ano {ano_filtro}: {len(df)} registros")
                else:
                    print(f"⚠️ Coluna de ano não encontrada. Colunas disponíveis: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            print(f"❌ Erro ao ler CSV: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _mapear_colunas_csv(self, columns: list) -> dict:
        """
        Mapeia colunas do CSV para os nomes esperados pelo sistema
        """
        mapping = {}
        
        # Mapeamento baseado nos diferentes formatos de CSV que podemos encontrar
        column_map = {
            # Colunas de identificação
            'Autor': 'autor',
            'Nome_do_Autor': 'autor',
            'Nome do Autor da Emenda': 'autor',
            'Ano': 'ano',
            'Ano_da_Emenda': 'ano',
            'Ano Emenda': 'ano',
            'Número_Emenda': 'numero_emenda',
            'Número da emenda': 'numero_emenda',
            'Numero Emenda': 'numero_emenda',
            'Código_da_Emenda': 'codigo_emenda',
            'Código da Emenda': 'codigo_emenda',
            
            # Colunas de tipo
            'Tipo_Emenda': 'tipo_emenda',
            'Tipo de Emenda': 'tipo_emenda',
            'Tipo Emenda': 'tipo_emenda',
            
            # Colunas financeiras
            'Valor_Empenhado': 'valor_empenhado',
            'Valor Empenhado': 'valor_empenhado',
            'Valor_Liquidado': 'valor_liquidado',
            'Valor Liquidado': 'valor_liquidado',
            'Valor_Pago': 'valor_pago',
            'Valor Pago': 'valor_pago',
            
            # Colunas de localização
            'UF': 'uf',
            'Função': 'funcao',
            'Nome_Função': 'funcao',
            'Nome Função': 'funcao',
            'Subfunção': 'subfuncao',
            'Nome_Subfunção': 'subfuncao',
            'Nome Subfunção': 'subfuncao',
            'Localidade_do_Gasto': 'localidade',
            'Localidade do gasto': 'localidade',
            'Localidade de aplicação do recurso': 'localidade',
            'Município': 'municipio',
            
            # Colunas de data
            'Data_do_Empenho': 'data_empenho',
            'Data do Empenho': 'data_empenho',
            'Data Empenho': 'data_empenho',
            
            # Códigos
            'Código_Função': 'codigo_funcao',
            'Código Função': 'codigo_funcao',
            'Código_Subfunção': 'codigo_subfuncao',
            'Código Subfunção': 'codigo_subfuncao',
            'Nome_Programa': 'programa',
            'Nome Programa': 'programa',
            'Nome_Ação': 'acao',
            'Nome Ação': 'acao'
        }
        
        for col in columns:
            if col in column_map:
                mapping[col] = column_map[col]
        
        return mapping

    def mapear_tipo_emenda(self, tipo_emenda: str) -> str:
        """
        Mapeia tipos de emenda do CSV para o modelo
        """
        if not tipo_emenda:
            return 'EMD'
        
        tipo_normalizado = str(tipo_emenda).strip().upper()
        
        mapeamento = {
            'EMENDA INDIVIDUAL': 'EMD',
            'EMENDA DE BANCADA': 'EMB',
            'EMENDA DE COMISSÃO': 'EMC',
            'EMENDA DE RELATOR': 'EMR'
        }
        
        return mapeamento.get(tipo_normalizado, 'EMD')

    def extrair_local_emenda(self, funcao: str, subfuncao: str, localidade: str) -> Optional[str]:
        """
        Extrai local da emenda baseado na função e localidade
        """
        if not funcao:
            return None
        
        funcao_lower = str(funcao).lower()
        
        # Mapeamento baseado em funções orçamentárias
        if 'saúde' in funcao_lower or 'saude' in funcao_lower:
            return 'SAÚDE'
        elif 'educação' in funcao_lower or 'educacao' in funcao_lower:
            return 'EDUCAÇÃO'
        elif 'urbanismo' in funcao_lower:
            return 'URBANISMO'
        elif 'assistência' in funcao_lower or 'assistencia' in funcao_lower:
            return 'ASSISTÊNCIA SOCIAL'
        elif 'segurança' in funcao_lower or 'seguranca' in funcao_lower:
            return 'SEGURANÇA'
        elif 'infraestrutura' in funcao_lower:
            return 'INFRAESTRUTURA'
        else:
            return str(funcao).upper() if funcao else 'OUTROS'

    def extrair_natureza_emenda(self, tipo_emenda: str, autor: str) -> str:
        """
        Extrai natureza da emenda baseado no tipo e autor
        """
        if not tipo_emenda:
            return 'Individual'
        
        if 'BANCADA' in str(tipo_emenda).upper():
            return 'Bancada'
        elif 'INDIVIDUAL' in str(tipo_emenda).upper():
            return 'Individual'
        elif 'COMISSÃO' in str(tipo_emenda).upper() or 'COMISSAO' in str(tipo_emenda).upper():
            return 'Comissão'
        else:
            return 'Individual'

    def converter_uf_para_sigla(self, uf: str) -> str:
        """
        Converte nome completo do estado para sigla de 2 caracteres
        """
        if not uf:
            return ""
        
        # Se já tem 2 caracteres, assume que é sigla
        if len(str(uf).strip()) == 2:
            return str(uf).strip().upper()
        
        # Mapeamento de nomes para siglas
        uf_normalizado = str(uf).strip().upper()
        
        mapa_ufs = {
            'ACRE': 'AC',
            'ALAGOAS': 'AL',
            'AMAPÁ': 'AP',
            'AMAZONAS': 'AM',
            'BAHIA': 'BA',
            'CEARÁ': 'CE',
            'DISTRITO FEDERAL': 'DF',
            'ESPÍRITO SANTO': 'ES',
            'GOIÁS': 'GO',
            'MARANHÃO': 'MA',
            'MATO GROSSO': 'MT',
            'MATO GROSSO DO SUL': 'MS',
            'MINAS GERAIS': 'MG',
            'PARÁ': 'PA',
            'PARAÍBA': 'PB',
            'PARANÁ': 'PR',
            'PERNAMBUCO': 'PE',
            'PIAUÍ': 'PI',
            'RIO DE JANEIRO': 'RJ',
            'RIO GRANDE DO NORTE': 'RN',
            'RIO GRANDE DO SUL': 'RS',
            'RONDÔNIA': 'RO',
            'RORAIMA': 'RR',
            'SANTA CATARINA': 'SC',
            'SÃO PAULO': 'SP',
            'SERGIPE': 'SE',
            'TOCANTINS': 'TO'
        }
        
        return mapa_ufs.get(uf_normalizado, uf_normalizado[:2] if len(uf_normalizado) >= 2 else "")

    def limpar_valor_monetario(self, valor) -> float:
        """
        Converte valor monetário para float de forma robusta
        """
        if not valor or pd.isna(valor):
            return 0.0
        
        try:
            # Remover formatação e converter
            valor_str = str(valor).replace('R$', '').replace('.', '').replace(',', '.')
            return float(valor_str)
        except (ValueError, AttributeError):
            return 0.0

    def salvar_emenda_csv(self, linha: pd.Series, db: Session) -> Optional[EmendaParlamentar]:
        """
        Salva emenda do CSV no banco de dados
        """
        try:
            # Usar campos mapeados flexivelmente
            codigo_emenda = str(linha.get('codigo_emenda', ''))
            if not codigo_emenda:
                print(f"      ⚠️ Emenda sem código, pulando: {linha.to_dict()}")
                return None
            
            # Verificar se já existe
            existente = db.query(EmendaParlamentar).filter(
                EmendaParlamentar.api_camara_id == codigo_emenda
            ).first()
            
            if existente:
                print(f"      ℹ️ Emenda já existe: {codigo_emenda}")
                return existente
            
            # Extrair dados básicos usando campos mapeados
            ano = int(linha.get('ano', 0))
            if ano == 0:
                print(f"      ⚠️ Emenda sem ano válido, pulando: {codigo_emenda}")
                return None
                
            tipo_emenda_csv = linha.get('tipo_emenda', '')
            nome_autor = linha.get('autor', '')  # USAR CAMPO MAPEADO
            
            # Mapear tipo
            tipo_mapeado = self.mapear_tipo_emenda(tipo_emenda_csv)
            
            # Extrair valores financeiros
            valor_empenhado = self.limpar_valor_monetario(linha.get('valor_empenhado'))
            valor_liquidado = self.limpar_valor_monetario(linha.get('valor_liquidado'))
            valor_pago = self.limpar_valor_monetario(linha.get('valor_pago'))
            
            # Usar o maior valor disponível
            valor_emenda = max(
                valor_empenhado or 0,
                valor_liquidado or 0,
                valor_pago or 0
            ) or 0
            
            # Extrair informações adicionais
            funcao = linha.get('funcao', '')
            subfuncao = linha.get('subfuncao', '')
            localidade = linha.get('localidade', '')
            municipio = linha.get('municipio', '')
            uf = linha.get('uf', '')
            
            # Converter UF para sigla de 2 caracteres se for nome completo
            uf = self.converter_uf_para_sigla(uf)
            
            # Extrair número da emenda
            numero_emenda = linha.get('numero_emenda', 0)
            try:
                numero_emenda = int(numero_emenda) if numero_emenda else 0
            except (ValueError, TypeError):
                numero_emenda = 0
            
            # Buscar deputado com matching robusto
            deputado_id = self.buscar_deputado_por_nome_robusto(nome_autor, db)
            
            # Criar emenda
            emenda = EmendaParlamentar(
                api_camara_id=codigo_emenda,
                deputado_id=deputado_id,
                tipo_emenda=tipo_mapeado,
                numero=numero_emenda,
                ano=ano,
                emenda=f"Emenda {tipo_emenda_csv} - {funcao} - {localidade}",
                local=self.extrair_local_emenda(funcao, subfuncao, localidade),
                natureza=self.extrair_natureza_emenda(tipo_emenda_csv, nome_autor),
                tema=funcao,
                valor_emenda=valor_emenda,
                beneficiario_principal=localidade,
                situacao='Ativa',  # Default pois CSV não fornece
                data_apresentacao=datetime(ano, 1, 1),  # Default início do ano
                autor=nome_autor,
                partido_autor=None,  # Não disponível neste CSV
                uf_autor=uf,
                url_documento=None,  # Não disponível neste CSV
                
                # Campos financeiros adicionais do CSV
                valor_empenhado=valor_empenhado,
                valor_liquidado=valor_liquidado,
                valor_pago=valor_pago,
                valor_resto_inscrito=self.limpar_valor_monetario(linha.get('valor_resto_inscrito')),
                valor_resto_cancelado=self.limpar_valor_monetario(linha.get('valor_resto_cancelado')),
                valor_resto_pago=self.limpar_valor_monetario(linha.get('valor_resto_pago')),
                
                # Campos de otimização
                codigo_funcao_api=linha.get('codigo_funcao'),
                codigo_subfuncao_api=linha.get('codigo_subfuncao'),
                
                # Campos de localização (usando campos existentes)
                uf_beneficiario=uf,
                municipio_beneficiario=municipio,
                
                # Campos de documentação
                documentos_url=None,
                quantidade_documentos=0
            )
            
            db.add(emenda)
            db.flush()  # Para obter o ID
            
            # Salvar detalhes específicos
            self._salvar_detalhes_emenda_csv(emenda, linha, db)
            
            # Upload para GCS
            gcs_url = self._upload_emenda_gcs(emenda, linha, db)
            if gcs_url:
                emenda.gcs_url = gcs_url
            
            print(f"      ✅ Emenda salva: {tipo_mapeado} {emenda.numero}/{ano} - R$ {valor_emenda:,.2f}")
            return emenda
            
        except Exception as e:
            print(f"      ❌ Erro ao salvar emenda: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return None

    def _salvar_detalhes_emenda_csv(self, emenda: EmendaParlamentar, linha: pd.Series, db: Session):
        """Salva detalhes específicos da emenda do CSV"""
        try:
            detalhe = DetalheEmenda(
                emenda_id=emenda.id,
        ementa=f"Emenda {linha.get('tipo_emenda')} para {linha.get('funcao', 'função não informada')}",
                justificativa=f"Localidade do gasto: {linha.get('localidade', 'N/A')}",
                texto_completo=f"Função: {linha.get('funcao', 'N/A')}\n"
                               f"Subfunção: {linha.get('subfuncao', 'N/A')}\n"
                               f"Programa: {linha.get('programa', 'N/A')}\n"
                               f"Ação: {linha.get('acao', 'N/A')}\n"
                               f"Localidade: {linha.get('localidade', 'N/A')}\n"
                               f"Município: {linha.get('municipio', 'N/A')}\n"
                               f"UF: {linha.get('uf', 'N/A')}\n"
                               f"Valor Empenhado: {linha.get('valor_empenhado', '0')}\n"
                               f"Valor Liquidado: {linha.get('valor_liquidado', '0')}\n"
                               f"Valor Pago: {linha.get('valor_pago', '0')}",
                pdf_url=None
            )
            db.add(detalhe)
        except Exception as e:
            print(f"      ⚠️ Erro ao salvar detalhes: {e}")

    def _upload_emenda_gcs(self, emenda: EmendaParlamentar, linha: pd.Series, db: Session) -> Optional[str]:
        """
        Faz upload dos dados completos da emenda para o GCS
        """
        try:
            # Preparar dados completos da emenda
            dados_completos = {
                'emenda': {
                    'id': emenda.id,
                    'api_camara_id': emenda.api_camara_id,
                    'tipo_emenda': emenda.tipo_emenda,
                    'numero': emenda.numero,
                    'ano': emenda.ano,
                    'emenda': emenda.emenda,
                    'local': emenda.local,
                    'natureza': emenda.natureza,
                    'tema': emenda.tema,
                    'valor_emenda': float(emenda.valor_emenda) if emenda.valor_emenda else None,
                    'beneficiario_principal': emenda.beneficiario_principal,
                    'situacao': emenda.situacao,
                    'data_apresentacao': emenda.data_apresentacao.isoformat() if emenda.data_apresentacao else None,
                    'autor': emenda.autor,
                    'partido_autor': emenda.partido_autor,
                    'uf_autor': emenda.uf_autor,
                    'municipio': emenda.municipio_beneficiario,
                    'regiao': getattr(emenda, 'regiao', None),
                    'created_at': emenda.created_at.isoformat() if emenda.created_at else None
                },
                'dados_csv_transparencia': linha.to_dict(),
                'metadados': {
                    'data_coleta': datetime.now().isoformat(),
                    'fonte': 'Download CSV Portal da Transparência',
                    'versao': '2.0'
                }
            }
            
            # Obter GCS Manager
            gcs = get_gcs_manager()
            if not gcs.is_available():
                print(f"      ⚠️ GCS não disponível, pulando upload")
                return None
            
            # Fazer upload
            gcs_url = gcs.upload_emenda(dados_completos, emenda.ano, str(emenda.api_camara_id))
            
            if gcs_url:
                print(f"      📁 Upload GCS realizado: {emenda.tipo_emenda} {emenda.numero}/{emenda.ano}")
                return gcs_url
            else:
                print(f"      ❌ Erro no upload GCS")
                return None
                
        except Exception as e:
            print(f"      ❌ Erro no upload GCS: {e}")
            return None

    def coletar_emendas_ano(self, ano: int, db: Session) -> Dict[str, int]:
        """
        Coleta emendas de um ano específico usando download do CSV
        """
        print(f"\n💰 COLETANDO EMENDAS VIA DOWNLOAD CSV - Ano {ano}")
        print("=" * 70)
        
        resultados = {
            'emendas_encontradas': 0,
            'emendas_salvas': 0,
            'emendas_com_autor': 0,
            'emendas_com_gcs': 0,
            'valor_total_empenhado': 0.0,
            'valor_total_liquidado': 0.0,
            'valor_total_pago': 0.0,
            'erros': 0
        }
        
        try:
            # Etapa 1: Baixar arquivo
            zip_path = self.baixar_arquivo_emendas()
            if not zip_path:
                resultados['erros'] += 1
                return resultados
            
            # Etapa 2: Extrair CSV
            csv_path = self.extrair_csv_do_zip(zip_path)
            if not csv_path:
                resultados['erros'] += 1
                return resultados
            
            # Etapa 3: Ler e filtrar CSV
            df_emendas = self.ler_csv_emendas(csv_path, ano)
            resultados['emendas_encontradas'] = len(df_emendas)
            
            if len(df_emendas) == 0:
                print(f"   ⚠️ Nenhuma emenda encontrada para {ano}")
                return resultados
            
            print(f"\n💾 SALVANDO EMENDAS NO BANCO DE DADOS")
            print("-" * 50)
            
            # Etapa 4: Processar e salvar cada emenda
            for i, (idx, linha) in enumerate(df_emendas.iterrows(), 1):
                print(f"   📄 Processando {i}/{len(df_emendas)}: {linha.get('codigo_emenda', 'N/A')}")
                
                try:
                    # Salvar emenda
                    emenda = self.salvar_emenda_csv(linha, db)
                    if emenda:
                        resultados['emendas_salvas'] += 1
                        
                        if emenda.deputado_id:
                            resultados['emendas_com_autor'] += 1
                        
                        if emenda.gcs_url:
                            resultados['emendas_com_gcs'] += 1
                        
                        # Acumular valores
                        valor_empenhado = self.limpar_valor_monetario(linha.get('valor_empenhado')) or 0
                        valor_liquidado = self.limpar_valor_monetario(linha.get('valor_liquidado')) or 0
                        valor_pago = self.limpar_valor_monetario(linha.get('valor_pago')) or 0
                        
                        resultados['valor_total_empenhado'] += valor_empenhado
                        resultados['valor_total_liquidado'] += valor_liquidado
                        resultados['valor_total_pago'] += valor_pago
                    
                    # Rate limiting para não sobrecarregar o banco
                    if i % 10 == 0:
                        db.commit()
                        time.sleep(0.1)  # Pequena pausa
                    
                except Exception as e:
                    print(f"      ❌ Erro ao processar emenda: {e}")
                    resultados['erros'] += 1
                    continue
            
            # Commit final
            db.commit()
            
            # Limpar arquivos temporários
            try:
                zip_path.unlink()
                csv_path.unlink()
                print(f"🧹 Arquivos temporários limpos")
            except:
                pass
            
        except Exception as e:
            print(f"❌ Erro geral na coleta: {e}")
            resultados['erros'] += 1
        
        return resultados

    def gerar_ranking_emendas_csv(self, ano: int, db: Session):
        """
        Gera ranking de emendas por deputado (dados do CSV)
        """
        try:
            print(f"\n🏆 GERANDO RANKING DE EMENDAS - {ano}")
            print("=" * 40)
            
            # Consulta para ranking
            ranking_query = db.query(
                EmendaParlamentar.deputado_id,
                func.count(EmendaParlamentar.id).label('quantidade'),
                func.sum(EmendaParlamentar.valor_emenda).label('valor_total'),
                func.avg(EmendaParlamentar.valor_emenda).label('valor_medio')
            ).filter(
                EmendaParlamentar.ano == ano,
                EmendaParlamentar.deputado_id.isnot(None),
                EmendaParlamentar.valor_emenda > 0
            ).group_by(EmendaParlamentar.deputado_id).all()
            
            # Salvar ranking
            for i, (deputado_id, quantidade, valor_total, valor_medio) in enumerate(ranking_query, 1):
                ranking = RankingEmendas(
                    deputado_id=deputado_id,
                    ano_referencia=ano,
                    quantidade_emendas=quantidade,
                    valor_total_emendas=valor_total or 0,
                    valor_medio_emenda=valor_medio or 0,
                    ranking_quantidade=i
                )
                db.add(ranking)
            
            db.commit()
            print(f"✅ Ranking gerado com {len(ranking_query)} deputados")
            
        except Exception as e:
            print(f"❌ Erro ao gerar ranking: {e}")
            db.rollback()

def main():
    """
    Função principal para execução standalone
    """
    print("💰 COLETA DE EMENDAS ORÇAMENTÁRIAS - Download CSV Oficial")
    print("=" * 70)
    
    # Usar o utilitário db_utils para obter sessão do banco
    from models.db_utils import get_db_session
    
    db_session = get_db_session()
    
    try:
        coletor = ColetorEmendasDownload()
        
        # Coletar emendas de 2025 (ano atual)
        ano_atual = datetime.now().year
        print(f"\n🎯 COLETANDO EMENDAS DE {ano_atual}")
        print("=" * 40)
        
        resultados = coletor.coletar_emendas_ano(ano_atual, db_session)
        
        print(f"\n📋 RESUMO DA COLETA - {ano_atual}")
        print("=" * 30)
        print(f"📄 Emendas encontradas: {resultados['emendas_encontradas']}")
        print(f"💾 Emendas salvas: {resultados['emendas_salvas']}")
        print(f"👥 Com autor identificado: {resultados['emendas_com_autor']}")
        print(f"📁 Com upload GCS: {resultados['emendas_com_gcs']}")
        print(f"💰 Valor total empenhado: R$ {resultados['valor_total_empenhado']:,.2f}")
        print(f"💰 Valor total liquidado: R$ {resultados['valor_total_liquidado']:,.2f}")
        print(f"💰 Valor total pago: R$ {resultados['valor_total_pago']:,.2f}")
        print(f"❌ Erros: {resultados['erros']}")
        
        # Gerar ranking
        if resultados['emendas_salvas'] > 0:
            coletor.gerar_ranking_emendas_csv(ano_atual, db_session)
        
        print(f"\n✅ Coleta de emendas via download CSV concluída!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A COLETA: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
