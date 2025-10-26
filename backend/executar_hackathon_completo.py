#!/usr/bin/env python3
"""
Execução Completa do Pipeline Hackathon Kritikos 2025
Este script executa todo o processo:
1. Limpeza completa do banco e GCS
2. Coleta de dados de deputados e votações
3. Geração de relatório final

Autor: Kritikos Team
Data: Outubro/2025
"""

import sys
from pathlib import Path
import subprocess
import time
from datetime import datetime
from typing import Dict, Any

# Adicionar o diretório src ao sys.path
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))

class ExecutorHackathon:
    """
    Executor completo do pipeline do hackathon
    """
    
    def __init__(self):
        """Inicializa o executor"""
        self.inicio_geral = datetime.now()
        self.resultados = {}
        
        print("🚀 EXECUTOR COMPLETO - HACKATHON KRITIKOS 2025")
        print("=" * 70)
        print(f"📅 Início: {self.inicio_geral.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🎯 Objetivo: Limpeza completa + coleta focada em deputados e votações")
    
    def executar_script(self, nome_script: str, caminho_script: str, descricao: str) -> bool:
        """
        Executa um script específico
        
        Args:
            nome_script: Nome identificador do script
            caminho_script: Caminho do script para executar
            descricao: Descrição do que o script faz
            
        Returns:
            bool: True se sucesso, False se erro
        """
        print(f"\n{'='*25} {nome_script} {'='*25}")
        print(f"📝 Descrição: {descricao}")
        print(f"📂 Script: {caminho_script}")
        print(f"⏱️ Início: {datetime.now().strftime('%H:%M:%S')}")
        
        inicio_script = datetime.now()
        
        try:
            # Executar o script
            resultado = subprocess.run(
                [sys.executable, caminho_script],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hora de timeout por script
            )
            
            fim_script = datetime.now()
            duracao = (fim_script - inicio_script).total_seconds()
            
            # Mostrar resultado
            if resultado.returncode == 0:
                print(f"✅ {nome_script} concluído com sucesso em {duracao:.1f}s")
                
                # Salvar resultado
                self.resultados[nome_script.lower().replace(' ', '_')] = {
                    'status': 'sucesso',
                    'duracao_segundos': duracao,
                    'stdout': resultado.stdout,
                    'stderr': resultado.stderr,
                    'inicio': inicio_script,
                    'fim': fim_script
                }
                
                return True
            else:
                print(f"❌ ERRO em {nome_script}:")
                print(f"   Código de saída: {resultado.returncode}")
                print(f"   Stderr: {resultado.stderr}")
                print(f"   Duração: {duracao:.1f}s")
                
                # Salvar erro
                self.resultados[nome_script.lower().replace(' ', '_')] = {
                    'status': 'erro',
                    'duracao_segundos': duracao,
                    'codigo_saida': resultado.returncode,
                    'stdout': resultado.stdout,
                    'stderr': resultado.stderr,
                    'inicio': inicio_script,
                    'fim': fim_script
                }
                
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {nome_script} excedeu o tempo limite de 1 hora")
            return False
            
        except Exception as e:
            print(f"❌ ERRO CRÍTICO ao executar {nome_script}: {e}")
            return False
    
    def executar_limpeza_banco(self) -> bool:
        """Executa limpeza do banco de dados"""
        return self.executar_script(
            "Limpeza Banco",
            "testes/limpar_banco.py",
            "Remove todos os dados do banco de dados"
        )
    
    def executar_limpeza_gcs(self) -> bool:
        """Executa limpeza do Google Cloud Storage"""
        return self.executar_script(
            "Limpeza GCS",
            "testes/limpar_gcs.py",
            "Remove todos os arquivos do Google Cloud Storage"
        )
    
    def executar_pipeline_hackathon(self) -> bool:
        """Executa a pipeline do hackathon"""
        return self.executar_script(
            "Pipeline Hackathon",
            "pipeline_hackathon.py",
            "Coleta dados de deputados e votações para o hackathon"
        )
    
    def gerar_relatorio_final(self):
        """Gera relatório final de toda a execução"""
        fim_geral = datetime.now()
        duracao_total = (fim_geral - self.inicio_geral).total_seconds()
        
        print(f"\n{'='*70}")
        print("📋 RELATÓRIO FINAL - EXECUÇÃO COMPLETA HACKATHON")
        print(f"{'='*70}")
        print(f"📅 Início: {self.inicio_geral.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📅 Fim: {fim_geral.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"⏱️ Duração total: {duracao_total:.1f}s ({duracao_total/60:.1f}min)")
        
        print(f"\n📊 Resultados por etapa:")
        
        etapas_sucesso = 0
        total_etapas = len(self.resultados)
        
        for etapa, dados in self.resultados.items():
            status = dados['status']
            duracao = dados['duracao_segundos']
            
            if status == 'sucesso':
                etapas_sucesso += 1
                print(f"   ✅ {etapa.replace('_', ' ').title()}: Sucesso ({duracao:.1f}s)")
            else:
                print(f"   ❌ {etapa.replace('_', ' ').title()}: Erro ({duracao:.1f}s)")
        
        print(f"\n📈 Estatísticas:")
        print(f"   🎯 Etapas executadas: {etapas_sucesso}/{total_etapas}")
        print(f"   ⏱️ Tempo médio por etapa: {duracao_total/total_etapas:.1f}s")
        print(f"   📊 Taxa de sucesso: {(etapas_sucesso/total_etapas)*100:.1f}%")
        
        # Status final
        if etapas_sucesso == total_etapas:
            print(f"\n🎉 EXECUÇÃO COMPLETA CONCLUÍDA COM SUCESSO!")
            print(f"🎯 Ambiente limpo e dados coletados para o hackathon!")
            print(f"\n💡 PRÓXIMOS PASSOS:")
            print(f"   📊 Use os dados para suas análises no hackathon")
            print(f"   🗳️  Explore os dados de votações"
                  f"   💰 Analise padrões de gastos")
            print(f"   👥 Compare dados entre deputados e partidos")
        else:
            print(f"\n⚠️ EXECUÇÃO CONCLUÍDA COM PROBLEMAS")
            print(f"❌ {total_etapas - etapas_sucesso} etapas falharam")
            print(f"\n🔧 RECOMENDAÇÕES:")
            print(f"   📋 Verifique os logs de erro acima")
            print(f"   🔍 Verifique conexão com banco e GCS")
            print(f"   🌐 Verifique conexão com a internet")
            print(f"   🔄 Tente executar novamente as etapas que falharam")
        
        # Salvar relatório em arquivo
        self._salvar_relatorio_em_arquivo()
        
        return {
            'status': 'sucesso' if etapas_sucesso == total_etapas else 'parcial',
            'duracao_total': duracao_total,
            'etapas_sucesso': etapas_sucesso,
            'total_etapas': total_etapas,
            'resultados_detalhados': self.resultados
        }
    
    def _salvar_relatorio_em_arquivo(self):
        """Salva o relatório em um arquivo JSON"""
        try:
            import json
            
            nome_arquivo = f"relatorio_hackathon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            caminho_arquivo = Path(__file__).parent / nome_arquivo
            
            # Preparar dados para JSON
            relatorio_json = {
                'metadata': {
                    'inicio': self.inicio_geral.isoformat(),
                    'fim': datetime.now().isoformat(),
                    'duracao_total': (datetime.now() - self.inicio_geral).total_seconds(),
                    'versao': 'hackathon-2025-v1.0'
                },
                'resultados': {}
            }
            
            for etapa, dados in self.resultados.items():
                relatorio_json['resultados'][etapa] = {
                    'status': dados['status'],
                    'duracao_segundos': dados['duracao_segundos'],
                    'inicio': dados['inicio'].isoformat(),
                    'fim': dados['fim'].isoformat()
                }
                
                if dados['status'] == 'erro':
                    relatorio_json['resultados'][etapa]['codigo_saida'] = dados.get('codigo_saida')
                    relatorio_json['resultados'][etapa]['stderr'] = dados.get('stderr', '')[:500]  # Limitar tamanho
            
            # Salvar arquivo
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(relatorio_json, f, indent=2, ensure_ascii=False)
            
            print(f"\n📄 Relatório salvo em: {caminho_arquivo}")
            
        except Exception as e:
            print(f"\n⚠️ Erro ao salvar relatório em arquivo: {e}")
    
    def executar_processo_completo(self) -> Dict[str, Any]:
        """Executa todo o processo do hackathon"""
        
        print(f"\n🚀 INICIANDO PROCESSO COMPLETO DO HACKATHON")
        print(f"Este processo irá:")
        print(f"   1️⃣ Limpar completamente o banco de dados")
        print(f"   2️⃣ Limpar completamente o Google Cloud Storage")
        print(f"   3️⃣ Coletar dados de deputados e votações")
        print(f"   4️⃣ Gerar relatório final")
        
        # Confirmar execução
        print(f"\n⚠️  ATENÇÃO: Esta operação irá APAGAR TODOS os dados existentes!")
        print(f"Digite 'EXECUTAR HACKATHON' para confirmar:")
        confirmacao = input("> ").strip()
        
        if confirmacao != "EXECUTAR HACKATHON":
            print("❌ Operação cancelada pelo usuário.")
            return {'status': 'cancelado'}
        
        # Etapa 1: Limpeza do banco
        if not self.executar_limpeza_banco():
            print("❌ Falha na limpeza do banco. Interrompendo execução.")
            return self.gerar_relatorio_final()
        
        # Etapa 2: Limpeza do GCS
        if not self.executar_limpeza_gcs():
            print("❌ Falha na limpeza do GCS. Interrompendo execução.")
            return self.gerar_relatorio_final()
        
        # Etapa 3: Pipeline do hackathon
        if not self.executar_pipeline_hackathon():
            print("❌ Falha na pipeline do hackathon.")
            return self.gerar_relatorio_final()
        
        # Etapa 4: Relatório final
        return self.gerar_relatorio_final()

def main():
    """Função principal"""
    executor = ExecutorHackathon()
    resultado = executor.executar_processo_completo()
    
    if resultado['status'] == 'sucesso':
        print(f"\n🎉 HACKATHON KRITIKOS 2025 - PROCESSO CONCLUÍDO COM SUCESSO!")
        print(f"🎯 Ambiente pronto para as análises do hackathon!")
    elif resultado['status'] == 'cancelado':
        print(f"\n⏹️ Processo cancelado pelo usuário.")
    else:
        print(f"\n⚠️ Processo concluído com problemas. Verifique os logs acima.")
    
    return resultado

if __name__ == "__main__":
    main()
