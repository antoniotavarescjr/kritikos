#!/usr/bin/env python3
"""
Script para revisar e categorizar todas as proposições salvas no GCS
Identifica duplicatas, organiza dados e gera estatísticas completas
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any

# Adicionar diretório src ao path
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
sys.path.append(str(SRC_DIR))

from utils.gcs_utils import get_gcs_manager
from models.db_utils import get_db_session
from models.proposicao_models import Proposicao

class RevisorGCSProposicoes:
    def __init__(self):
        """Inicializa o revisor do GCS"""
        self.gcs_manager = get_gcs_manager()
        self.db = get_db_session()
        
        print("🔍 REVISOR GCS - PROPOSIÇÕES")
        print("=" * 50)
        print(f"📁 Bucket: {self.gcs_manager.bucket_name}")
        print(f"🗄️ Projeto: {self.gcs_manager.project_id}")
        
    def listar_todos_arquivos_gcs(self) -> Dict[str, List[Dict]]:
        """
        Lista todos os arquivos de proposições no GCS
        
        Returns:
            Dict: Arquivos organizados por tipo e ano
        """
        print("\n📋 LISTANDO ARQUIVOS NO GCS")
        print("=" * 40)
        
        arquivos_por_tipo = defaultdict(lambda: defaultdict(list))
        total_arquivos = 0
        
        try:
            # Listar blobs no bucket
            blobs = self.gcs_manager.bucket.list_blobs(prefix='proposicoes/')
            
            for blob in blobs:
                if blob.name.endswith('.json'):
                    # Extrair informações do path
                    path_parts = blob.name.split('/')
                    
                    if len(path_parts) >= 5:
                        ano = path_parts[1]  # proposicoes/ANO/
                        tipo = path_parts[2]  # proposicoes/ANO/TIPO/
                        subtipo = path_parts[3] if path_parts[3] != 'texto-completo' else 'texto-completo'
                        filename = path_parts[-1]
                        
                        arquivo_info = {
                            'path': blob.name,
                            'filename': filename,
                            'size': blob.size,
                            'updated': blob.updated,
                            'md5_hash': blob.md5_hash,
                            'ano': ano,
                            'tipo': tipo,
                            'subtipo': subtipo
                        }
                        
                        arquivos_por_tipo[tipo][ano].append(arquivo_info)
                        total_arquivos += 1
            
            print(f"📁 Total de arquivos encontrados: {total_arquivos}")
            
            # Estatísticas por tipo
            for tipo in sorted(arquivos_por_tipo.keys()):
                total_tipo = sum(len(arquivos_por_tipo[tipo][ano]) for ano in arquivos_por_tipo[tipo])
                print(f"   • {tipo}: {total_tipo} arquivos")
                
                for ano in sorted(arquivos_por_tipo[tipo].keys()):
                    qtd = len(arquivos_por_tipo[tipo][ano])
                    print(f"      - {ano}: {qtd} arquivos")
            
            return dict(arquivos_por_tipo)
            
        except Exception as e:
            print(f"❌ Erro ao listar arquivos: {e}")
            return {}
    
    def analisar_duplicatas(self, arquivos_por_tipo: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, List[Dict]]:
        """
        Identifica arquivos duplicados baseado em conteúdo e nome
        
        Args:
            arquivos_por_tipo: Dicionário de arquivos organizados
            
        Returns:
            Dict: Duplicatas encontradas
        """
        print(f"\n🔍 ANALISANDO DUPLICATAS")
        print("=" * 40)
        
        duplicatas = defaultdict(list)
        hashes_vistos = defaultdict(list)
        nomes_vistos = defaultdict(list)
        
        # Analisar por hash MD5
        for tipo in arquivos_por_tipo:
            for ano in arquivos_por_tipo[tipo]:
                for arquivo in arquivos_por_tipo[tipo][ano]:
                    md5_hash = arquivo.get('md5_hash')
                    filename = arquivo.get('filename')
                    
                    if md5_hash:
                        hashes_vistos[md5_hash].append(arquivo)
                    
                    if filename:
                        nomes_vistos[filename].append(arquivo)
        
        # Identificar duplicatas por hash
        print("📋 Duplicatas por hash MD5:")
        total_duplicatas_hash = 0
        
        for md5_hash, arquivos in hashes_vistos.items():
            if len(arquivos) > 1:
                total_duplicatas_hash += len(arquivos) - 1
                duplicatas['hash'].append({
                    'hash': md5_hash,
                    'arquivos': arquivos,
                    'quantidade': len(arquivos)
                })
                
                print(f"   🔁 Hash {md5_hash[:8]}...: {len(arquivos)} cópias")
                for arq in arquivos:
                    print(f"      - {arq['path']}")
        
        # Identificar duplicatas por nome
        print(f"\n📋 Duplicatas por nome:")
        total_duplicatas_nome = 0
        
        for nome, arquivos in nomes_vistos.items():
            if len(arquivos) > 1:
                total_duplicatas_nome += len(arquivos) - 1
                duplicatas['nome'].append({
                    'nome': nome,
                    'arquivos': arquivos,
                    'quantidade': len(arquivos)
                })
                
                print(f"   🔁 Nome {nome}: {len(arquivos)} cópias")
                for arq in arquivos:
                    print(f"      - {arq['path']}")
        
        total_duplicatas = total_duplicatas_hash + total_duplicatas_nome
        print(f"\n📊 Total de duplicatas: {total_duplicatas}")
        print(f"   • Por hash: {total_duplicatas_hash}")
        print(f"   • Por nome: {total_duplicatas_nome}")
        
        return dict(duplicatas)
    
    def comparar_com_banco(self, arquivos_por_tipo: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, Any]:
        """
        Compara arquivos no GCS com registros no banco
        
        Args:
            arquivos_por_tipo: Dicionário de arquivos
            
        Returns:
            Dict: Resultados da comparação
        """
        print(f"\n🗄️ COMPARANDO GCS COM BANCO DE DADOS")
        print("=" * 50)
        
        try:
            # Buscar todas as proposições no banco
            proposicoes_db = self.db.query(Proposicao).all()
            
            print(f"📊 Proposições no banco: {len(proposicoes_db)}")
            
            # Estatísticas por tipo e ano no banco
            stats_db = defaultdict(lambda: defaultdict(int))
            gcs_urls = set()
            
            for prop in proposicoes_db:
                stats_db[prop.tipo][prop.ano] += 1
                if prop.gcs_url:
                    gcs_urls.add(prop.gcs_url)
            
            print(f"📁 URLs GCS no banco: {len(gcs_urls)}")
            
            # Contar arquivos no GCS
            stats_gcs = defaultdict(lambda: defaultdict(int))
            total_arquivos_gcs = 0
            
            for tipo in arquivos_por_tipo:
                for ano in arquivos_por_tipo[tipo]:
                    # Contar apenas arquivos de texto completo
                    texto_completo = [a for a in arquivos_por_tipo[tipo][ano] 
                                    if a.get('subtipo') == 'texto-completo']
                    stats_gcs[tipo][ano] = len(texto_completo)
                    total_arquivos_gcs += len(texto_completo)
            
            print(f"📁 Arquivos no GCS: {total_arquivos_gcs}")
            
            # Comparação detalhada
            print(f"\n📋 COMPARAÇÃO POR TIPO E ANO:")
            
            todos_tipos = set(stats_db.keys()) | set(stats_gcs.keys())
            
            for tipo in sorted(todos_tipos):
                print(f"\n   📄 {tipo}:")
                
                todos_anos = set(stats_db[tipo].keys()) | set(stats_gcs[tipo].keys())
                
            for ano in sorted(todos_anos):
                qtd_db = stats_db[tipo].get(ano, 0)
                qtd_gcs = stats_gcs[tipo].get(ano, 0)
                status = "✅" if qtd_db == qtd_gcs else "⚠️"
                
                print(f"      {ano}: Banco={qtd_db}, GCS={qtd_gcs} {status}")
            
            # Identificar inconsistências
            inconsistencias = []
            
            # Arquivos GCS sem registro no banco
            arquivos_gcs_paths = set()
            for tipo in arquivos_por_tipo:
                for ano in arquivos_por_tipo[tipo]:
                    for arquivo in arquivos_por_tipo[tipo][ano]:
                        if arquivo.get('subtipo') == 'texto-completo':
                            arquivos_gcs_paths.add(arquivo['path'])
            
            # URLs no banco que não existem no GCS
            urls_banco_sem_gcs = gcs_urls - arquivos_gcs_paths
            if urls_banco_sem_gcs:
                inconsistencias.append({
                    'tipo': 'URLs no banco sem arquivo GCS',
                    'quantidade': len(urls_banco_sem_gcs),
                    'items': list(urls_banco_sem_gcs)[:5]  # Primeiros 5
                })
            
            # Arquivos GCS sem URL no banco
            arquivos_sem_url_banco = arquivos_gcs_paths - gcs_urls
            if arquivos_sem_url_banco:
                inconsistencias.append({
                    'tipo': 'Arquivos GCS sem URL no banco',
                    'quantidade': len(arquivos_sem_url_banco),
                    'items': list(arquivos_sem_url_banco)[:5]  # Primeiros 5
                })
            
            if inconsistencias:
                print(f"\n⚠️ INCONSISTÊNCIAS ENCONTRADAS:")
                for inc in inconsistencias:
                    print(f"   • {inc['tipo']}: {inc['quantidade']} itens")
                    for item in inc['items']:
                        print(f"      - {item}")
            else:
                print(f"\n✅ Nenhuma inconsistência encontrada!")
            
            return {
                'total_db': len(proposicoes_db),
                'total_gcs': total_arquivos_gcs,
                'stats_db': dict(stats_db),
                'stats_gcs': dict(stats_gcs),
                'inconsistencias': inconsistencias
            }
            
        except Exception as e:
            print(f"❌ Erro na comparação: {e}")
            return {}
    
    def analisar_conteudo_amostras(self, arquivos_por_tipo: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, Any]:
        """
        Analisa o conteúdo de amostras dos arquivos
        
        Args:
            arquivos_por_tipo: Dicionário de arquivos
            
        Returns:
            Dict: Análise de conteúdo
        """
        print(f"\n📄 ANALISANDO CONTEÚDO DE AMOSTRAS")
        print("=" * 45)
        
        analise = {
            'amostras_analisadas': 0,
            'tipos_conteudo': Counter(),
            'tamanhos_medios': defaultdict(list),
            'problemas_encontrados': []
        }
        
        # Analisar até 5 amostras por tipo
        for tipo in list(arquivos_por_tipo.keys())[:5]:  # Limitar a 5 tipos
            print(f"\n📄 Analisando {tipo}:")
            
            amostras_tipo = 0
            for ano in list(arquivos_por_tipo[tipo].keys())[:2]:  # Limitar a 2 anos
                for arquivo in arquivos_por_tipo[tipo][ano][:3]:  # Até 3 arquivos
                    if amostras_tipo >= 5:
                        break
                    
                    try:
                        # Baixar conteúdo
                        content = self.gcs_manager.download_json(arquivo['path'])
                        
                        if content:
                            analise['amostras_analisadas'] += 1
                            analise['tamanhos_medios'][tipo].append(len(str(content)))
                            
                            # Analisar estrutura
                            if isinstance(content, dict):
                                keys = list(content.keys())
                                print(f"      📋 {arquivo['filename']}: {keys[:5]}...")
                                
                                # Verificar campos importantes
                                campos_essenciais = ['id', 'siglaTipo', 'numero', 'ano', 'ementa']
                                campos_faltantes = [c for c in campos_essenciais if c not in content]
                                
                                if campos_faltantes:
                                    analise['problemas_encontrados'].append({
                                        'arquivo': arquivo['path'],
                                        'problema': f"Campos faltantes: {campos_faltantes}"
                                    })
                                
                                # Identificar tipo de conteúdo
                                if 'textoCompleto' in content:
                                    analise['tipos_conteudo']['com_texto'] += 1
                                else:
                                    analise['tipos_conteudo']['metadados_apenas'] += 1
                            
                            amostras_tipo += 1
                            
                    except Exception as e:
                        print(f"      ❌ Erro ao analisar {arquivo['filename']}: {e}")
                        analise['problemas_encontrados'].append({
                            'arquivo': arquivo['path'],
                            'problema': f"Erro na leitura: {str(e)}"
                        })
        
        # Resumo da análise
        print(f"\n📊 RESUMO DA ANÁLISE DE CONTEÚDO:")
        print(f"   • Amostras analisadas: {analise['amostras_analisadas']}")
        print(f"   • Tipos de conteúdo: {dict(analise['tipos_conteudo'])}")
        
        if analise['tamanhos_medios']:
            print(f"   • Tamanhos médios por tipo:")
            for tipo, tamanhos in analise['tamanhos_medios'].items():
                media = sum(tamanhos) / len(tamanhos)
                print(f"      - {tipo}: {media:.0f} caracteres")
        
        if analise['problemas_encontrados']:
            print(f"   • Problemas encontrados: {len(analise['problemas_encontrados'])}")
            for prob in analise['problemas_encontrados'][:3]:  # Primeiros 3
                print(f"      - {prob['arquivo']}: {prob['problema']}")
        
        return analise
    
    def gerar_relatorio_final(self, arquivos_por_tipo: Dict, duplicatas: Dict, 
                            comparacao: Dict, analise: Dict) -> str:
        """
        Gera um relatório completo da análise
        
        Args:
            arquivos_por_tipo: Arquivos organizados
            duplicatas: Duplicatas encontradas
            comparacao: Comparação com banco
            analise: Análise de conteúdo
            
        Returns:
            str: Caminho do relatório gerado
        """
        print(f"\n📝 GERANDO RELATÓRIO FINAL")
        print("=" * 40)
        
        relatorio = {
            'data_geracao': datetime.now().isoformat(),
            'resumo': {
                'total_arquivos_gcs': sum(
                    len(arquivos_por_tipo[tipo][ano]) 
                    for tipo in arquivos_por_tipo 
                    for ano in arquivos_por_tipo[tipo]
                ),
                'total_tipos': len(arquivos_por_tipo),
                'total_duplicatas': (
                    sum(d['quantidade'] - 1 for d in duplicatas.get('hash', [])) +
                    sum(d['quantidade'] - 1 for d in duplicatas.get('nome', []))
                ),
                'proposicoes_banco': comparacao.get('total_db', 0),
                'inconsistencias': len(comparacao.get('inconsistencias', []))
            },
            'arquivos_por_tipo': {
                tipo: {
                    ano: len(arquivos)
                    for ano, arquivos in anos.items()
                }
                for tipo, anos in arquivos_por_tipo.items()
            },
            'duplicatas': duplicatas,
            'comparacao_banco_gcs': comparacao,
            'analise_conteudo': analise,
            'recomendacoes': []
        }
        
        # Gerar recomendações
        if relatorio['resumo']['total_duplicatas'] > 0:
            relatorio['recomendacoes'].append(
                f"Remover {relatorio['resumo']['total_duplicatas']} arquivos duplicados"
            )
        
        if relatorio['resumo']['inconsistencias'] > 0:
            relatorio['recomendacoes'].append(
                f"Corrigir {relatorio['resumo']['inconsistencias']} inconsistências entre GCS e banco"
            )
        
        if analise['problemas_encontrados']:
            relatorio['recomendacoes'].append(
                f"Investigar {len(analise['problemas_encontrados'])} problemas de conteúdo"
            )
        
        # Salvar relatório
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        relatorio_path = f"relatorio_gcs_proposicoes_{timestamp}.json"
        
        try:
            with open(relatorio_path, 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✅ Relatório salvo: {relatorio_path}")
            
            # Resumo final
            print(f"\n📊 RESUMO FINAL:")
            print(f"   • Arquivos no GCS: {relatorio['resumo']['total_arquivos_gcs']}")
            print(f"   • Tipos de proposições: {relatorio['resumo']['total_tipos']}")
            print(f"   • Duplicatas: {relatorio['resumo']['total_duplicatas']}")
            print(f"   • Proposições no banco: {relatorio['resumo']['proposicoes_banco']}")
            print(f"   • Inconsistências: {relatorio['resumo']['inconsistencias']}")
            print(f"   • Recomendações: {len(relatorio['recomendacoes'])}")
            
            return relatorio_path
            
        except Exception as e:
            print(f"❌ Erro ao salvar relatório: {e}")
            return ""
    
    def executar_revisao_completa(self):
        """
        Executa a revisão completa do GCS
        """
        try:
            # 1. Listar todos os arquivos
            arquivos_por_tipo = self.listar_todos_arquivos_gcs()
            
            if not arquivos_por_tipo:
                print("❌ Nenhum arquivo encontrado no GCS!")
                return
            
            # 2. Analisar duplicatas
            duplicatas = self.analisar_duplicatas(arquivos_por_tipo)
            
            # 3. Comparar com banco
            comparacao = self.comparar_com_banco(arquivos_por_tipo)
            
            # 4. Analisar conteúdo de amostras
            analise = self.analisar_conteudo_amostras(arquivos_por_tipo)
            
            # 5. Gerar relatório final
            relatorio_path = self.gerar_relatorio_final(
                arquivos_por_tipo, duplicatas, comparacao, analise
            )
            
            print(f"\n🎉 REVISÃO CONCLUÍDA COM SUCESSO!")
            if relatorio_path:
                print(f"📋 Relatório disponível: {relatorio_path}")
            
        except Exception as e:
            print(f"❌ Erro durante a revisão: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.db.close()

def main():
    """
    Função principal
    """
    print("🔍 REVISÃO COMPLETA DO GCS - PROPOSIÇÕES")
    print("=" * 60)
    print("Este script irá:")
    print("   • Listar todos os arquivos de proposições no GCS")
    print("   • Identificar duplicatas por hash e nome")
    print("   • Comparar com registros no banco de dados")
    print("   • Analisar conteúdo de amostras")
    print("   • Gerar relatório completo com recomendações")
    print("=" * 60)
    
    revisor = RevisorGCSProposicoes()
    revisor.executar_revisao_completa()

if __name__ == "__main__":
    main()
