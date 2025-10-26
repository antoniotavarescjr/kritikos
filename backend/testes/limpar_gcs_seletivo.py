#!/usr/bin/env python3
"""
Script de Limpeza Seletiva do Google Cloud Storage do Kritikos
Remove apenas documentos de tipos irrelevantes (REQ, SUG, RIC, etc.) 
mantendo apenas os tipos prioritários (PL, PEC, PLP, MPV, etc.)

Objetivo: Reduzir custos de storage mantendo apenas dados valiosos
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

class LimpezaSeletivaGCS:
    """
    Classe para limpeza seletiva do GCS
    Remove apenas documentos irrelevantes mantendo os prioritários
    """
    
    def __init__(self):
        """Inicializa o gerenciador de limpeza seletiva"""
        self.gcs_manager = get_gcs_manager()
        
        # Tipos de documentos prioritários (MANTER)
        self.tipos_manter = ['PL', 'PEC', 'PLP', 'MPV', 'PDC', 'PLV', 'PRC']
        
        # Tipos de documentos irrelevantes (REMOVER)
        self.tipos_remover = ['REQ', 'SUG', 'RIC', 'IND', 'PRL', 'MSC', 'PCR', 'REQ']
        
        # Estatísticas
        self.estatisticas = {
            'total_antes': 0,
            'total_depois': 0,
            'removidos': 0,
            'mantidos': 0,
            'erros': 0,
            'tipos_removidos': {},
            'tipos_mantidos': {},
            'economia_mb': 0
        }
        
        print("🧹 LIMPEZA SELETIVA DO GOOGLE CLOUD STORAGE KRITIKOS")
        print("=" * 60)
        print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🎯 Objetivo: Remover documentos irrelevantes mantendo apenas os prioritários")
        print(f"📋 Tipos a manter: {', '.join(self.tipos_manter)}")
        print(f"🗑️  Tipos a remover: {', '.join(self.tipos_remover)}")
    
    def _extrair_tipo_documento(self, blob_name: str) -> str:
        """
        Extrai o tipo do documento do caminho do blob
        
        Args:
            blob_name: Nome do blob no formato "proposicoes/2025/PL/..."
            
        Returns:
            str: Tipo do documento (PL, PEC, REQ, etc.)
        """
        try:
            # Extrair partes do caminho
            partes = blob_name.split('/')
            
            # Estrutura real: proposicoes/2025/TIPO/...
            if len(partes) >= 3 and partes[0] == 'proposicoes':
                return partes[2]  # Pega "PL" de "proposicoes/2025/PL/..."
            else:
                return 'OUTRO'
                
        except Exception:
            return 'OUTRO'
    
    def _deve_remover_documento(self, blob_name: str) -> bool:
        """
        Verifica se o documento deve ser removido
        
        Args:
            blob_name: Nome do blob
            
        Returns:
            bool: True se deve remover, False caso contrário
        """
        tipo = self._extrair_tipo_documento(blob_name)
        return tipo in self.tipos_remover
    
    def _deve_manter_documento(self, blob_name: str) -> bool:
        """
        Verifica se o documento deve ser mantido
        
        Args:
            blob_name: Nome do blob
            
        Returns:
            bool: True se deve manter, False caso contrário
        """
        tipo = self._extrair_tipo_documento(blob_name)
        return tipo in self.tipos_manter
    
    def analisar_storage_atual(self):
        """
        Analisa o storage atual para identificar volumes por tipo
        
        Returns:
            Dict: Estatísticas detalhadas do storage
        """
        print("\n📊 ANÁLISE DO STORAGE ATUAL")
        print("=" * 50)
        
        try:
            # Listar todos os blobs
            blobs = self.gcs_manager.list_blobs()
            
            if not blobs:
                print("✅ Bucket está vazio!")
                return self.estatisticas
            
            self.estatisticas['total_antes'] = len(blobs)
            
            print(f"📁 Total de arquivos: {self.estatisticas['total_antes']:,}")
            
            # Analisar por tipo
            for blob in blobs:
                tipo = self._extrair_tipo_documento(blob.name)
                
                if self._deve_remover_documento(blob.name):
                    self.estatisticas['tipos_removidos'][tipo] = self.estatisticas['tipos_removidos'].get(tipo, 0) + 1
                    self.estatisticas['removidos'] += 1
                elif self._deve_manter_documento(blob.name):
                    self.estatisticas['tipos_mantidos'][tipo] = self.estatisticas['tipos_mantidos'].get(tipo, 0) + 1
                    self.estatisticas['mantidos'] += 1
                else:
                    self.estatisticas['tipos_removidos']['OUTRO'] = self.estatisticas['tipos_removidos'].get('OUTRO', 0) + 1
                    self.estatisticas['removidos'] += 1
            
            # Mostrar estatísticas
            print(f"\n📂 Arquivos por tipo:")
            print(f"   📋 A MANTER (tipos prioritários):")
            for tipo, quantidade in sorted(self.estatisticas['tipos_mantidos'].items()):
                print(f"      ✅ {tipo}: {quantidade:,} arquivos")
            
            print(f"\n   🗑️  A REMOVER (tipos irrelevantes):")
            for tipo, quantidade in sorted(self.estatisticas['tipos_removidos'].items()):
                print(f"      ❌ {tipo}: {quantidade:,} arquivos")
            
            print(f"\n📊 Resumo:")
            print(f"   📋 Mantidos: {self.estatisticas['mantidos']:,} arquivos")
            print(f"   🗑️  Removidos: {self.estatisticas['removidos']:,} arquivos")
            print(f"   📊 Total: {self.estatisticas['total_antes']:,} arquivos")
            
            return self.estatisticas
            
        except Exception as e:
            print(f"❌ Erro ao analisar storage: {e}")
            return self.estatisticas
    
    def executar_limpeza_seletiva(self):
        """
        Executa a limpeza seletiva do storage
        
        Returns:
            bool: True se sucesso, False caso contrário
        """
        print("\n🗑️  EXECUTANDO LIMPEZA SELETIVA...")
        print("=" * 50)
        
        try:
            # Listar todos os blobs
            blobs = self.gcs_manager.list_blobs()
            
            if not blobs:
                print("✅ Bucket está vazio!")
                return True
            
            print(f"📁 Processando {len(blobs):,} arquivos...")
            
            # Processar cada blob
            lote_size = 50
            lote_atual = 0
            removidos_lote = 0
            
            for i, blob in enumerate(blobs):
                try:
                    if self._deve_remover_documento(blob.name):
                        # Remover documento irrelevante
                        if self.gcs_manager.delete_blob(blob.name):
                            self.estatisticas['removidos'] += 1
                            removidos_lote += 1
                        else:
                            self.estatisticas['erros'] += 1
                    else:
                        # Manter documento prioritário
                        self.estatisticas['mantidos'] += 1
                    
                    # Progresso
                    if (i + 1) % lote_size == 0:
                        lote_atual += 1
                        progresso = ((i + 1) / len(blobs)) * 100
                        print(f"   📦 Lote {lote_atual}: {removidos_lote}/{lote_size} arquivos removidos ({progresso:.1f}%)")
                        removidos_lote = 0
                        
                except Exception as e:
                    print(f"   ❌ Erro ao processar {blob.name}: {e}")
                    self.estatisticas['erros'] += 1
            
            print(f"\n✅ Limpeza seletiva concluída!")
            print(f"   📋 Mantidos: {self.estatisticas['mantidos']:,} arquivos")
            print(f"   🗑️  Removidos: {self.estatisticas['removidos']:,} arquivos")
            print(f"   ❌ Erros: {self.estatisticas['erros']}")
            
            return self.estatisticas['erros'] == 0
            
        except Exception as e:
            print(f"❌ Erro durante limpeza seletiva: {e}")
            return False
    
    def verificar_resultado(self):
        """
        Verifica o resultado da limpeza seletiva
        
        Returns:
            bool: True se sucesso, False caso contrário
        """
        print("\n🔍 VERIFICANDO RESULTADO DA LIMPEZA...")
        print("=" * 40)
        
        try:
            # Listar blobs restantes
            blobs = self.gcs_manager.list_blobs()
            
            self.estatisticas['total_depois'] = len(blobs)
            
            print(f"📁 Arquivos restantes: {self.estatisticas['total_depois']:,}")
            
            # Verificar se só restam tipos prioritários
            tipos_restantes = set()
            for blob in blobs:
                tipo = self._extrair_tipo_documento(blob.name)
                tipos_restantes.add(tipo)
            
            tipos_indesejados = tipos_restantes - set(self.tipos_manter)
            
            if tipos_indesejados:
                print(f"⚠️  Ainda existem tipos indesejados: {list(tipos_indesejados)}")
                print("   📋 Exemplos de arquivos restantes:")
                for blob in blobs[:10]:
                    if self._deve_remover_documento(blob.name):
                        print(f"      • {blob.name}")
                return False
            else:
                print("✅ Apenas tipos prioritários restam!")
                print(f"   📋 Tipos encontrados: {list(tipos_restantes)}")
                return True
                
        except Exception as e:
            print(f"❌ Erro ao verificar resultado: {e}")
            return False
    
    def calcular_economia(self):
        """
        Calcula a economia de storage obtida
        
        Returns:
            float: Economia em MB
        """
        try:
            # Estimativa baseada nos documentos removidos
            # Tamanho médio estimado por tipo de documento
            tamanhos_estimados = {
                'REQ': 0.5,      # 500 KB
                'SUG': 0.2,      # 200 KB
                'RIC': 0.3,      # 300 KB
                'IND': 0.1,      # 100 KB
                'PRL': 0.1,      # 100 KB
                'MSC': 0.1,      # 100 KB
                'PCR': 0.1,      # 100 KB
                'OUTRO': 0.2     # 200 KB
            }
            
            economia_bytes = 0
            for tipo, quantidade in self.estatisticas['tipos_removidos'].items():
                tamanho_mb = tamanhos_estimados.get(tipo, 0.2)  # Default 200 KB
                economia_bytes += quantidade * (tamanho_mb * 1024 * 1024)
            
            economia_mb = economia_bytes / (1024 * 1024)
            self.estatisticas['economia_mb'] = economia_mb
            
            return economia_mb
            
        except Exception as e:
            print(f"❌ Erro ao calcular economia: {e}")
            return 0
    
    def gerar_relatorio_final(self):
        """
        Gera relatório final da operação
        """
        print(f"\n📋 RELATÓRIO FINAL - LIMPEZA SELETIVA GCS")
        print("=" * 50)
        print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        print(f"\n📊 Estatísticas da Operação:")
        print(f"   📁 Arquivos antes: {self.estatisticas['total_antes']:,}")
        print(f"   📁 Arquivos depois: {self.estatisticas['total_depois']:,}")
        print(f"   📋 Mantidos: {self.estatisticas['mantidos']:,}")
        print(f"   🗑️  Removidos: {self.estatisticas['removidos']:,}")
        print(f"   ❌ Erros: {self.estatisticas['erros']}")
        
        print(f"\n📂 Tipos Mantidos:")
        for tipo, quantidade in sorted(self.estatisticas['tipos_mantidos'].items()):
            print(f"   ✅ {tipo}: {quantidade:,} arquivos")
        
        print(f"\n📂 Tipos Removidos:")
        for tipo, quantidade in sorted(self.estatisticas['tipos_removidos'].items()):
            print(f"   ❌ {tipo}: {quantidade:,} arquivos")
        
        print(f"\n💰 Economia de Storage:")
        print(f"   💾 Economia estimada: {self.estatisticas['economia_mb']:.1f} MB")
        print(f"   💰 Custo economizado: ~${self.estatisticas['economia_mb'] * 0.023:.2f} USD/mês")  # ~$0.023/GB/mês
        
        print(f"\n✅ Limpeza seletiva concluída com sucesso!")
        print(f"🎯 Storage otimizado mantendo apenas dados valiosos!")

def confirmar_limpeza_seletiva():
    """
    Solicita confirmação do usuário antes de executar limpeza seletiva
    """
    print("\n⚠️  ATENÇÃO: Este script irá REMOVER DOCUMENTOS IRRELEVANTES do Google Cloud Storage!")
    print("📋 Documentos irrelevantes: REQ, SUG, RIC, IND, PRL, MSC, PCR, etc.")
    print("📋 Documentos mantidos: PL, PEC, PLP, MPV, PDC, PLV, PRC (tipos prioritários)")
    print("💰 Objetivo: Reduzir custos mantendo apenas dados valiosos")
    print("\nDigite 'LIMPAR SELETIVO' em maiúsculas para confirmar:")
    
    confirmacao = input("> ").strip()
    
    if confirmacao == "LIMPAR SELETIVO":
        return True
    else:
        print("❌ Operação cancelada pelo usuário.")
        return False

def main():
    """
    Função principal do script de limpeza seletiva
    """
    # Inicializar GCS Manager
    gcs_manager = get_gcs_manager()
    
    if not gcs_manager or not gcs_manager.is_available():
        print("❌ GCS não está disponível!")
        print("Verifique suas credenciais e configuração.")
        return
    
    print(f"✅ GCS Manager inicializado - Bucket: {gcs_manager.bucket_name}")
    
    try:
        # Criar gerenciador de limpeza
        limpador = LimpezaSeletivaGCS()
        
        # Solicitar confirmação
        if not confirmar_limpeza_seletiva():
            return
        
        # Analisar storage atual
        limpador.analisar_storage_atual()
        
        # Verificar se há documentos para remover
        if limpador.estatisticas['removidos'] == 0:
            print("\n✅ Não há documentos irrelevantes para remover!")
            print("📋 Storage já está otimizado com apenas tipos prioritários.")
            return
        
        # Executar limpeza seletiva
        print("\n🚀 Iniciando limpeza seletiva...")
        sucesso = limpador.executar_limpeza_seletiva()
        
        if sucesso:
            # Verificar resultado
            if limpador.verificar_resultado():
                # Calcular economia
                limpador.calcular_economia()
                
                # Gerar relatório final
                limpador.gerar_relatorio_final()
            else:
                print("\n⚠️  Limpeza incompleta - verifique manualmente")
        else:
            print("\n❌ Falha durante limpeza seletiva")
            
    except Exception as e:
        print(f"\n❌ Erro durante limpeza seletiva: {e}")
        
    finally:
        print("\n🔚 Operação finalizada.")

if __name__ == "__main__":
    main()
