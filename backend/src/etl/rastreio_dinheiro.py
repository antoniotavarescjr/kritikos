"""
Módulo de Rastreio Completo do Dinheiro
Segue o fluxo completo dos recursos desde a aprovação da emenda até a execução final
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado, Mandato
from models.emenda_models import EmendaParlamentar, DetalheEmenda, ExecucaoEmenda, RankingEmendas
from models.financeiro_models import GastoParlamentar

class RastreioDinheiro:
    """
    Classe responsável pelo rastreio completo do fluxo financeiro das emendas
    """

    def __init__(self):
        """Inicializa o sistema de rastreio."""
        print("✅ Sistema de Rastreio de Dinheiro inicializado")

    def analisar_fluxo_emenda(self, emenda_id: int, db: Session) -> Dict[str, Any]:
        """
        Analisa o fluxo completo de dinheiro para uma emenda específica
        """
        try:
            # Buscar emenda
            emenda = db.query(EmendaParlamentar).filter(
                EmendaParlamentar.id == emenda_id
            ).first()
            
            if not emenda:
                return {"erro": "Emenda não encontrada"}
            
            # Buscar detalhes e execuções
            detalhes = db.query(DetalheEmenda).filter(
                DetalheEmenda.emenda_id == emenda_id
            ).all()
            
            execucoes = db.query(ExecucaoEmenda).filter(
                ExecucaoEmenda.emenda_id == emenda_id
            ).all()
            
            # Calcular métricas do fluxo
            fluxo = {
                "emenda": {
                    "id": emenda.id,
                    "codigo": emenda.api_camara_id,
                    "descricao": emenda.emenda,
                    "autor": emenda.autor,
                    "valor_emendado": emenda.valor_empenhado,
                    "valor_liquidado": emenda.valor_liquidado,
                    "valor_pago": emenda.valor_pago,
                    "situacao": emenda.situacao
                },
                "fluxo_financeiro": self._calcular_fluxo_financeiro(emenda, execucoes),
                "beneficiarios": self._mapear_beneficiarios(detalhes, execucoes),
                "eficiencia": self._calcular_eficiencia(emenda),
                "documentos": self._mapear_documentos(detalhes, execucoes),
                "timeline": self._criar_timeline(emenda, detalhes, execucoes)
            }
            
            return fluxo
            
        except Exception as e:
            print(f"❌ Erro ao analisar fluxo da emenda {emenda_id}: {e}")
            return {"erro": str(e)}

    def _calcular_fluxo_financeiro(self, emenda: EmendaParlamentar, execucoes: List[ExecucaoEmenda]) -> Dict:
        """
        Calcula o fluxo financeiro completo
        """
        # Converter Decimal para float
        valor_emendado = float(emenda.valor_empenhado or 0)
        valor_liquidado = float(emenda.valor_liquidado or 0)
        valor_pago = float(emenda.valor_pago or 0)
        
        # Somar execuções
        total_executado = sum([float(e.valor_executado or 0) for e in execucoes])
        
        # Calcular taxas
        taxa_liquidacao = (valor_liquidado / valor_emendado * 100) if valor_emendado > 0 else 0
        taxa_pagamento = (valor_pago / valor_emendado * 100) if valor_emendado > 0 else 0
        taxa_execucao = (total_executado / valor_emendado * 100) if valor_emendado > 0 else 0
        
        return {
            "valor_aprovado": valor_emendado,
            "valor_empenhado": valor_emendado,
            "valor_liquidado": valor_liquidado,
            "valor_pago": valor_pago,
            "valor_executado": total_executado,
            "saldo_pendente": valor_emendado - valor_pago,
            "taxa_liquidacao": round(taxa_liquidacao, 2),
            "taxa_pagamento": round(taxa_pagamento, 2),
            "taxa_execucao": round(taxa_execucao, 2),
            "status_fluxo": self._classificar_status_fluxo(valor_emendado, valor_pago)
        }

    def _classificar_status_fluxo(self, valor_aprovado: float, valor_pago: float) -> str:
        """
        Classifica o status do fluxo financeiro
        """
        if valor_pago == 0:
            return "Não Executado"
        elif valor_pago < valor_aprovado * 0.5:
            return "Execução Parcial Baixa"
        elif valor_pago < valor_aprovado * 0.8:
            return "Execução Parcial Média"
        elif valor_pago < valor_aprovado:
            return "Execução Parcial Alta"
        else:
            return "Totalmente Executado"

    def _mapear_beneficiarios(self, detalhes: List[DetalheEmenda], execucoes: List[ExecucaoEmenda]) -> List[Dict]:
        """
        Mapeia todos os beneficiários do fluxo
        """
        beneficiarios = []
        
        # Beneficiários dos detalhes
        for detalhe in detalhes:
            if detalhe.beneficiario_nome:
                beneficiarios.append({
                    "nome": detalhe.beneficiario_nome,
                    "cpf_cnpj": detalhe.beneficiario_cnpj_cpf,
                    "tipo": "Beneficiário Principal",
                    "valor": float(detalhe.valor_documento or 0),
                    "documento": detalhe.numero_processo,
                    "data": detalhe.data_documento
                })
        
        # Favorecidos das execuções
        for execucao in execucoes:
            if execucao.favorecido_nome:
                beneficiarios.append({
                    "nome": execucao.favorecido_nome,
                    "cpf_cnpj": execucao.favorecido_cnpj_cpf,
                    "tipo": "Favorecido na Execução",
                    "valor": float(execucao.valor_executado or 0),
                    "documento": execucao.documento_resgate,
                    "data": execucao.data_execucao
                })
        
        return beneficiarios

    def _calcular_eficiencia(self, emenda: EmendaParlamentar) -> Dict:
        """
        Calcula métricas de eficiência da emenda
        """
        # Converter Decimal para float
        valor_aprovado = float(emenda.valor_empenhado or 0)
        valor_pago = float(emenda.valor_pago or 0)
        
        # Eficiência de execução
        eficiencia_execucao = (valor_pago / valor_aprovado * 100) if valor_aprovado > 0 else 0
        
        # Tempo de execução (simulado - precisaria de datas reais)
        # Aqui poderíamos calcular baseado nas datas das execuções
        tempo_medio_execucao = 180  # dias (simulado)
        
        return {
            "eficiencia_execucao": round(eficiencia_execucao, 2),
            "tempo_medio_execucao": tempo_medio_execucao,
            "classificacao": self._classificar_eficiencia(eficiencia_execucao),
            "indice_eficiencia": self._calcular_indice_eficiencia(emenda)
        }

    def _classificar_eficiencia(self, eficiencia: float) -> str:
        """
        Classifica a eficiência em categorias
        """
        if eficiencia >= 90:
            return "Excelente"
        elif eficiencia >= 70:
            return "Bom"
        elif eficiencia >= 50:
            return "Regular"
        elif eficiencia >= 30:
            return "Baixo"
        else:
            return "Crítico"

    def _calcular_indice_eficiencia(self, emenda: EmendaParlamentar) -> float:
        """
        Calcula um índice composto de eficiência (0-100)
        """
        # Converter Decimal para float
        valor_aprovado = float(emenda.valor_empenhado or 0)
        valor_pago = float(emenda.valor_pago or 0)
        
        # Fator 1: Taxa de execução (60% peso)
        taxa_execucao = (valor_pago / valor_aprovado * 100) if valor_aprovado > 0 else 0
        
        # Fator 2: Complexidade (40% peso) - baseado no tipo de emenda
        complexidade = self._calcular_complexidade_emenda(emenda.tipo_emenda)
        
        indice = (taxa_execucao * 0.6) + (complexidade * 0.4)
        return round(indice, 2)

    def _calcular_complexidade_emenda(self, tipo_emenda: str) -> float:
        """
        Calcula pontuação de complexidade baseada no tipo de emenda
        """
        # Tipos mais complexos têm pontuação mais alta
        complexidades = {
            "INDIVIDUAL": 80,
            "BANCADA": 90,
            "COMISSÃO": 70,
            "RELAUTOR": 85
        }
        
        for tipo, pontos in complexidades.items():
            if tipo.upper() in tipo_emenda.upper():
                return pontos
        
        return 60  # Padrão para tipos não identificados

    def _mapear_documentos(self, detalhes: List[DetalheEmenda], execucoes: List[ExecucaoEmenda]) -> List[Dict]:
        """
        Mapeia todos os documentos do fluxo
        """
        documentos = []
        
        # Documentos dos detalhes
        for detalhe in detalhes:
            if detalhe.numero_processo or detalhe.tipo_documento:
                documentos.append({
                    "tipo": detalhe.tipo_documento or "Processo",
                    "numero": detalhe.numero_processo,
                    "data": detalhe.data_documento,
                    "valor": float(detalhe.valor_documento or 0),
                    "observacao": detalhe.observacao
                })
        
        # Documentos das execuções
        for execucao in execucoes:
            if execucao.documento_resgate:
                documentos.append({
                    "tipo": "Documento de Resgate",
                    "numero": execucao.documento_resgate,
                    "data": execucao.data_execucao,
                    "valor": float(execucao.valor_executado or 0),
                    "observacao": f"Tipo execução: {execucao.tipo_execucao}"
                })
        
        return documentos

    def _criar_timeline(self, emenda: EmendaParlamentar, detalhes: List[DetalheEmenda], execucoes: List[ExecucaoEmenda]) -> List[Dict]:
        """
        Cria uma timeline cronológica dos eventos
        """
        timeline = []
        
        # Evento inicial: aprovação da emenda
        timeline.append({
            "data": None,  # Poderia ser data de aprovação
            "evento": "Aprovação da Emenda",
            "descricao": f"Emenda {emenda.emenda} aprovada com valor de R$ {float(emenda.valor_empenhado or 0):,.2f}",
            "valor": float(emenda.valor_empenhado or 0),
            "tipo": "aprovacao"
        })
        
        # Eventos de detalhes/documentos
        for detalhe in detalhes:
            if detalhe.data_documento:
                timeline.append({
                    "data": detalhe.data_documento,
                    "evento": "Documento Registrado",
                    "descricao": f"{detalhe.tipo_documento}: {detalhe.numero_processo}",
                    "valor": float(detalhe.valor_documento or 0),
                    "tipo": "documento"
                })
        
        # Eventos de execução
        for execucao in execucoes:
            if execucao.data_execucao:
                timeline.append({
                    "data": execucao.data_execucao,
                    "evento": "Execução Financeira",
                    "descricao": f"Pagamento/Execução: {execucao.tipo_execucao}",
                    "valor": float(execucao.valor_executado or 0),
                    "tipo": "execucao"
                })
        
        # Ordenar por data
        timeline.sort(key=lambda x: x["data"] or datetime.min)
        
        return timeline

    def gerar_relatorio_completo(self, db: Session, ano: Optional[int] = None, deputado_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Gera um relatório completo do rastreio de dinheiro
        """
        try:
            print(f"\n📊 GERANDO RELATÓRIO COMPLETO DE RASTREIO")
            print("=" * 50)
            
            # Base de consulta
            query = db.query(EmendaParlamentar)
            
            if ano:
                query = query.filter(EmendaParlamentar.ano == ano)
            
            if deputado_id:
                query = query.filter(EmendaParlamentar.deputado_id == deputado_id)
            
            emendas = query.all()
            
            if not emendas:
                return {"erro": "Nenhuma emenda encontrada para os critérios"}
            
            # Métricas gerais
            total_emendado = sum([float(e.valor_empenhado or 0) for e in emendas])
            total_pago = sum([float(e.valor_pago or 0) for e in emendas])
            taxa_execucao_geral = (total_pago / total_emendado * 100) if total_emendado > 0 else 0
            
            # Análise por emenda
            analises = []
            for emenda in emendas:
                analise = self.analisar_fluxo_emenda(emenda.id, db)
                if "erro" not in analise:
                    analises.append(analise)
            
            # Top beneficiários
            todos_beneficiarios = []
            for analise in analises:
                todos_beneficiarios.extend(analise["beneficiarios"])
            
            beneficiarios_top = self._agrupar_beneficiarios(todos_beneficiarios)
            
            # Status do fluxo
            status_fluxo = {}
            for analise in analises:
                status = analise["fluxo_financeiro"]["status_fluxo"]
                status_fluxo[status] = status_fluxo.get(status, 0) + 1
            
            relatorio = {
                "resumo": {
                    "total_emendas": len(emendas),
                    "total_emendado": total_emendado,
                    "total_pago": total_pago,
                    "taxa_execucao_geral": round(taxa_execucao_geral, 2),
                    "saldo_pendente": total_emendado - total_pago
                },
                "status_fluxo": status_fluxo,
                "beneficiarios_top": beneficiarios_top[:10],  # Top 10
                "analises_detalhadas": analises,
                "metricas_eficiencia": self._calcular_metricas_eficiencia_geral(analises)
            }
            
            print(f"✅ Relatório gerado: {len(emendas)} emendas analisadas")
            return relatorio
            
        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            return {"erro": str(e)}

    def _agrupar_beneficiarios(self, beneficiarios: List[Dict]) -> List[Dict]:
        """
        Agrupa beneficiários por nome/CNPJ e soma valores
        """
        agrupados = {}
        
        for benef in beneficiarios:
            chave = f"{benef['nome']}_{benef['cpf_cnpj']}"
            if chave not in agrupados:
                agrupados[chave] = {
                    "nome": benef["nome"],
                    "cpf_cnpj": benef["cpf_cnpj"],
                    "valor_total": 0,
                    "quantidade": 0,
                    "tipos": set()
                }
            
            agrupados[chave]["valor_total"] += benef["valor"] or 0
            agrupados[chave]["quantidade"] += 1
            agrupados[chave]["tipos"].add(benef["tipo"])
        
        # Converter para lista e ordenar por valor
        resultado = []
        for agrupado in agrupados.values():
            agrupado["tipos"] = list(agrupado["tipos"])
            resultado.append(agrupado)
        
        return sorted(resultado, key=lambda x: x["valor_total"], reverse=True)

    def _calcular_metricas_eficiencia_geral(self, analises: List[Dict]) -> Dict:
        """
        Calcula métricas gerais de eficiência
        """
        if not analises:
            return {}
        
        eficiencias = [a["eficiencia"]["eficiencia_execucao"] for a in analises]
        indices = [a["eficiencia"]["indice_eficiencia"] for a in analises]
        
        return {
            "eficiencia_media": round(sum(eficiencias) / len(eficiencias), 2),
            "eficiencia_max": max(eficiencias),
            "eficiencia_min": min(eficiencias),
            "indice_eficiencia_medio": round(sum(indices) / len(indices), 2),
            "distribuicao_eficiencia": self._distribuicao_eficiencia(eficiencias)
        }

    def _distribuicao_eficiencia(self, eficiencias: List[float]) -> Dict:
        """
        Calcula a distribuição de eficiência por categoria
        """
        distribuicao = {
            "Excelente": 0,
            "Bom": 0,
            "Regular": 0,
            "Baixo": 0,
            "Crítico": 0
        }
        
        for ef in eficiencias:
            if ef >= 90:
                distribuicao["Excelente"] += 1
            elif ef >= 70:
                distribuicao["Bom"] += 1
            elif ef >= 50:
                distribuicao["Regular"] += 1
            elif ef >= 30:
                distribuicao["Baixo"] += 1
            else:
                distribuicao["Crítico"] += 1
        
        return distribuicao

