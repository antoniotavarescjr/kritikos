#!/usr/bin/env python3
"""
Processador de metadados do GCS para baixar documentos de proposições
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.gcs_utils import get_gcs_manager
from etl.pdf_coleta_module import PDFColetaManager
from models.db_utils import get_db_session
from sqlalchemy import text

class GCSMetadataProcessor:
    """
    Processador de metadados do GCS para baixar documentos
    """
    
    def __init__(self):
        self.gcs = get_gcs_manager()
        self.pdf_coleta = PDFColetaManager()
        self.session = get_db_session()
        
        # Estatísticas
        self.stats = {
            'total_metadados': 0,
            'processados': 0,
            'sucessos': 0,
            'falhas': 0,
            'sem_documento': 0,
            'ja_existe': 0
        }
        
        # Checkpoint
        self.checkpoint_file = Path('checkpoint_metadados.json')
        self.processados = set()
        self.carregar_checkpoint()
    
    def carregar_checkpoint(self):
        """Carrega checkpoint de processamento anterior"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    self.processados = set(data.get('processados', []))
                    print(f"✅ Checkpoint carregado: {len(self.processados)} já processados")
            except Exception as e:
                print(f"⚠️ Erro ao carregar checkpoint: {e}")
    
    def salvar_checkpoint(self):
        """Salva checkpoint de processamento"""
        try:
            data = {
                'processados': list(self.processados),
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats
            }
            with open(self.checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Erro ao salvar checkpoint: {e}")
    
    def listar_metadados(self, prefix: str = 'proposicoes/') -> List[str]:
        """
        Lista todos os arquivos de metadados no GCS
        
        Args:
            prefix: Prefixo para filtrar arquivos
            
        Returns:
            List[str]: Lista de paths de metadados
        """
        if not self.gcs or not self.gcs.is_available():
            print("❌ GCS não disponível")
            return []
        
        print("🔍 Listando metadados no GCS...")
        blobs = self.gcs.list_blobs(prefix)
        
        # Filtrar apenas arquivos de metadados
        metadata_files = [
            blob.name for blob in blobs 
            if 'metadata' in blob.name and blob.name.endswith('.json')
        ]
        
        print(f"📊 Encontrados {len(metadata_files)} arquivos de metadados")
        return metadata_files
    
    def extrair_informacoes_proposicao(self, metadata: Dict) -> Optional[Dict]:
        """
        Extrai informações da proposição do metadado
        
        Args:
            metadata: Metadados da proposição
            
        Returns:
            Dict: Informações extraídas ou None se erro
        """
        try:
            # Verificar estrutura
            if 'proposicao' not in metadata:
                print("   ⚠️ Metadado não contém 'proposicao'")
                return None
            
            prop = metadata['proposicao']
            
            # Extrair informações básicas
            info = {
                'id': prop.get('id'),
                'uri': prop.get('uri'),
                'siglaTipo': prop.get('siglaTipo'),
                'codTipo': prop.get('codTipo'),
                'numero': prop.get('numero'),
                'ano': prop.get('ano'),
                'ementa': prop.get('ementa', ''),
                'documento_disponivel': metadata.get('documento_disponivel', False)
            }
            
            # Verificar se tem URL direta
            if 'urlInteiroTeor' in prop:
                info['urlInteiroTeor'] = prop['urlInteiroTeor']
            
            return info
            
        except Exception as e:
            print(f"   ❌ Erro ao extrair informações: {e}")
            return None
    
    def verificar_texto_ja_existe(self, info: Dict) -> bool:
        """
        Verifica se o texto já existe no GCS
        
        Args:
            info: Informações da proposição
            
        Returns:
            bool: True se já existe, False caso contrário
        """
        try:
            # Possíveis paths para o texto
            possible_paths = [
                f"proposicoes/{info['ano']}/{info['siglaTipo']}/texto-completo/{info['siglaTipo']}-{info['id']}-texto-completo.txt",
                f"proposicoes/{info['ano']}/{info['siglaTipo']}/texto-completo/{info['siglaTipo']}-{info['id']}-texto.html",
                f"proposicoes/{info['ano']}/{info['siglaTipo']}/documento/{info['siglaTipo']}-{info['id']}-texto.html"
            ]
            
            for path in possible_paths:
                if self.gcs.bucket.blob(path).exists():
                    return True
            
            return False
            
        except Exception:
            return False
    
    def processar_metadado(self, metadata_path: str) -> bool:
        """
        Processa um único metadado
        
        Args:
            metadata_path: Path do metadado no GCS
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            print(f"\n📄 Processando: {metadata_path}")
            
            # Verificar se já foi processado
            if metadata_path in self.processados:
                print("   ⏭️ Já processado, pulando...")
                self.stats['ja_existe'] += 1
                return True
            
            # Baixar metadado
            metadata = self.gcs.download_json(metadata_path, compressed=False)
            if not metadata:
                print("   ❌ Erro ao baixar metadado")
                self.stats['falhas'] += 1
                return False
            
            # Extrair informações
            info = self.extrair_informacoes_proposicao(metadata)
            if not info:
                print("   ❌ Erro ao extrair informações")
                self.stats['falhas'] += 1
                return False
            
            print(f"   📋 {info['siglaTipo']} {info['numero']}/{info['ano']} (ID: {info['id']})")
            
            # Verificar se documento está disponível
            if not info.get('documento_disponivel', False):
                print("   ⚠️ Documento não disponível na API")
                self.stats['sem_documento'] += 1
                self.processados.add(metadata_path)
                return True
            
            # Verificar se texto já existe
            if self.verificar_texto_ja_existe(info):
                print("   ✅ Texto já existe no GCS")
                self.stats['ja_existe'] += 1
                self.processados.add(metadata_path)
                return True
            
            # Preparar dados para o PDFColetaManager
            coleta_data = {
                'id': info['id'],
                'uri': info['uri'],
                'siglaTipo': info['siglaTipo'],
                'numero': info['numero'],
                'ano': info['ano'],
                'ementa': info['ementa']
            }
            
            # Adicionar URL direta se disponível
            if 'urlInteiroTeor' in info:
                coleta_data['urlInteiroTeor'] = info['urlInteiroTeor']
            
            # Usar PDFColetaManager para baixar
            print("   🔄 Baixando documento...")
            resultado = self.pdf_coleta.processar_proposicao(coleta_data)
            
            if resultado:
                print("   ✅ Documento baixado com sucesso")
                self.stats['sucessos'] += 1
            else:
                print("   ❌ Falha ao baixar documento")
                self.stats['falhas'] += 1
            
            # Marcar como processado
            self.processados.add(metadata_path)
            return resultado
            
        except Exception as e:
            print(f"   ❌ Erro no processamento: {e}")
            self.stats['falhas'] += 1
            return False
    
    def processar_lote(self, limite: Optional[int] = None, continuar: bool = True) -> Dict:
        """
        Processa lote de metadados
        
        Args:
            limite: Limite de metadados para processar
            continuar: Se deve continuar do checkpoint
            
        Returns:
            Dict: Estatísticas do processamento
        """
        print("🚀 Iniciando processamento de metadados do GCS...")
        
        # Listar metadados
        metadata_files = self.listar_metadados()
        self.stats['total_metadados'] = len(metadata_files)
        
        if not metadata_files:
            print("❌ Nenhum metadado encontrado")
            return self.stats
        
        # Filtrar já processados se continuar
        if continuar:
            metadata_files = [f for f in metadata_files if f not in self.processados]
            print(f"📊 {len(metadata_files)} metadados para processar (continuando)")
        
        # Aplicar limite
        if limite:
            metadata_files = metadata_files[:limite]
            print(f"📊 Limitado a {len(metadata_files)} metadados")
        
        # Processar
        start_time = time.time()
        for i, metadata_path in enumerate(metadata_files, 1):
            print(f"\n📍 Progresso: {i}/{len(metadata_files)}")
            
            self.processar_metadado(metadata_path)
            self.stats['processados'] += 1
            
            # Salvar checkpoint a cada 10 processamentos
            if i % 10 == 0:
                self.salvar_checkpoint()
                print(f"💾 Checkpoint salvo ({i} processados)")
            
            # Pequena pausa para não sobrecarregar
            time.sleep(0.5)
        
        # Salvar checkpoint final
        self.salvar_checkpoint()
        
        # Estatísticas finais
        elapsed = time.time() - start_time
        print(f"\n📊 PROCESSAMENTO CONCLUÍDO")
        print(f"⏱️ Tempo total: {elapsed:.2f} segundos")
        print(f"📊 Estatísticas:")
        print(f"   Total de metadados: {self.stats['total_metadados']}")
        print(f"   Processados: {self.stats['processados']}")
        print(f"   Sucessos: {self.stats['sucessos']}")
        print(f"   Falhas: {self.stats['falhas']}")
        print(f"   Sem documento: {self.stats['sem_documento']}")
        print(f"   Já existiam: {self.stats['ja_existe']}")
        
        if self.stats['processados'] > 0:
            taxa_sucesso = (self.stats['sucessos'] / self.stats['processados']) * 100
            print(f"   Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        return self.stats

def main():
    """
    Função principal para execução via CLI
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Processar metadados do GCS')
    parser.add_argument('--limite', type=int, help='Limite de metadados para processar')
    parser.add_argument('--continuar', action='store_true', help='Continuar do checkpoint')
    parser.add_argument('--ano', type=str, help='Filtrar por ano específico')
    
    args = parser.parse_args()
    
    # Configurar variável de ambiente
    os.environ['GCS_BUCKET_NAME'] = 'kritikos-emendas-prod'
    
    processor = GCSMetadataProcessor()
    
    # Se ano especificado, filtrar
    if args.ano:
        print(f"🔍 Filtrando por ano: {args.ano}")
        # Aqui poderia implementar filtro por ano se necessário
    
    # Processar
    stats = processor.processar_lote(
        limite=args.limite,
        continuar=args.continuar
    )
    
    print("\n✅ Processamento concluído!")

if __name__ == "__main__":
    main()
