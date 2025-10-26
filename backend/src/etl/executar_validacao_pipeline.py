#!/usr/bin/env python3
"""
Script Principal de Validação do Pipeline
Executa validação completa e gera relatório final das coletas para o período 06/2025+
"""

import sys
from pathlib import Path
from datetime import datetime

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar scripts de validação e relatório
from etl.validacao_pipeline import ValidadorPipeline
from etl.relatorio_coletas import GeradorRelatorio

def main():
    """
    Função principal que executa validação completa do pipeline
    """
    print("🔍 VALIDAÇÃO COMPLETA DO PIPELINE KRITIKOS")
    print("=" * 60)
    print(f"📅 Data de execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🎯 Objetivo: Validar funcionamento das coletas para período 06/2025+")
    print(f"📋 Escopo: Todas as coletas exceto proposições")
    print("=" * 60)
    
    try:
        # Etapa 1: Executar validação do pipeline
        print("\n🔍 ETAPA 1: EXECUTANDO VALIDAÇÃO DO PIPELINE")
        print("-" * 50)
        
        validador = ValidadorPipeline()
        resultados_validacao = validador.executar_validacao_completa()
        
        # Etapa 2: Gerar relatório final
        print("\n📊 ETAPA 2: GERANDO RELATÓRIO FINAL")
        print("-" * 50)
        
        gerador = GeradorRelatorio()
        
        # Salvar relatório em ambos os formatos
        arquivo_json = gerador.salvar_relatorio_json(resultados_validacao)
        arquivo_txt = gerador.salvar_relatorio_txt(resultados_validacao)
        
        # Etapa 3: Exibir resumo final
        print("\n🎯 ETAPA 3: RESUMO FINAL DA VALIDAÇÃO")
        print("=" * 50)
        
        resumo = resultados_validacao.get('resumo_geral', {})
        total_validacoes = resumo.get('total_validacoes', 0)
        sucessos = resumo.get('sucessos', 0)
        alertas = resumo.get('alertas', 0)
        erros = resumo.get('erros', 0)
        
        print(f"📊 Total de coletas validadas: {total_validacoes}")
        print(f"✅ Coletas funcionando: {sucessos}")
        print(f"⚠️ Coletas com alertas: {alertas}")
        print(f"❌ Coletas com erros: {erros}")
        
        if total_validacoes > 0:
            percentual_sucesso = (sucessos / total_validacoes) * 100
            print(f"📈 Taxa de sucesso: {percentual_sucesso:.1f}%")
        
        print(f"\n📁 Relatórios gerados:")
        print(f"   📄 JSON: {arquivo_json}")
        print(f"   📄 TXT: {arquivo_txt}")
        
        # Conclusão final
        print("\n" + "=" * 60)
        print("🎉 CONCLUSÃO DA VALIDAÇÃO")
        print("=" * 60)
        
        if total_validacoes > 0 and sucessos == total_validacoes:
            print("🎉 SUCESSO TOTAL!")
            print("✅ Todas as coletas estão funcionando perfeitamente")
            print("✅ Pipeline validado com 100% de sucesso")
            print("✅ Período 06/2025+ está sendo respeitado")
            print("✅ Configurações centralizadas funcionando corretamente")
            print("\n🚀 O pipeline está pronto para uso em produção!")
            
        elif total_validacoes > 0 and sucessos >= total_validacoes * 0.8:
            print("👍 SUCESSO PARCIAL!")
            print("✅ Maioria das coletas funcionando bem")
            print("⚠️ Algumas melhorias podem ser necessárias")
            print("✅ Pipeline funcional para uso com ressalvas")
            
        elif total_validacoes > 0:
            print("⚠️ RESULTADO MISTO!")
            print("✅ Algumas coletas funcionando")
            print("❌ Outras precisam de atenção")
            print("🔧 Revisões recomendadas antes do uso em produção")
            
        else:
            print("❓ RESULTADO INCONCLUSIVO!")
            print("⚠️ Nenhuma coleta foi validada")
            print("🔧 Verifique as configurações e execute novamente")
        
        print(f"\n📅 Validação concluída em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 60)
        
        return {
            'status': 'sucesso' if sucessos == total_validacoes else 'parcial' if sucessos > 0 else 'erro',
            'resultados': resultados_validacao,
            'relatorios': {
                'json': arquivo_json,
                'txt': arquivo_txt
            }
        }
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO DURANTE A VALIDAÇÃO")
        print(f"❌ Detalhes: {str(e)}")
        print("=" * 60)
        print("🔧 Verifique as configurações e dependências")
        print("📋 Entre em contato com o suporte técnico se o erro persistir")
        
        return {
            'status': 'erro_critico',
            'erro': str(e),
            'resultados': None,
            'relatorios': None
        }

if __name__ == "__main__":
    resultado = main()
    
    # Exit code baseado no resultado
    if resultado.get('status') == 'sucesso':
        sys.exit(0)  # Sucesso total
    elif resultado.get('status') == 'parcial':
        sys.exit(1)  # Sucesso parcial
    elif resultado.get('status') == 'erro':
        sys.exit(2)  # Erros nas coletas
    else:
        sys.exit(3)  # Erro crítico na validação
