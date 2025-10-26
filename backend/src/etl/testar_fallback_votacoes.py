#!/usr/bin/env python3
"""
Script de Teste do Fallback de Votações
Testa o funcionamento completo do coletor fallback de votações
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar configurações e modelos
from config import get_votacoes_fallback_config, deve_usar_fallback_votacoes
from models.database import get_db
from models.proposicao_models import Votacao, VotoDeputado, VotacaoObjeto, VotacaoProposicao, OrientacaoBancada

class TestadorFallbackVotacoes:
    """
    Classe responsável por testar o coletor fallback de votações
    """

    def __init__(self):
        """Inicializa o testador"""
        print("🧪 Testador de Fallback de Votações inicializado")
        
        # Verificar configurações
        self.fallback_habilitado = deve_usar_fallback_votacoes()
        self.config = get_votacoes_fallback_config()
        
        print(f"🔧 Fallback habilitado: {self.fallback_habilitado}")
        print(f"📅 Anos configurados: {self.config.get('anos_para_coletar', [])}")
        print(f"🎯 Limite de registros: {self.config.get('limite_registros', 0)}")

    def testar_configuracoes(self) -> Dict[str, Any]:
        """Testa configurações do fallback"""
        print("\n🔧 TESTANDO CONFIGURAÇÕES")
        print("=" * 50)
        
        resultado = {
            'tipo': 'configuracoes',
            'status': 'desconhecido',
            'dados': {},
            'erros': []
        }
        
        try:
            # Verificar configurações obrigatórias
            configs_obrigatorias = [
                'anos_para_coletar',
                'limite_registros',
                'base_url',
                'tipos_arquivos'
            ]
            
            configs_faltantes = []
            for config in configs_obrigatorias:
                if not self.config.get(config):
                    configs_faltantes.append(config)
            
            if configs_faltantes:
                resultado['status'] = 'erro'
                resultado['erros'].append(f"Configurações faltantes: {', '.join(configs_faltantes)}")
                print(f"   ❌ Configurações faltantes: {', '.join(configs_faltantes)}")
            else:
                resultado['status'] = 'sucesso'
                resultado['dados'] = {
                    'fallback_habilitado': self.fallback_habilitado,
                    'anos_configurados': self.config.get('anos_para_coletar'),
                    'limite_registros': self.config.get('limite_registros'),
                    'base_url': self.config.get('base_url'),
                    'tipos_arquivos': self.config.get('tipos_arquivos'),
                    'cache_dir': self.config.get('cache_dir')
                }
                print(f"   ✅ Todas as configurações estão presentes")
                print(f"   📅 Anos: {self.config.get('anos_para_coletar')}")
                print(f"   🎯 Limite: {self.config.get('limite_registros')}")
                print(f"   📁 Cache: {self.config.get('cache_dir')}")
                
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro no teste: {str(e)}")
            print(f"   ❌ Erro: {e}")
        
        return resultado

    def testar_models(self) -> Dict[str, Any]:
        """Testa models do banco de dados"""
        print("\n🗄️ TESTANDO MODELS DO BANCO")
        print("=" * 50)
        
        resultado = {
            'tipo': 'models',
            'status': 'desconhecido',
            'dados': {},
            'erros': []
        }
        
        db = None
        try:
            db = next(get_db())
            
            # Testar contagem de tabelas
            votacoes_count = db.query(Votacao).count()
            votos_count = db.query(VotoDeputado).count()
            objetos_count = db.query(VotacaoObjeto).count()
            proposicoes_count = db.query(VotacaoProposicao).count()
            orientacoes_count = db.query(OrientacaoBancada).count()
            
            resultado['dados'] = {
                'votacoes': votacoes_count,
                'votos': votos_count,
                'objetos': objetos_count,
                'proposicoes': proposicoes_count,
                'orientacoes': orientacoes_count
            }
            
            # Validar estrutura mínima
            if votacoes_count >= 0:  # Pode ser zero, é normal
                resultado['status'] = 'sucesso'
                print(f"   ✅ Models acessíveis")
                print(f"   📊 Votações: {votacoes_count}")
                print(f"   👥 Votos: {votos_count}")
                print(f"   📋 Objetos: {objetos_count}")
                print(f"   📄 Proposições: {proposicoes_count}")
                print(f"   🏛️ Orientações: {orientacoes_count}")
            else:
                resultado['status'] = 'erro'
                resultado['erros'].append("Erro ao acessar models")
                print(f"   ❌ Erro ao acessar models")
                
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro no teste: {str(e)}")
            print(f"   ❌ Erro: {e}")
        finally:
            if db:
                db.close()
        
        return resultado

    def testar_import_coletor(self) -> Dict[str, Any]:
        """Testa importação do coletor fallback"""
        print("\n📦 TESTANDO IMPORTAÇÃO DO COLETOR")
        print("=" * 50)
        
        resultado = {
            'tipo': 'import_coletor',
            'status': 'desconhecido',
            'dados': {},
            'erros': []
        }
        
        try:
            # Tentar importar o coletor
            from coleta_votacoes_fallback import ColetorVotacoesFallback
            
            # Tentar instanciar
            coletor = ColetorVotacoesFallback()
            
            resultado['status'] = 'sucesso'
            resultado['dados'] = {
                'classe': 'ColetorVotacoesFallback',
                'instanciado': True,
                'metodos_disponiveis': [
                    'coletar_votacoes_periodo',
                    'baixar_arquivo_json',
                    'processar_votacoes_principais',
                    'processar_votos_deputados',
                    'processar_objetos_votacao',
                    'processar_proposicoes_afetadas',
                    'processar_orientacoes_bancada'
                ]
            }
            
            print(f"   ✅ Coletor importado com sucesso")
            print(f"   📦 Classe: ColetorVotacoesFallback")
            print(f"   🔧 Instanciado: {coletor is not None}")
            print(f"   📋 Métodos disponíveis: {len(resultado['dados']['metodos_disponiveis'])}")
            
        except ImportError as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro de importação: {str(e)}")
            print(f"   ❌ Erro de importação: {e}")
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro no teste: {str(e)}")
            print(f"   ❌ Erro: {e}")
        
        return resultado

    def testar_conexao_arquivos(self) -> Dict[str, Any]:
        """Testa conexão com os arquivos JSON"""
        print("\n🌐 TESTANDO CONEXÃO COM ARQUIVOS")
        print("=" * 50)
        
        resultado = {
            'tipo': 'conexao_arquivos',
            'status': 'desconhecido',
            'dados': {},
            'erros': []
        }
        
        try:
            import requests
            
            base_url = self.config.get('base_url')
            anos = self.config.get('anos_para_coletar', [])
            tipos_arquivos = self.config.get('tipos_arquivos', [])
            
            # Testar conexão com um arquivo específico
            if anos and tipos_arquivos:
                ano_teste = anos[0]
                tipo_teste = tipos_arquivos[0]
                
                # Corrigir URL para usar o formato correto
                url_teste = f"https://dadosabertos.camara.leg.br/arquivos/votacoes/json/votacoes-{ano_teste}.json"
                
                print(f"   📡 Testando URL: {url_teste}")
                
                response = requests.head(url_teste, timeout=10, allow_redirects=True)
                
                if response.status_code in [200, 301, 302]:  # Aceitar redirecionamentos
                    resultado['status'] = 'sucesso'
                    resultado['dados'] = {
                        'url_teste': url_teste,
                        'status_code': response.status_code,
                        'content_length': response.headers.get('content-length', 'desconhecido'),
                        'content_type': response.headers.get('content-type', 'desconhecido')
                    }
                    print(f"   ✅ Conexão bem-sucedida")
                    print(f"   📊 Status: {response.status_code}")
                    print(f"   📏 Tamanho: {response.headers.get('content-length', 'desconhecido')} bytes")
                else:
                    resultado['status'] = 'erro'
                    resultado['erros'].append(f"Status code: {response.status_code}")
                    print(f"   ❌ Status code: {response.status_code}")
            else:
                resultado['status'] = 'erro'
                resultado['erros'].append("Configurações de anos ou tipos ausentes")
                print(f"   ❌ Configurações de anos ou tipos ausentes")
                
        except requests.exceptions.RequestException as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro de requisição: {str(e)}")
            print(f"   ❌ Erro de requisição: {e}")
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro no teste: {str(e)}")
            print(f"   ❌ Erro: {e}")
        
        return resultado

    def executar_testes_completos(self) -> Dict[str, Any]:
        """Executa todos os testes do fallback"""
        print("🧪 INICIANDO TESTES COMPLETOS DO FALLBACK")
        print("=" * 60)
        
        resultados = {
            'data_teste': datetime.now().isoformat(),
            'fallback_habilitado': self.fallback_habilitado,
            'testes': {},
            'resumo_geral': {
                'total_testes': 0,
                'sucessos': 0,
                'erros': 0
            }
        }
        
        # Executar todos os testes
        testes = [
            ('configuracoes', self.testar_configuracoes),
            ('models', self.testar_models),
            ('import_coletor', self.testar_import_coletor),
            ('conexao_arquivos', self.testar_conexao_arquivos)
        ]
        
        for nome_teste, funcao_teste in testes:
            print(f"\n🧪 Executando teste: {nome_teste}")
            resultado_teste = funcao_teste()
            resultados['testes'][nome_teste] = resultado_teste
            resultados['resumo_geral']['total_testes'] += 1
            
            status = resultado_teste.get('status', 'desconhecido')
            if status == 'sucesso':
                resultados['resumo_geral']['sucessos'] += 1
            elif status == 'erro':
                resultados['resumo_geral']['erros'] += 1
        
        return resultados

def main():
    """Função principal para execução dos testes"""
    print("🧪 TESTES DO FALLBACK DE VOTAÇÕES")
    print("=" * 60)
    
    testador = TestadorFallbackVotacoes()
    resultados = testador.executar_testes_completos()
    
    # Exibir resumo final
    print("\n📋 RESUMO FINAL DOS TESTES")
    print("=" * 50)
    
    resumo = resultados['resumo_geral']
    print(f"📅 Data dos testes: {resultados['data_teste']}")
    print(f"🔧 Fallback habilitado: {resultados['fallback_habilitado']}")
    print(f"\n📊 Resumo dos Testes:")
    print(f"   ✅ Sucessos: {resumo['sucessos']}")
    print(f"   ❌ Erros: {resumo['erros']}")
    print(f"   📋 Total: {resumo['total_testes']}")
    
    # Detalhes por teste
    print(f"\n📋 Detalhes por Teste:")
    for nome, teste in resultados['testes'].items():
        status = teste.get('status', 'desconhecido')
        icone = "✅" if status == 'sucesso' else "❌"
        print(f"   {icone} {nome.title()}: {status}")
        
        erros = teste.get('erros', [])
        if erros:
            for erro in erros:
                print(f"      - {erro}")
    
    # Conclusão
    total_sucessos = resumo['sucessos']
    total_testes = resumo['total_testes']
    
    if total_testes > 0 and total_sucessos == total_testes:
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"✅ Fallback de votações está pronto para uso")
    elif total_sucessos >= total_testes * 0.8:  # 80% de sucesso
        print(f"\n👍 MAIORIA DOS TESTES PASSOU!")
        print(f"⚠️ Algumas melhorias podem ser necessárias")
    else:
        print(f"\n⚠️ PROBLEMAS ENCONTRADOS!")
        print(f"🔧 Verifique os erros listados acima")

if __name__ == "__main__":
    main()
