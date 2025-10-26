#!/usr/bin/env python3
"""
Script de Investigação da Estrutura do Google Cloud Storage
Analisa a estrutura real dos arquivos para entender padrões de nomes
Objetivo: Descobrir como identificar corretamente os tipos de documentos (PL, PEC, REQ, etc.)

Seguro: Apenas leitura, sem modificações no storage
"""

import sys
from pathlib import Path
import os
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

# Adicionar o diretório src ao sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
sys.path.append(str(SRC_DIR))

from utils.gcs_utils import get_gcs_manager

class InvestigadorGCS:
    """
    Classe para investigar a estrutura real dos arquivos no GCS
    Analisa padrões de nomes para entender como extrair tipos corretamente
    """
    
    def __init__(self):
        """Inicializa o investigador do GCS"""
        self.gcs_manager = get_gcs_manager()
        
        # Estatísticas da investigação
        self.estatisticas = {
            'total_arquivos': 0,
            'estruturas_encontradas': {},
            'padroes_identificados': {},
            'exemplos_estrutura': [],
            'tipos_encontrados': {},
            'tamanhos_medios': {},
            'profundidades': {}
        }
        
        # Amostra para análise (primeiros N arquivos)
        self.tamanho_amostra = 20
        self.tamanho_analise_completa = 50
        
        print("🔍 INVESTIGAÇÃO DA ESTRUTURA DO GCS")
        print("=" * 50)
        print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🎯 Objetivo: Descobrir estrutura real dos arquivos no storage")
        print(f"📊 Amostra: Primeiros {self.tamanho_amostra} arquivos para análise")
        print(f"📋 Análise: {self.tamanho_analise_completa} arquivos para padrões")
    
    def listar_todos_arquivos(self):
        """
        Lista todos os arquivos no bucket GCS
        
        Returns:
            List: Lista de blobs encontrados
        """
        print(f"\n📁 LISTANDO TODOS OS ARQUIVOS...")
        print("=" * 30)
        
        try:
            blobs = self.gcs_manager.list_blobs()
            
            if not blobs:
                print("✅ Bucket está vazio!")
                return []
            
            self.estatisticas['total_arquivos'] = len(blobs)
            print(f"📊 Total de arquivos encontrados: {self.estatisticas['total_arquivos']:,}")
            
            return blobs
            
        except Exception as e:
            print(f"❌ Erro ao listar arquivos: {e}")
            return []
    
    def analisar_estrutura_blob(self, blob_name: str, profundidade_maxima: int = 10) -> dict:
        """
        Analisa a estrutura do caminho de um blob
        
        Args:
            blob_name: Nome do blob
            profundidade_maxima: Profundidade máxima para análise
            
        Returns:
            Dict: Informações detalhadas da estrutura
        """
        try:
            partes = blob_name.split('/')
            profundidade = len(partes)
            
            # Analisar cada parte do caminho
            estrutura_analizada = {
                'blob_name': blob_name,
                'partes': partes,
                'profundidade': profundidade,
                'tipo_estrutura': self.classificar_estrutura(partes),
                'possivel_tipo_documento': self.extrair_tipo_possivel(partes),
                'tamanho_bytes': getattr(blob, 'size', 0),
                'content_type': getattr(blob, 'content_type', 'unknown'),
                'updated': getattr(blob, 'updated', None)
            }
            
            # Extrair informações adicionais
            if profundidade >= 2:
                estrutura_analizada['diretorio_base'] = partes[0]
                estrutura_analyzed['subdiretorio'] = '/'.join(partes[1:-1]) if profundidade > 2 else ''
            
            if profundidade >= 1:
                estrutura_analyzed['nome_arquivo'] = partes[-1]
            
            return estrutura_analyzed
            
        except Exception as e:
            print(f"   ❌ Erro ao analisar {blob_name}: {e}")
            return None
    
    def classificar_estrutura(self, partes: list) -> str:
        """
        Classifica o tipo de estrutura do caminho
        
        Args:
            partes: Partes do caminho do blob
            
        Returns:
            str: Tipo de estrutura encontrado
        """
        if len(partes) == 1:
            return "raiz_unica"
        elif len(partes) == 2:
            return "diretorio_arquivo"
        elif len(partes) == 3:
            return "subdiretorio_arquivo"
        elif len(partes) == 4:
            return "subsubdiretorio_arquivo"
        elif len(partes) >= 5:
            return "estrutura_profunda"
        else:
            return "desconhecida"
    
    def extrair_tipo_possivel(self, partes: list) -> str:
        """
        Extrai tipo de documento possível das partes do caminho
        
        Args:
            partes: Partes do caminho do blob
            
        Returns:
            str: Tipo possível de documento
        """
        if not partes:
            return "vazio"
        
        # Estratégias de extração baseadas em posições comuns
        estrategias = []
        
        # Estratégia 1: Última parte (nome do arquivo)
        try:
            nome_arquivo = partes[-1]
            if '_' in nome_arquivo:
                # Formato: PL_12345_2025.json
                tipo = nome_arquivo.split('_')[0]
                if tipo and len(tipo) >= 2:
                    estrategias.append(('nome_arquivo', tipo))
        except:
            pass
        
        # Estratégia 2: Penúltima parte (diretório de tipo)
        try:
            if len(partes) >= 2:
                diretorio_tipo = partes[-2]
                if diretorio_tipo.isupper() and len(diretorio_tipo) >= 2:
                    estrategias.append(('diretorio_tipo', diretorio_tipo))
        except:
            pass
        
        # Estratégia 3: Terceira parte (subdiretorio)
        try:
            if len(partes) >= 3:
                subdiretorio = partes[-3]
                if subdiretorio.isupper() and len(subdiretorio) >= 2:
                    estrategias.append(('subdiretorio', subdiretorio))
        except:
            pass
        
        # Estratégia 4: Buscar em todas as partes
        try:
            for i, parte in enumerate(partes):
                if parte.isupper() and len(parte) >= 2 and len(parte) <= 10:
                    estrategias.append((f'parte_{i}', parte))
        except:
            pass
        
        # Retornar a estratégia mais confiável
        if estrategias:
            # Priorizar estratégias mais comuns
            prioridade = ['nome_arquivo', 'diretorio_tipo', 'subdiretorio']
            for prio in prioridade:
                for estrategia, tipo in estrategias:
                    if estrategia == prio:
                        return tipo
            
            # Se não encontrar prioridade, retornar a primeira
            return estrategias[0][1]
        
        return "desconhecido"
    
    def analisar_amostra_inicial(self, blobs: list):
        """
        Analisa a amostra inicial de arquivos
        
        Args:
            blobs: Lista de blobs para analisar
        """
        print(f"\n📊 ANÁLISE DA AMOSTRA INICIAL (primeiros {self.tamanho_amostra})")
        print("=" * 50)
        
        for i, blob in enumerate(blobs[:self.tamanho_amostra]):
            try:
                print(f"   📄 {i+1:2d}. {blob.name}")
                
                # Analisar estrutura
                estrutura = self.analisar_estrutura_blob(blob.name)
                if estrutura:
                    self.estatisticas['exemplos_estrutura'].append(estrutura)
                    
                    # Contar estruturas
                    tipo_estrutura = estrutura['tipo_estrutura']
                    self.estatisticas['estruturas_encontradas'][tipo_estrutura] = \
                        self.estatisticas['estruturas_encontradas'].get(tipo_estrutura, 0) + 1
                    
                    # Contar profundidades
                    profundidade = estrutura['profundidade']
                    self.estatisticas['profundidades'][profundidade] = \
                        self.estatisticas['profundidades'].get(profundidade, 0) + 1
                    
                    # Contar tipos possíveis
                    tipo_possivel = estrutura['possivel_tipo_documento']
                    if tipo_possivel != "desconhecido":
                        self.estatisticas['tipos_encontrados'][tipo_possivel] = \
                            self.estatisticas['tipos_encontrados'].get(tipo_possivel, 0) + 1
                
            except Exception as e:
                print(f"      ❌ Erro ao analisar {blob.name}: {e}")
        
        print(f"\n📋 RESUMO DA AMOSTRA INICIAL:")
        print(f"   📊 Arquivos analisados: {len(blobs[:self.tamanho_amostra])}")
        print(f"   📂 Estruturas encontradas: {dict(self.estatisticas['estruturas_encontradas'])}")
        print(f"   📏 Profundidades: {dict(self.estatisticas['profundidades'])}")
        print(f"   📋 Tipos possíveis: {dict(self.estatisticas['tipos_encontrados'])}")
    
    def analisar_padroes_completos(self, blobs: list):
        """
        Analisa padrões completos em amostra maior
        
        Args:
            blobs: Lista de blobs para analisar
        """
        print(f"\n🔍 ANÁLISE DE PADRÕES COMPLETOS (primeiros {self.tamanho_analise_completa})")
        print("=" * 50)
        
        # Analisar amostra maior
        for i, blob in enumerate(blobs[:self.tamanho_analise_completa]):
            try:
                estrutura = self.analisar_estrutura_blob(blob.name)
                if estrutura:
                    # Analisar padrões específicos
                    self.analisar_padroes_especificos(estrutura)
            except Exception as e:
                print(f"      ❌ Erro ao analisar padrão {i+1}: {e}")
        
        print(f"\n📋 PADRÕES IDENTIFICADOS:")
        for padrao, info in self.estatisticas['padroes_identificados'].items():
            print(f"   📋 {padrao}: {info}")
    
    def analisar_padroes_especificos(self, estrutura: dict):
        """
        Analisa padrões específicos na estrutura
        
        Args:
            estrutura: Estrutura analisada do blob
        """
        # Padrão 1: Estrutura de diretórios
        if estrutura['profundidade'] >= 3:
            diretorio_base = estrutura.get('diretorio_base', '')
            if diretorio_base:
                self.estatisticas['padroes_identificados']['diretorio_base'] = \
                    self.estatisticas['padroes_identificados'].get('diretorio_base', set())
                self.estatisticas['padroes_identificados']['diretorio_base'].add(diretorio_base)
        
        # Padrão 2: Extensões de arquivos
        nome_arquivo = estrutura.get('nome_arquivo', '')
        if nome_arquivo and '.' in nome_arquivo:
            extensao = nome_arquivo.split('.')[-1].lower()
            self.estatisticas['padroes_identificados']['extensoes'] = \
                self.estatisticas['padroes_identificados'].get('extensoes', set())
            self.estatisticas['padroes_identificados']['extensoes'].add(extensao)
        
        # Padrão 3: Formatos de nomes
        if '_' in nome_arquivo:
            partes_nome = nome_arquivo.split('_')
            if len(partes_nome) >= 3:
                formato = '_'.join(partes_nome[:2]) + '_*'
                self.estatisticas['padroes_identificados']['formatos_nome'] = \
                    self.estatisticas['padroes_identificados'].get('formatos_nome', set())
                self.estatisticas['padroes_identificados']['formatos_nome'].add(formato)
    
    def calcular_tamanhos_medios(self, blobs: list):
        """
        Calcula tamanhos médios por tipo
        
        Args:
            blobs: Lista de blobs para analisar
        """
        print(f"\n💾 ANÁLISE DE TAMANHOS (primeiros {self.tamanho_analise_completa})")
        print("=" * 40)
        
        tamanhos_por_tipo = {}
        contagem_por_tipo = {}
        
        for blob in blobs[:self.tamanho_analise_completa]:
            try:
                tamanho = getattr(blob, 'size', 0)
                estrutura = self.analisar_estrutura_blob(blob.name)
                
                if estrutura:
                    tipo_possivel = estrutura['possivel_tipo_documento']
                    if tipo_possivel != "desconhecido":
                        tamanhos_por_tipo[tipo_possivel] = tamanhos_por_tipo.get(tipo_possivel, 0) + tamanho
                        contagem_por_tipo[tipo_possivel] = contagem_por_tipo.get(tipo_possivel, 0) + 1
            except Exception as e:
                print(f"      ❌ Erro ao analisar tamanho: {e}")
        
        print(f"📊 Tamanhos médios por tipo:")
        for tipo, tamanho_total in sorted(tamanhos_por_tipo.items()):
            contagem = contagem_por_tipo.get(tipo, 0)
            tamanho_medio = tamanho_total / contagem if contagem > 0 else 0
            tamanho_mb = tamanho_medio / (1024 * 1024)
            
            self.estatisticas['tamanhos_medios'][tipo] = tamanho_mb
            print(f"   📋 {tipo}: {tamanho_mb:.2f} MB médio ({contagem:,} arquivos)")
    
    def gerar_relatorio_completo(self):
        """
        Gera relatório completo da investigação
        """
        print(f"\n📋 RELATÓRIO COMPLETO DA INVESTIGAÇÃO")
        print("=" * 50)
        print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        print(f"\n📊 ESTATÍSTICAS GERAIS:")
        print(f"   📁 Total de arquivos: {self.estatisticas['total_arquivos']:,}")
        print(f"   📂 Estruturas encontradas: {len(self.estatisticas['estruturas_encontradas'])}")
        print(f"   📏 Profundidades máximas: {max(self.estatisticas['profundidades'].keys()) if self.estatisticas['profundidades'] else 0}")
        print(f"   📋 Tipos encontrados: {len(self.estatisticas['tipos_encontrados'])}")
        print(f"   📋 Padrões identificados: {len(self.estatisticas['padroes_identificados'])}")
        
        print(f"\n📂 ESTRUTURAS ENCONTRADAS:")
        for estrutura, quantidade in sorted(self.estatisticas['estruturas_encontradas'].items()):
            print(f"   📁 {estrutura}: {quantidade:,} arquivos")
        
        print(f"\n📏 PROFUNDIDADES:")
        for profundidade, quantidade in sorted(self.estatisticas['profundidades'].items()):
            print(f"   📏 Profundidade {profundidade}: {quantidade:,} arquivos")
        
        print(f"\n📋 TIPOS DE DOCUMENTOS:")
        for tipo, quantidade in sorted(self.estatisticas['tipos_encontrados'].items()):
            tamanho_mb = self.estatisticas['tamanhos_medios'].get(tipo, 0)
            print(f"   📋 {tipo}: {quantidade:,} arquivos ({tamanho_mb:.2f} MB médio)")
        
        print(f"\n📋 PADRÕES IDENTIFICADOS:")
        for padrao, conjunto in self.estatisticas['padroes_identificados'].items():
            print(f"   📋 {padrao}: {sorted(list(conjunto))}")
        
        # Salvar relatório em arquivo
        self.salvar_relatorio_arquivo()
    
    def salvar_relatorio_arquivo(self):
        """
        Salva relatório completo em arquivo para análise posterior
        """
        try:
            arquivo_relatorio = Path(__file__).resolve().parent / 'relatorio_investigacao_gcs.md'
            
            with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
                f.write("# RELATÓRIO DE INVESTIGAÇÃO - ESTRUTURA GCS\n\n")
                f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Total de arquivos: {self.estatisticas['total_arquivos']}\n\n")
                
                f.write("## ESTATÍSTICAS GERAIS\n\n")
                f.write(f"- Total de arquivos: {self.estatisticas['total_arquivos']:,}\n")
                f.write(f"- Estruturas encontradas: {len(self.estatisticas['estruturas_encontradas'])}\n")
                f.write(f"- Profundidades máximas: {max(self.estatisticas['profundidades'].keys()) if self.estatisticas['profundidades'] else 0}\n")
                f.write(f"- Tipos encontrados: {len(self.estatisticas['tipos_encontrados'])}\n")
                f.write(f"- Padrões identificados: {len(self.estatisticas['padroes_identificados'])}\n\n")
                
                f.write("## ESTRUTURAS ENCONTRADAS\n\n")
                for estrutura, quantidade in sorted(self.estatisticas['estruturas_encontradas'].items()):
                    f.write(f"- {estrutura}: {quantidade:,} arquivos\n")
                f.write("\n")
                
                f.write("## PROFUNDIDADES\n\n")
                for profundidade, quantidade in sorted(self.estatisticas['profundidades'].items()):
                    f.write(f"- Profundidade {profundidade}: {quantidade:,} arquivos\n")
                f.write("\n")
                
                f.write("## TIPOS DE DOCUMENTOS\n\n")
                for tipo, quantidade in sorted(self.estatisticas['tipos_encontrados'].items()):
                    tamanho_mb = self.estatisticas['tamanhos_medios'].get(tipo, 0)
                    f.write(f"- {tipo}: {quantidade:,} arquivos ({tamanho_mb:.2f} MB médio)\n")
                f.write("\n")
                
                f.write("## PADRÕES IDENTIFICADOS\n\n")
                for padrao, conjunto in self.estatisticas['padroes_identificados'].items():
                    f.write(f"- {padrao}: {sorted(list(conjunto))}\n")
                f.write("\n")
                
                f.write("## EXEMPLOS DE ESTRUTURA\n\n")
                for i, estrutura in enumerate(self.estatisticas['exemplos_estrutura'][:5]):
                    f.write(f"### Exemplo {i+1}\n")
                    f.write(f"- Blob: {estrutura['blob_name']}\n")
                    f.write(f"- Estrutura: {' -> '.join(estrutura['partes'])}\n")
                    f.write(f"- Profundidade: {estrutura['profundidade']}\n")
                    f.write(f"- Tipo estrutura: {estrutura['tipo_estrutura']}\n")
                    f.write(f"- Tipo possível: {estrutura['possivel_tipo_documento']}\n")
                    f.write(f"- Tamanho: {estrutura['tamanho_bytes']} bytes\n")
                    f.write("\n")
            
            print(f"✅ Relatório salvo em: {arquivo_relatorio}")
            
        except Exception as e:
            print(f"❌ Erro ao salvar relatório: {e}")
    
    def executar_investigacao(self):
        """
        Executa a investigação completa do GCS
        """
        print("🚀 INICIANDO INVESTIGAÇÃO COMPLETA DO GCS...")
        print("=" * 50)
        
        try:
            # Listar todos os arquivos
            blobs = self.listar_todos_arquivos()
            
            if not blobs:
                print("✅ Bucket está vazio - investigação concluída")
                return
            
            # Análise da amostra inicial
            self.analisar_amostra_inicial(blobs)
            
            # Análise de padrões completos
            self.analisar_padroes_completos(blobs)
            
            # Cálculo de tamanhos médios
            self.calcular_tamanhos_medios(blobs)
            
            # Gerar relatório completo
            self.gerar_relatorio_completo()
            
            print(f"\n✅ Investigação concluída com sucesso!")
            print(f"📋 Relatório salvo para análise detalhada")
            
        except Exception as e:
            print(f"❌ Erro durante investigação: {e}")

def main():
    """
    Função principal da investigação
    """
    print("🔍 INVESTIGAÇÃO DA ESTRUTURA DO GCS")
    print("=" * 60)
    print("Objetivo: Descobrir estrutura real dos arquivos no storage")
    print("Segurança: Apenas leitura, sem modificações permanentes")
    
    # Inicializar GCS Manager
    gcs_manager = get_gcs_manager()
    
    if not gcs_manager or not gcs_manager.is_available():
        print("❌ GCS não está disponível!")
        print("Verifique suas credenciais e configuração.")
        return
    
    print(f"✅ GCS Manager inicializado - Bucket: {gcs_manager.bucket_name}")
    
    try:
        # Criar investigador
        investigador = InvestigadorGCS()
        
        # Executar investigação completa
        investigador.executar_investigacao()
        
    except Exception as e:
        print(f"\n❌ Erro durante investigação: {e}")
        
    finally:
        print("\n🔚 Investigação finalizada.")

if __name__ == "__main__":
    main()