def main():
    """
    Função principal para execução standalone
    """
    print("💰 RASTREIO COMPLETO DO DINHEIRO")
    print("=" * 50)
    
    from models.db_utils import get_db_session
    
    db_session = get_db_session()
    
    try:
        rastreio = RastreioDinheiro()
        
        # Gerar relatório completo para 2024
        relatorio = rastreio.gerar_relatorio_completo(db_session, ano=2024)
        
        if "erro" not in relatorio:
            print(f"\n📋 RESUMO DO RASTREIO - 2024")
            print("=" * 35)
            print(f"📄 Total de emendas: {relatorio['resumo']['total_emendas']}")
            print(f"💰 Total emendado: R$ {relatorio['resumo']['total_emendado']:,.2f}")
            print(f"💸 Total pago: R$ {relatorio['resumo']['total_pago']:,.2f}")
            print(f"📈 Taxa de execução: {relatorio['resumo']['taxa_execucao_geral']}%")
            print(f"⏳ Saldo pendente: R$ {relatorio['resumo']['saldo_pendente']:,.2f}")
            
            print(f"\n🏆 TOP 5 BENEFICIÁRIOS")
            print("=" * 25)
            for i, benef in enumerate(relatorio['beneficiarios_top'][:5], 1):
                print(f"{i}. {benef['nome']}: R$ {benef['valor_total']:,.2f}")
            
            print(f"\n📊 DISTRIBUIÇÃO DE STATUS")
            print("=" * 25)
            for status, count in relatorio['status_fluxo'].items():
                print(f"{status}: {count}")
        
        print(f"\n✅ Rastreio concluído!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE O RASTREIO: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
