#!/usr/bin/env python3
"""
Validação da Coleta de Emendas Orçamentárias
Verifica integridade, quantidade e qualidade dos dados salvos
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "src"))
# --- Fim do Bloco ---

# Importar modelos
from models.database import get_db
from models.politico_models import Deputado
from models.emenda_models import EmendaParlamentar, DetalheEmenda, RankingEmendas

def validar_coleta_emendas(db: Session) -> Dict[str, Any]:
    """
    Validação completa da coleta de emendas
    """
    print("🔍 VALIDAÇÃO COMPLETA DA COLETA DE EMENDAS")
    print("=" * 60)
    
    resultado = {
        'data_validacao': datetime.now().isoformat(),
        'emendas': {},
        'detalhes': {},
        'ranking': {},
        'integridade': {},
        'erros': []
    }
    
    try:
        # 1. Validar Emendas
        print("\n📄 VALIDANDO EMENDAS")
        print("-" * 30)
        
        emendas_stats = db.query(
            func.count(EmendaParlamentar.id).label('total'),
            func.count(func.distinct(EmendaParlamentar.ano)).label('anos_distintos'),
            func.count(func.distinct(EmendaParlamentar.tipo_emenda)).label('tipos_distintos'),
            func.count(func.distinct(EmendaParlamentar.deputado_id)).label('deputados_distintos'),
            func.sum(EmendaParlamentar.valor_emenda).label('valor_total'),
            func.avg(EmendaParlamentar.valor_emenda).label('valor_medio'),
            func.min(EmendaParlamentar.valor_emenda).label('valor_minimo'),
            func.max(EmendaParlamentar.valor_emenda).label('valor_maximo')
        ).first()
        
        resultado['emendas'] = {
            'total_registros': emendas_stats.total or 0,
            'anos_distintos': emendas_stats.anos_distintos or 0,
            'tipos_distintos': emendas_stats.tipos_distintos or 0,
            'deputados_distintos': emendas_stats.deputados_distintos or 0,
            'valor_total': float(emendas_stats.valor_total or 0),
            'valor_medio': float(emendas_stats.valor_medio or 0),
            'valor_minimo': float(emendas_stats.valor_minimo or 0),
            'valor_maximo': float(emendas_stats.valor_maximo or 0)
        }
        
        print(f"   ✅ Total de emendas: {emendas_stats.total}")
        print(f"   ✅ Anos distintos: {emendas_stats.anos_distintos}")
        print(f"   ✅ Tipos distintos: {emendas_stats.tipos_distintos}")
        print(f"   ✅ Deputados distintos: {emendas_stats.deputados_distintos}")
        print(f"   ✅ Valor total: R$ {emendas_stats.valor_total:,.2f}")
        print(f"   ✅ Valor médio: R$ {emendas_stats.valor_medio:,.2f}")
        
        # 2. Validar por Ano
        print("\n📅 VALIDANDO POR ANO")
        print("-" * 30)
        
        emendas_por_ano = db.query(
            EmendaParlamentar.ano,
            func.count(EmendaParlamentar.id).label('quantidade'),
            func.sum(EmendaParlamentar.valor_emenda).label('valor_total'),
            func.avg(EmendaParlamentar.valor_emenda).label('valor_medio')
        ).group_by(EmendaParlamentar.ano).order_by(EmendaParlamentar.ano.desc()).all()
        
        resultado['emendas']['por_ano'] = {}
        
        for ano_data in emendas_por_ano:
            ano = ano_data.ano
            valor_total = ano_data.valor_total or 0
            valor_medio = ano_data.valor_medio or 0
            resultado['emendas']['por_ano'][ano] = {
                'quantidade': ano_data.quantidade,
                'valor_total': float(valor_total),
                'valor_medio': float(valor_medio)
            }
            print(f"   ✅ {ano}: {ano_data.quantidade} emendas, R$ {valor_total:,.2f}")
        
        # 3. Validar por Tipo
        print("\n🏷️ VALIDANDO POR TIPO")
        print("-" * 30)
        
        emendas_por_tipo = db.query(
            EmendaParlamentar.tipo_emenda,
            func.count(EmendaParlamentar.id).label('quantidade'),
            func.sum(EmendaParlamentar.valor_emenda).label('valor_total'),
            func.avg(EmendaParlamentar.valor_emenda).label('valor_medio')
        ).group_by(EmendaParlamentar.tipo_emenda).order_by(func.count(EmendaParlamentar.id).desc()).all()
        
        resultado['emendas']['por_tipo'] = {}
        
        for tipo_data in emendas_por_tipo:
            tipo = tipo_data.tipo_emenda
            valor_total = tipo_data.valor_total or 0
            valor_medio = tipo_data.valor_medio or 0
            resultado['emendas']['por_tipo'][tipo] = {
                'quantidade': tipo_data.quantidade,
                'valor_total': float(valor_total),
                'valor_medio': float(valor_medio)
            }
            print(f"   ✅ {tipo}: {tipo_data.quantidade} emendas, R$ {valor_total:,.2f}")
        
        # 4. Validar Detalhes
        print("\n📋 VALIDANDO DETALHES")
        print("-" * 30)
        
        detalhes_stats = db.query(
            func.count(DetalheEmenda.id).label('total'),
            func.count(func.distinct(DetalheEmenda.emenda_id)).label('emendas_com_detalhe')
        ).first()
        
        resultado['detalhes'] = {
            'total_registros': detalhes_stats.total or 0,
            'emendas_com_detalhes': detalhes_stats.emendas_com_detalhe or 0
        }
        
        print(f"   ✅ Total de detalhes: {detalhes_stats.total}")
        print(f"   ✅ Emendas com detalhes: {detalhes_stats.emendas_com_detalhe}")
        
        # 5. Validar Ranking
        print("\n🏆 VALIDANDO RANKING")
        print("-" * 30)
        
        ranking_stats = db.query(
            func.count(RankingEmendas.id).label('total'),
            func.count(func.distinct(RankingEmendas.ano_referencia)).label('anos_distintos'),
            func.count(func.distinct(RankingEmendas.deputado_id)).label('deputados_distintos')
        ).first()
        
        resultado['ranking'] = {
            'total_registros': ranking_stats.total or 0,
            'anos_distintos': ranking_stats.anos_distintos or 0,
            'deputados_distintos': ranking_stats.deputados_distintos or 0
        }
        
        print(f"   ✅ Total de rankings: {ranking_stats.total}")
        print(f"   ✅ Anos distintos: {ranking_stats.anos_distintos}")
        print(f"   ✅ Deputados distintos: {ranking_stats.deputados_distintos}")
        
        # 6. Validar Integridade
        print("\n🔒 VALIDANDO INTEGRIDADE")
        print("-" * 30)
        
        # Verificar emendas sem valor
        emendas_sem_valor = db.query(EmendaParlamentar).filter(
            or_(
                EmendaParlamentar.valor_emenda.is_(None),
                EmendaParlamentar.valor_emenda <= 0
            )
        ).count()
        
        # Verificar emendas sem autor
        emendas_sem_autor = db.query(EmendaParlamentar).filter(
            EmendaParlamentar.deputado_id.is_(None)
        ).count()
        
        # Verificar emendas com dados incompletos
        emendas_incompletas = db.query(EmendaParlamentar).filter(
            or_(
                EmendaParlamentar.emenda.is_(None),
                EmendaParlamentar.local.is_(None),
                EmendaParlamentar.natureza.is_(None)
            )
        ).count()
        
        resultado['integridade'] = {
            'emendas_sem_valor': emendas_sem_valor,
            'emendas_sem_autor': emendas_sem_autor,
            'emendas_incompletas': emendas_incompletas,
            'percentual_completude': 0
        }
        
        total_emendas = resultado['emendas']['total_registros']
        if total_emendas > 0:
            emendas_completas = total_emendas - emendas_incompletas
            resultado['integridade']['percentual_completude'] = (emendas_completas / total_emendas) * 100
        
        print(f"   ✅ Emendas sem valor: {emendas_sem_valor}")
        print(f"   ✅ Emendas sem autor: {emendas_sem_autor}")
        print(f"   ✅ Emendas incompletas: {emendas_incompletas}")
        print(f"   ✅ Percentual completude: {resultado['integridade']['percentual_completude']:.1f}%")
        
        # 7. Verificar Duplicatas
        print("\n🔍 VALIDANDO DUPLICATAS")
        print("-" * 30)
        
        duplicatas = db.query(
            EmendaParlamentar.api_camara_id,
            func.count(EmendaParlamentar.id).label('ocorrencias')
        ).group_by(EmendaParlamentar.api_camara_id).having(
            func.count(EmendaParlamentar.id) > 1
        ).count()
        
        resultado['integridade']['duplicatas'] = duplicatas
        print(f"   ✅ Códigos duplicados: {duplicatas}")
        
        # 8. Verificar Consistência de Valores
        print("\n💰 VALIDANDO CONSISTÊNCIA DE VALORES")
        print("-" * 30)
        
        # Verificar valores muito altos ou muito baixos
        valores_extremos = db.query(EmendaParlamentar).filter(
            or_(
                EmendaParlamentar.valor_emenda > 10000000,  # Mais de 10 milhões
                EmendaParlamentar.valor_emenda < 100      # Menos de 100 reais
            )
        ).limit(10).all()
        
        resultado['integridade']['valores_extremos'] = len(valores_extremos)
        
        if valores_extremos:
            print(f"   ⚠️ Valores extremos encontrados: {len(valores_extremos)}")
            for emenda in valores_extremos[:3]:  # Mostrar apenas 3 exemplos
                print(f"      - {emenda.tipo_emenda} {emenda.numero}/{emenda.ano}: R$ {emenda.valor_emenda:,.2f}")
        else:
            print("   ✅ Nenhum valor extremo encontrado")
        
        # 9. Status Final
        print("\n📊 RESUMO DA VALIDAÇÃO")
        print("=" * 40)
        
        total_erros = (
            resultado['integridade']['emendas_sem_valor'] +
            resultado['integridade']['emendas_sem_autor'] +
            resultado['integridade']['emendas_incompletas'] +
            resultado['integridade']['duplicatas']
        )
        
        if total_erros == 0:
            print("   ✅ VALIDAÇÃO CONCLUÍDA SEM ERROS!")
            print("   🎉 Todos os dados estão consistentes!")
        else:
            print(f"   ⚠️ ENCONTRADOS {total_erros} PROBLEMAS")
            print("   🔧 Recomendada revisão dos dados")
        
        resultado['status_final'] = 'SUCESSO' if total_erros == 0 else 'ALERTA'
        resultado['total_erros'] = total_erros
        
        return resultado
        
    except Exception as e:
        print(f"❌ ERRO DURANTE VALIDAÇÃO: {e}")
        resultado['erros'].append(f"Erro geral: {str(e)}")
        resultado['status_final'] = 'ERRO'
        return resultado

def gerar_relatorio_validacao(resultado: Dict[str, Any]) -> str:
    """
    Gera relatório formatado da validação
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"relatorio_validacao_emendas_{timestamp}.md"
    caminho_arquivo = Path(__file__).parent / nome_arquivo
    
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        f.write("# 📊 RELATÓRIO DE VALIDAÇÃO - COLETA DE EMENDAS\n\n")
        f.write(f"**Data/Hora:** {resultado['data_validacao']}\n")
        f.write(f"**Status Final:** {resultado['status_final']}\n\n")
        
        f.write("## 📄 ESTATÍSTICAS DE EMENDAS\n\n")
        f.write(f"- **Total de Registros:** {resultado['emendas']['total_registros']}\n")
        f.write(f"- **Anos Distintos:** {resultado['emendas']['anos_distintos']}\n")
        f.write(f"- **Tipos Distintos:** {resultado['emendas']['tipos_distintos']}\n")
        f.write(f"- **Deputados Distintos:** {resultado['emendas']['deputados_distintos']}\n")
        f.write(f"- **Valor Total:** R$ {resultado['emendas']['valor_total']:,.2f}\n")
        f.write(f"- **Valor Médio:** R$ {resultado['emendas']['valor_medio']:,.2f}\n")
        f.write(f"- **Valor Mínimo:** R$ {resultado['emendas']['valor_minimo']:,.2f}\n")
        f.write(f"- **Valor Máximo:** R$ {resultado['emendas']['valor_maximo']:,.2f}\n\n")
        
        f.write("### 📅 EMENDAS POR ANO\n\n")
        f.write("| Ano | Quantidade | Valor Total | Valor Médio |\n")
        f.write("|------|------------|-------------|-------------|\n")
        
        for ano, dados in resultado['emendas']['por_ano'].items():
            f.write(f"| {ano} | {dados['quantidade']} | R$ {dados['valor_total']:,.2f} | R$ {dados['valor_medio']:,.2f} |\n")
        
        f.write("\n### 🏷️ EMENDAS POR TIPO\n\n")
        f.write("| Tipo | Quantidade | Valor Total | Valor Médio |\n")
        f.write("|------|------------|-------------|-------------|\n")
        
        for tipo, dados in resultado['emendas']['por_tipo'].items():
            f.write(f"| {tipo} | {dados['quantidade']} | R$ {dados['valor_total']:,.2f} | R$ {dados['valor_medio']:,.2f} |\n")
        
        f.write("\n## 📋 ESTATÍSTICAS DE DETALHES\n\n")
        f.write(f"- **Total de Registros:** {resultado['detalhes']['total_registros']}\n")
        f.write(f"- **Emendas com Detalhes:** {resultado['detalhes']['emendas_com_detalhes']}\n\n")
        
        f.write("## 🏆 ESTATÍSTICAS DE RANKING\n\n")
        f.write(f"- **Total de Registros:** {resultado['ranking']['total_registros']}\n")
        f.write(f"- **Anos Distintos:** {resultado['ranking']['anos_distintos']}\n")
        f.write(f"- **Deputados Distintos:** {resultado['ranking']['deputados_distintos']}\n\n")
        
        f.write("## 🔒 ANÁLISE DE INTEGRIDADE\n\n")
        f.write(f"- **Emendas sem Valor:** {resultado['integridade']['emendas_sem_valor']}\n")
        f.write(f"- **Emendas sem Autor:** {resultado['integridade']['emendas_sem_autor']}\n")
        f.write(f"- **Emendas Incompletas:** {resultado['integridade']['emendas_incompletas']}\n")
        f.write(f"- **Códigos Duplicados:** {resultado['integridade']['duplicatas']}\n")
        f.write(f"- **Valores Extremos:** {resultado['integridade']['valores_extremos']}\n")
        f.write(f"- **Percentual Completude:** {resultado['integridade']['percentual_completude']:.1f}%\n\n")
        
        if resultado['erros']:
            f.write("## ❌ ERROS ENCONTRADOS\n\n")
            for erro in resultado['erros']:
                f.write(f"- {erro}\n")
            f.write("\n")
        
        f.write("---\n")
        f.write("*Relatório gerado automaticamente pelo sistema Kritikos*\n")
    
    return str(caminho_arquivo)

def main():
    """
    Função principal para execução standalone
    """
    print("🔍 VALIDAÇÃO DA COLETA DE EMENDAS ORÇAMENTÁRIAS")
    print("=" * 70)
    
    # Usar o utilitário db_utils para obter sessão do banco
    from models.db_utils import get_db_session
    
    db_session = next(get_db())
    
    try:
        # Executar validação completa
        resultado = validar_coleta_emendas(db_session)
        
        # Gerar relatório
        caminho_relatorio = gerar_relatorio_validacao(resultado)
        
        print(f"\n✅ VALIDAÇÃO CONCLUÍDA!")
        print(f"📁 Relatório salvo: {caminho_relatorio}")
        print(f"📊 Status: {resultado['status_final']}")
        print(f"🔍 Total de erros: {resultado.get('total_erros', 0)}")
        
        if resultado['status_final'] == 'SUCESSO':
            print("\n🎉 PARABÉNS! Coleta validada com sucesso!")
        else:
            print("\n⚠️ ATENÇÃO! Foram encontrados problemas que precisam ser revisados.")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE VALIDAÇÃO: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
