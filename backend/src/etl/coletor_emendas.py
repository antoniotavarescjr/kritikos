#!/usr/bin/env python3
"""
Coletor de Emendas Parlamentares - Versão Genérica e Configurável
Foco em matching exato de nomes usando normalização robusta
Processamento direto do CSV sem dependência do Storage
Ano configurável via config.py
"""

import sys
import os
import zipfile
import requests
import pandas as pd
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

# --- Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(SRC_DIR))

# Importar modelos e utilitários
from src.models.database import get_db
from src.models.politico_models import Deputado
from src.models.emenda_models import EmendaParlamentar, DetalheEmenda, RankingEmendas
from src.utils.normalizacao_utils import normalizar_nome_para_matching, criar_indice_nomes_normalizados, buscar_deputado_por_nome_normalizado
from src.etl.config import (
    get_emendas_config, 
    get_ano_emendas, 
    get_descricao_emendas, 
    get_url_download_emendas,
    emendas_habilitadas,
    get_periodo_emendas
)

# Usar logger global (já configurado no pipeline)
logger = logging.getLogger(__name__)

class ColetorEmendasGenerico:
    """
    Coletor genérico de emendas com ano configurável
    """
    
    def __init__(self):
        """Inicializa o coletor com configurações dinâmicas"""
        if not emendas_habilitadas():
            raise ValueError("Coleta de emendas está desabilitada nas configurações")
        
        self.ano = get_ano_emendas()
        self.download_url = get_url_download_emendas()
        self.config = get_emendas_config()
        self.temp_dir = Path(self.config.get('temp_dir', 'temp')).resolve()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Estatísticas
        self.estatisticas = {
            'ano_coleta': self.ano,
            'emendas_encontradas': 0,
            'emendas_salvas': 0,
            'emendas_com_match': 0,
            'emendas_sem_match': 0,
            'valor_total': 0.0,
            'valor_com_match': 0.0,
            'valor_sem_match': 0.0,
            'erros': 0,
            'data_inicio': datetime.now(),
            'data_fim': None
        }
        
        logger.info(f"Coletor de emendas inicializado - Ano: {self.ano}")
        logger.info(f"Diretório temporário: {self.temp_dir}")
        logger.info(f"URL de download: {self.download_url}")
    
    def baixar_arquivo_emendas(self) -> Optional[Path]:
        """Baixa o arquivo ZIP de emendas do Portal da Transparência"""
        logger.info(f"Baixando arquivo de emendas: {self.download_url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/zip,application/octet-stream,*/*',
            }
            
            response = requests.get(self.download_url, headers=headers, timeout=300, allow_redirects=True)
            response.raise_for_status()
            
            # Verificar se é HTML (erro)
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                logger.error("❌ Download retornou HTML em vez de ZIP")
                return None
            
            # Verificar tamanho mínimo
            if len(response.content) < 1000000:  # 1MB
                logger.error(f"❌ Arquivo muito pequeno: {len(response.content)} bytes")
                return None
            
            # Salvar arquivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_path = self.temp_dir / f"emendas_{self.ano}_{timestamp}.zip"
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"✅ Download concluído: {zip_path} ({len(response.content):,} bytes)")
            return zip_path
            
        except Exception as e:
            logger.error(f"❌ Erro no download: {e}")
            return None
    
    def extrair_csv_do_zip(self, zip_path: Path) -> Optional[Path]:
        """Extrai o arquivo CSV do ZIP baixado"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                arquivos = zip_ref.namelist()
                logger.info(f"📁 Arquivos no ZIP: {arquivos}")
                
                # Procurar arquivo CSV esperado
                csv_file = None
                arquivo_esperado = self.config.get('arquivo_csv_esperado', 'EmendasParlamentares.csv')
                
                for arquivo in arquivos:
                    if arquivo.lower().endswith('.csv') and arquivo_esperado.lower() in arquivo.lower():
                        csv_file = arquivo
                        break
                
                if not csv_file:
                    # Se não encontrar o esperado, pega qualquer CSV
                    for arquivo in arquivos:
                        if arquivo.lower().endswith('.csv'):
                            csv_file = arquivo
                            break
                
                if not csv_file:
                    logger.error("❌ Nenhum arquivo CSV encontrado no ZIP")
                    return None
                
                # Extrair CSV
                zip_ref.extract(csv_file, self.temp_dir)
                csv_path = self.temp_dir / csv_file
                
                logger.info(f"✅ CSV extraído: {csv_path}")
                return csv_path
                
        except Exception as e:
            logger.error(f"❌ Erro ao extrair CSV: {e}")
            return None
    
    def ler_csv_emendas_ano(self, csv_path: Path) -> pd.DataFrame:
        """Lê o arquivo CSV filtrando apenas emendas do ano configurado"""
        logger.info(f"📊 Lendo CSV: {csv_path}")
        logger.info(f"🎯 Filtrando emendas do ano: {self.ano}")
        
        try:
            # Tentar diferentes encodings e separadores
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            separators = [';', ',', '\t']
            df = None
            
            for encoding in encodings:
                for sep in separators:
                    try:
                        df = pd.read_csv(csv_path, encoding=encoding, sep=sep, decimal=',', thousands='.')
                        logger.info(f"✅ CSV lido: encoding={encoding}, separador={sep}")
                        break
                    except Exception:
                        continue
                if df is not None:
                    break
            
            if df is None:
                raise Exception("Não foi possível ler o CSV")
            
            logger.info(f"📊 Dimensões originais: {df.shape}")
            
            # Padronizar nomes de colunas
            df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace(r'[^\w_]', '', regex=True)
            logger.info(f"📋 Colunas padronizadas: {list(df.columns)}")
            
            # Mapear colunas flexivelmente
            column_mapping = self._mapear_colunas_csv(df.columns)
            if column_mapping:
                df = df.rename(columns=column_mapping)
                logger.info(f"📋 Colunas mapeadas: {list(df.columns)}")
            
            # Filtrar apenas emendas do ano configurado
            ano_col = None
            for col in ['ano', 'Ano', 'Ano_da_Emenda', 'Ano Emenda']:
                if col in df.columns:
                    ano_col = col
                    break
            
            if ano_col:
                df_ano = df[df[ano_col] == self.ano].copy()
                logger.info(f"📊 Filtradas {len(df_ano)} emendas de {self.ano} (de {len(df)} totais)")
                return df_ano
            else:
                logger.warning(f"⚠️ Coluna de ano não encontrada, usando todos os dados")
                return df
                
        except Exception as e:
            logger.error(f"❌ Erro ao ler CSV: {e}")
            return pd.DataFrame()
    
    def _mapear_colunas_csv(self, columns: list) -> dict:
        """Mapeia colunas do CSV para nomes esperados"""
        mapping = {}
        
        column_map = {
            # Identificação
            'Autor': 'autor',
            'Nome_do_Autor': 'autor',
            'Nome do Autor da Emenda': 'autor',
            'Ano': 'ano',
            'Ano_da_Emenda': 'ano',
            'Ano Emenda': 'ano',
            'Número_Emenda': 'numero_emenda',
            'Número da emenda': 'numero_emenda',
            'Código_da_Emenda': 'codigo_emenda',
            'Código da Emenda': 'codigo_emenda',
            'Código_do_Autor_da_Emenda': 'codigo_autor_emenda',
            'Código do Autor da Emenda': 'codigo_autor_emenda',
            
            # Tipo
            'Tipo_Emenda': 'tipo_emenda',
            'Tipo de Emenda': 'tipo_emenda',
            
            # Financeiros
            'Valor_Empenhado': 'valor_empenhado',
            'Valor Empenhado': 'valor_empenhado',
            'Valor_Liquidado': 'valor_liquidado',
            'Valor Liquidado': 'valor_liquidado',
            'Valor_Pago': 'valor_pago',
            'Valor Pago': 'valor_pago',
            
            # Localização
            'UF': 'uf',
            'Função': 'funcao',
            'Nome_Função': 'funcao',
            'Subfunção': 'subfuncao',
            'Nome_Subfunção': 'subfuncao',
            'Localidade_do_Gasto': 'localidade',
            'Localidade do gasto': 'localidade',
            'Localidade de aplicação do recurso': 'localidade',
            'Município': 'municipio',
            
            # Códigos
            'Código_Função': 'codigo_funcao',
            'Código_Subfunção': 'codigo_subfuncao',
            'Nome_Programa': 'programa',
            'Nome_Ação': 'acao'
        }
        
        for col in columns:
            if col in column_map:
                mapping[col] = column_map[col]
        
        return mapping
    
    def limpar_valor_monetario(self, valor) -> float:
        """Converte valor monetário no formato brasileiro para float"""
        if not valor or pd.isna(valor):
            return 0.0
        
        try:
            valor_str = str(valor).strip()
            
            # Remover R$ se existir
            valor_str = valor_str.replace('R$', '').strip()
            
            # Substituir vírgula por ponto (decimal brasileiro)
            valor_str = valor_str.replace(',', '.')
            
            # Converter para float
            return float(valor_str)
        except (ValueError, AttributeError):
            return 0.0
    
    def salvar_emenda(self, linha: pd.Series, db: Session, indice_nomes: dict) -> Optional[EmendaParlamentar]:
        """Salva emenda do CSV no banco usando matching otimizado"""
        try:
            # Extrair dados básicos
            codigo_emenda = str(linha.get('codigo_emenda', ''))
            if not codigo_emenda:
                return None
            
            # Verificar se já existe
            existente = db.query(EmendaParlamentar).filter(
                EmendaParlamentar.api_camara_id == codigo_emenda
            ).first()
            
            if existente:
                return existente
            
            # Dados da emenda
            ano = int(linha.get('ano', self.ano))
            tipo_emenda_csv = linha.get('tipo_emenda', '')
            nome_autor = linha.get('autor', '')
            
            # Ignorar bancadas se configurado
            if self.config.get('ignorar_bancadas', True) and 'bancada' in nome_autor.lower():
                return None
            
            # Buscar deputado por código do autor (matching 100% preciso)
            codigo_autor_csv = linha.get('codigo_autor_emenda', '')
            
            # Pular códigos inválidos
            if not codigo_autor_csv or codigo_autor_csv in ['S/I', '', 'Sem informação']:
                if self.config.get('mostrar_progresso', True):
                    logger.warning(f"      ❌ Emenda IGNORADA código inválido: {codigo_autor_csv}")
                return None
            
            try:
                codigo_autor_int = int(codigo_autor_csv)
            except (ValueError, TypeError):
                if self.config.get('mostrar_progresso', True):
                    logger.warning(f"      ❌ Emenda IGNORADA código não numérico: {codigo_autor_csv}")
                return None
            
            # Buscar deputado por código do autor
            deputado = db.query(Deputado).filter(
                Deputado.codigo_autor_emenda == codigo_autor_int
            ).first()
            
            if not deputado:
                if self.config.get('mostrar_progresso', True):
                    logger.warning(f"      ❌ Emenda IGNORADA código não encontrado: {codigo_autor_int}")
                return None
            
            deputado_id = deputado.id
            
            # Extrair valores financeiros
            valor_empenhado = self.limpar_valor_monetario(linha.get('valor_empenhado'))
            valor_liquidado = self.limpar_valor_monetario(linha.get('valor_liquidado'))
            valor_pago = self.limpar_valor_monetario(linha.get('valor_pago'))
            
            # Usar o maior valor disponível
            valor_emenda = max(valor_empenhado, valor_liquidado, valor_pago)
            
            # Aplicar valor mínimo se configurado
            valor_minimo = self.config.get('valor_minimo', 0.01)
            if valor_emenda < valor_minimo:
                return None
            
            # Extrair informações adicionais
            funcao = linha.get('funcao', '')
            localidade = linha.get('localidade', '')
            municipio = linha.get('municipio', '')
            uf = linha.get('uf', '')
            
            # Extrair número da emenda
            try:
                numero_emenda = int(linha.get('numero_emenda', 0))
            except (ValueError, TypeError):
                numero_emenda = 0
            
            # Mapear tipo
            tipo_mapeado = self._mapear_tipo_emenda(tipo_emenda_csv)
            
            # Criar emenda
            emenda = EmendaParlamentar(
                api_camara_id=codigo_emenda,
                deputado_id=deputado_id,
                tipo_emenda=tipo_mapeado,
                numero=numero_emenda,
                ano=ano,
                emenda=f"Emenda {tipo_emenda_csv} - {funcao} - {localidade}",
                local=self._extrair_local_emenda(funcao),
                natureza=self._extrair_natureza_emenda(tipo_emenda_csv),
                tema=funcao,
                valor_emenda=valor_emenda,
                beneficiario_principal=localidade,
                situacao='Ativa',
                data_apresentacao=datetime(ano, 1, 1),
                autor=nome_autor,
                partido_autor=None,
                uf_autor=uf,
                url_documento=None,
                
                # Campos financeiros
                valor_empenhado=valor_empenhado,
                valor_liquidado=valor_liquidado,
                valor_pago=valor_pago,
                
                # Campos de localização
                uf_beneficiario=uf,
                municipio_beneficiario=municipio,
                
                # Campos de otimização
                codigo_funcao_api=linha.get('codigo_funcao'),
                codigo_subfuncao_api=linha.get('codigo_subfuncao'),
            )
            
            db.add(emenda)
            db.flush()
            
            # Salvar detalhes
            self._salvar_detalhes_emenda(emenda, linha, db)
            
            # Atualizar estatísticas
            self.estatisticas['emendas_salvas'] += 1
            self.estatisticas['valor_total'] += valor_emenda
            
            if deputado_id:
                self.estatisticas['emendas_com_match'] += 1
                self.estatisticas['valor_com_match'] += valor_emenda
                if self.config.get('mostrar_progresso', True):
                    logger.info(f"      ✅ Emenda salva COM match: {nome_autor} -> ID {deputado_id}")
            else:
                self.estatisticas['emendas_sem_match'] += 1
                self.estatisticas['valor_sem_match'] += valor_emenda
                if self.config.get('mostrar_progresso', True):
                    logger.warning(f"      ⚠️ Emenda salva SEM match: {nome_autor} (normalizado: {nome_autor_normalizado})")
            
            return emenda
            
        except Exception as e:
            logger.error(f"      ❌ Erro ao salvar emenda: {e}")
            self.estatisticas['erros'] += 1
            return None
    
    def _mapear_tipo_emenda(self, tipo_emenda: str) -> str:
        """Mapeia tipos de emenda do CSV para o modelo"""
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
    
    def _extrair_local_emenda(self, funcao: str) -> str:
        """Extrai local da emenda baseado na função"""
        if not funcao:
            return 'OUTROS'
        
        funcao_lower = str(funcao).lower()
        
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
            return str(funcao).upper()
    
    def _extrair_natureza_emenda(self, tipo_emenda: str) -> str:
        """Extrai natureza da emenda baseado no tipo"""
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
    
    def _salvar_detalhes_emenda(self, emenda: EmendaParlamentar, linha: pd.Series, db: Session):
        """Salva detalhes específicos da emenda"""
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
            logger.warning(f"      ⚠️ Erro ao salvar detalhes: {e}")
    
    def gerar_ranking(self, db: Session):
        """Gera ranking de emendas por deputado para o ano configurado"""
        try:
            logger.info(f"🏆 Gerando ranking de emendas {self.ano}...")
            
            # Consulta para ranking
            ranking_query = db.query(
                EmendaParlamentar.deputado_id,
                func.count(EmendaParlamentar.id).label('quantidade'),
                func.sum(EmendaParlamentar.valor_emenda).label('valor_total'),
                func.avg(EmendaParlamentar.valor_emenda).label('valor_medio')
            ).filter(
                EmendaParlamentar.ano == self.ano,
                EmendaParlamentar.deputado_id.isnot(None),
                EmendaParlamentar.valor_emenda > 0
            ).group_by(EmendaParlamentar.deputado_id).all()
            
            # Salvar ranking
            for i, (deputado_id, quantidade, valor_total, valor_medio) in enumerate(ranking_query, 1):
                ranking = RankingEmendas(
                    deputado_id=deputado_id,
                    ano_referencia=self.ano,
                    quantidade_emendas=quantidade,
                    valor_total_emendas=valor_total or 0,
                    valor_medio_emenda=valor_medio or 0,
                    ranking_quantidade=i
                )
                db.add(ranking)
            
            db.commit()
            logger.info(f"✅ Ranking gerado com {len(ranking_query)} deputados")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar ranking: {e}")
            db.rollback()
    
    def coletar_emendas(self, db: Session) -> Dict[str, any]:
        """Executa o processo completo de coleta de emendas"""
        logger.info(f"🚀 Iniciando coleta de emendas {self.ano}")
        logger.info(f"📋 Descrição: {get_descricao_emendas()}")
        
        try:
            # Etapa 1: Baixar arquivo
            zip_path = self.baixar_arquivo_emendas()
            if not zip_path:
                return self.estatisticas
            
            # Etapa 2: Extrair CSV
            csv_path = self.extrair_csv_do_zip(zip_path)
            if not csv_path:
                return self.estatisticas
            
            # Etapa 3: Ler e filtrar CSV
            df_emendas = self.ler_csv_emendas_ano(csv_path)
            self.estatisticas['emendas_encontradas'] = len(df_emendas)
            
            if len(df_emendas) == 0:
                logger.warning(f"⚠️ Nenhuma emenda encontrada para {self.ano}")
                return self.estatisticas
            
            # Etapa 4: Criar índice de nomes para performance
            indice_nomes = criar_indice_nomes_normalizados(db)
            
            # Etapa 5: Processar emendas
            logger.info(f"💾 Processando {len(df_emendas)} emendas de {self.ano}...")
            
            batch_size = self.config.get('batch_size', 50)
            
            for i, (idx, linha) in enumerate(df_emendas.iterrows(), 1):
                if i % 100 == 0 and self.config.get('mostrar_progresso', True):
                    logger.info(f"   📄 Processando {i}/{len(df_emendas)} emendas...")
                
                self.salvar_emenda(linha, db, indice_nomes)
                
                # Commit periódico para não sobrecarregar
                if i % batch_size == 0:
                    db.commit()
            
            # Commit final
            db.commit()
            
            # Etapa 6: Gerar ranking se configurado
            if self.config.get('gerar_ranking', True) and self.estatisticas['emendas_com_match'] > 0:
                self.gerar_ranking(db)
            
            # Limpar arquivos temporários
            try:
                zip_path.unlink()
                csv_path.unlink()
                logger.info("🧹 Arquivos temporários limpos")
            except:
                pass
            
            # Finalizar estatísticas
            self.estatisticas['data_fim'] = datetime.now()
            
            return self.estatisticas
            
        except Exception as e:
            logger.error(f"❌ Erro geral na coleta: {e}")
            self.estatisticas['erros'] += 1
            self.estatisticas['data_fim'] = datetime.now()
            return self.estatisticas
    
    def exibir_resumo_final(self):
        """Exibe resumo estatístico final"""
        duracao = self.estatisticas['data_fim'] - self.estatisticas['data_inicio']
        
        logger.info("\n" + "="*70)
        logger.info(f"📊 RESUMO FINAL - COLETA DE EMENDAS {self.ano}")
        logger.info("="*70)
        
        total = self.estatisticas['emendas_salvas']
        com_match = self.estatisticas['emendas_com_match']
        sem_match = self.estatisticas['emendas_sem_match']
        
        logger.info(f"📄 Emendas encontradas: {self.estatisticas['emendas_encontradas']}")
        logger.info(f"💾 Emendas salvas: {total}")
        logger.info(f"✅ Com match de deputado: {com_match}")
        logger.info(f"❌ Sem match de deputado: {sem_match}")
        
        if total > 0:
            percentual_match = (com_match / total) * 100
            logger.info(f"📈 Taxa de matching: {percentual_match:.1f}%")
        
        logger.info(f"💰 Valor total: R$ {self.estatisticas['valor_total']:,.2f}")
        logger.info(f"💰 Valor com match: R$ {self.estatisticas['valor_com_match']:,.2f}")
        logger.info(f"💰 Valor sem match: R$ {self.estatisticas['valor_sem_match']:,.2f}")
        logger.info(f"❌ Erros: {self.estatisticas['erros']}")
        logger.info(f"⏱️ Duração: {duracao}")
        
        logger.info("="*70)


def main():
    """Função principal"""
    print("💰 COLETOR DE EMENDAS PARLAMENTARES - VERSÃO GENÉRICA")
    print("🎯 Foco: Matching exato com normalização robusta")
    print("⚙️ Ano configurável via config.py")
    print("="*70)
    
    # Obter sessão do banco
    db = next(get_db())
    
    try:
        # Criar coletor e executar
        coletor = ColetorEmendasGenerico()
        resultados = coletor.coletar_emendas(db)
        
        # Exibir resumo
        coletor.exibir_resumo_final()
        
        logger.info(f"✅ Coleta de emendas {coletor.ano} concluída!")
        
    except Exception as e:
        logger.error(f"❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
