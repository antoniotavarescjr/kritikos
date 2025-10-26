#!/usr/bin/env python3
"""
Script de Relatório Resumido das Coletas
Gera relatório simplificado do funcionamento das coletas para o período 06/2025+
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import json

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar configurações
from config import get_coleta_config, get_data_inicio_coleta, coleta_habilitada, get_tipos_coleta_habilitados
from validacao_pipeline import ValidadorPipeline

class GeradorRelatorio:
    """
    Classe responsável por gerar relatório resumido das coletas
    """

    def __init__(self):
        """Inicializa o gerador de relatório"""
        self.data_inicio = get_data_inicio_coleta()
        self.tipos_habilitados = get_tipos_coleta_habilitados()
        
        print(f"📊 Gerador de Relatório inicializado")
        print(f"📅 Período: {self.data_inicio} até hoje")

    def gerar_relatorio_resumido(self, resultados_validacao: Dict[str, Any]) -> str:
        """
        Gera relatório resumido formatado
        
        Args:
            resultados_validacao: Resultados da validação do pipeline
            
        Returns:
            str: Relatório formatado
        """
        relatorio = []
        relatorio.append("📊 RELATÓRIO DE VALIDAÇÃO DAS COLETAS")
        relatorio.append("=" * 60)
        relatorio.append("")
        
        # Cabeçalho
        relatorio.append(f"📅 Data do Relatório: {resultados_validacao['data_validacao']}")
        relatorio.append(f"📅 Período Validado: {resultados_validacao['periodo_validado']}")
        relatorio.append(f"🔧 Tipos Habilitados: {', '.join(resultados_validacao['tipos_habilitados'])}")
        relatorio.append("")
        
        # Resumo geral
        resumo = resultados_validacao['resumo_geral']
        relatorio.append("📋 RESUMO GERAL")
        relatorio.append("-" * 30)
        relatorio.append(f"✅ Sucessos: {resumo['sucessos']}")
        relatorio.append(f"⚠️ Alertas: {resumo['alertas']}")
        relatorio.append(f"❌ Erros: {resumo['erros']}")
        relatorio.append(f"📊 Total Validado: {resumo['total_validacoes']}")
        relatorio.append("")
        
        # Status por tipo
        relatorio.append("📋 STATUS POR TIPO DE COLETA")
        relatorio.append("-" * 40)
        
        validacoes = resultados_validacao.get('validacoes', {})
        
        # Ordem padrão para exibição
        ordem_tipos = ['referencia', 'gastos', 'remuneracao', 'emendas', 'votacoes']
        
        for tipo in ordem_tipos:
            if tipo in validacoes:
                validacao = validacoes[tipo]
                status = validacao.get('status', 'desconhecido')
                dados = validacao.get('dados', {})
                
                # Ícone baseado no status
                if status == 'sucesso':
                    icone = "✅"
                    status_texto = "FUNCIONANDO"
                elif status == 'alerta':
                    icone = "⚠️"
                    status_texto = "COM ALERTAS"
                elif status == 'erro':
                    icone = "❌"
                    status_texto = "COM ERROS"
                else:
                    icone = "❓"
                    status_texto = "DESCONHECIDO"
                
                relatorio.append(f"{icone} {tipo.upper()}: {status_texto}")
                
                # Detalhes específicos por tipo
                if tipo == 'referencia' and dados:
                    relatorio.append(f"   👥 Deputados ativos: {dados.get('deputados_ativos', 0)}")
                    relatorio.append(f"   🏛️ Partidos ativos: {dados.get('partidos_ativos', 0)}")
                
                elif tipo == 'gastos' and dados:
                    relatorio.append(f"   💰 Registros: {dados.get('gastos_total', 0)}")
                    relatorio.append(f"   💸 Valor total: R$ {dados.get('valor_total', 0):,.2f}")
                
                elif tipo == 'remuneracao' and dados:
                    relatorio.append(f"   💼 Registros: {dados.get('remuneracoes_total', 0)}")
                    relatorio.append(f"   💸 Valor total: R$ {dados.get('valor_total', 0):,.2f}")
                
                elif tipo == 'emendas' and dados:
                    relatorio.append(f"   📝 Registros: {dados.get('emendas_total', 0)}")
                    relatorio.append(f"   💸 Valor total: R$ {dados.get('valor_total', 0):,.2f}")
                
                elif tipo == 'votacoes' and dados:
                    relatorio.append(f"   🗳️ Registros: {dados.get('votacoes_total', 0)}")
                
                # Erros específicos
                erros = validacao.get('erros', [])
                if erros:
                    for erro in erros:
                        relatorio.append(f"      ⚠️ {erro}")
                
                relatorio.append("")
        
        # Conclusão
        relatorio.append("🎯 CONCLUSÃO")
        relatorio.append("-" * 20)
        
        total_sucessos = resumo['sucessos']
        total_validacoes = resumo['total_validacoes']
        
        if total_validacoes > 0:
            percentual_sucesso = (total_sucessos / total_validacoes) * 100
            
            if total_sucessos == total_validacoes:
                relatorio.append("🎉 TODAS AS COLETAS ESTÃO FUNCIONANDO PERFEITAMENTE!")
                relatorio.append(f"✅ Pipeline 100% funcional para o período {resultados_validacao['periodo_validado']}")
            elif percentual_sucesso >= 80:
                relatorio.append("👍 MAIORIA DAS COLETAS ESTÃO FUNCIONANDO BEM!")
                relatorio.append(f"✅ {percentual_sucesso:.1f}% de sucesso no período {resultados_validacao['periodo_validado']}")
            elif percentual_sucesso >= 50:
                relatorio.append("⚠️ METADE DAS COLETAS ESTÃO FUNCIONANDO")
                relatorio.append(f"⚠️ {percentual_sucesso:.1f}% de sucesso - melhorias necessárias")
            else:
                relatorio.append("❌ PROBLEMAS SÉRIOS ENCONTRADOS")
                relatorio.append(f"❌ Apenas {percentual_sucesso:.1f}% funcionando - ação necessária")
        else:
            relatorio.append("❓ NENHUMA COLETA VALIDADA")
        
        relatorio.append("")
        relatorio.append("=" * 60)
        relatorio.append(f"📅 Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        return "\n".join(relatorio)

    def salvar_relatorio_json(self, resultados_validacao: Dict[str, Any], arquivo: str = None) -> str:
        """
        Salva relatório em formato JSON
        
        Args:
            resultados_validacao: Resultados da validação
            arquivo: Nome do arquivo (opcional)
            
        Returns:
            str: Caminho do arquivo salvo
        """
        if arquivo is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            arquivo = f"relatorio_validacao_{timestamp}.json"
        
        # Preparar dados para JSON
        dados_json = {
            'metadados': {
                'data_geracao': datetime.now().isoformat(),
                'periodo_validado': resultados_validacao['periodo_validado'],
                'versao': '1.0',
                'fonte': 'Pipeline Kritikos'
            },
            'configuracao': {
                'data_inicio': self.data_inicio,
                'tipos_habilitados': self.tipos_habilitados
            },
            'resumo_geral': resultados_validacao['resumo_geral'],
            'validacoes_detalhadas': resultados_validacao.get('validacoes', {})
        }
        
        # Salvar arquivo
        caminho_completo = Path(__file__).parent.parent.parent / "relatorios" / arquivo
        caminho_completo.parent.mkdir(exist_ok=True)
        
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(dados_json, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📁 Relatório JSON salvo em: {caminho_completo}")
        return str(caminho_completo)

    def salvar_relatorio_txt(self, resultados_validacao: Dict[str, Any], arquivo: str = None) -> str:
        """
        Salva relatório em formato TXT
        
        Args:
            resultados_validacao: Resultados da validação
            arquivo: Nome do arquivo (opcional)
            
        Returns:
            str: Caminho do arquivo salvo
        """
        if arquivo is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            arquivo = f"relatorio_validacao_{timestamp}.txt"
        
        # Gerar conteúdo do relatório
        conteudo = self.gerar_relatorio_resumido(resultados_validacao)
        
        # Salvar arquivo
        caminho_completo = Path(__file__).parent.parent.parent / "relatorios" / arquivo
        caminho_completo.parent.mkdir(exist_ok=True)
        
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print(f"📁 Relatório TXT salvo em: {caminho_completo}")
        return str(caminho_completo)

def main():
    """Função principal para execução do relatório"""
    print("📊 GERADOR DE RELATÓRIO DAS COLETAS")
    print("=" * 60)
    
    # Executar validação primeiro
    print("🔍 Executando validação do pipeline...")
    validador = ValidadorPipeline()
    resultados = validador.executar_validacao_completa()
    
    # Gerar relatório
    gerador = GeradorRelatorio()
    
    print("\n📊 Gerando relatório resumido...")
    
    # Salvar em ambos os formatos
    arquivo_json = gerador.salvar_relatorio_json(resultados)
    arquivo_txt = gerador.salvar_relatorio_txt(resultados)
    
    # Exibir relatório no console
    print("\n" + "=" * 60)
    relatorio_console = gerador.gerar_relatorio_resumido(resultados)
    print(relatorio_console)
    
    print(f"\n✅ Relatórios gerados com sucesso!")
    print(f"📁 JSON: {arquivo_json}")
    print(f"📁 TXT: {arquivo_txt}")

if __name__ == "__main__":
    main()
