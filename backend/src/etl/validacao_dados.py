#!/usr/bin/env python3
"""
Script de validação de dados para o sistema Kritikos
Verifica qualidade, consistência e integridade dos dados
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar modelos
from models.db_utils import get_db_session
from models.politico_models import Deputado, Mandato
from models.base_models import Partido, Estado
from models.emenda_models import EmendaParlamentar, RankingEmendas
from models.financeiro_models import GastoParlamentar

class ValidadorDados:
    """
    Classe responsável por validar a qualidade dos dados no sistema
    """

    def __init__(self):
        """Inicializa o validador."""
        self.erros = []
        self.alertas = []
        self.estatisticas = {}

    def executar_validacao_completa(self, db: Session) -> Dict[str, Any]:
        """
        Executa todas as validações e retorna um relatório completo
        """
        print("🔍 INICIANDO VALIDAÇÃO COMPLETA DE DADOS")
        print("=" * 50)
        
        # 1. Validação de integridade referencial
        self._validar_integridade_referencial(db)
        
        # 2. Validação de qualidade de dados
        self._validar_qualidade_dados(db)
        
        # 3. Validação de regras de negócio
        self._validar_regras_negocio(db)
        
        # 4. Validação de duplicatas
        self._validar_duplicatas(db)
        
        # 5. Análise de completeza
        self._analisar_completeza(db)
        
        # Gerar relatório
        relatorio = self._gerar_relatorio()
        
        print(f"✅ Validação concluída!")
        print(f"   📊 Erros encontrados: {len(self.erros)}")
        print(f"   ⚠️ Alertas: {len(self.alertas)}")
        
        return relatorio

    def _validar_integridade_referencial(self, db: Session):
        """
        Verifica integridade das relações entre tabelas
        """
        print("\n🔗 Validando integridade referencial...")
        
        # Verificar emendas sem deputado
        emendas_sem_deputado = db.query(EmendaParlamentar).filter(
            EmendaParlamentar.deputado_id.is_(None)
        ).count()
        
        if emendas_sem_deputado > 0:
            self.erro(f"Emendas sem deputado: {emendas_sem_deputado}")
        
        # Verificar gastos sem deputado
        gastos_sem_deputado = db.query(GastoParlamentar).filter(
            GastoParlamentar.deputado_id.is_(None)
        ).count()
        
        if gastos_sem_deputado > 0:
            self.erro(f"Gastos sem deputado: {gastos_sem_deputado}")
        
        # Verificar mandatos sem partido
        mandatos_sem_partido = db.query(Mandato).filter(
            Mandato.partido_id.is_(None)
        ).count()
        
        if mandatos_sem_partido > 0:
            self.alerta(f"Mandatos sem partido: {mandatos_sem_partido}")
        
        # Verificar deputados sem mandato
        deputados_sem_mandato = db.execute(text("""
            SELECT COUNT(*) FROM deputados d 
            LEFT JOIN mandatos m ON d.id = m.deputado_id 
            WHERE m.id IS NULL
        """)).scalar()
        
        if deputados_sem_mandato > 0:
            self.alerta(f"Deputados sem mandato: {deputados_sem_mandato}")

    def _validar_qualidade_dados(self, db: Session):
        """
        Verifica qualidade dos dados (valores nulos, formatos, etc)
        """
        print("\n📊 Validando qualidade dos dados...")
        
        # Verificar valores monetários negativos em emendas
        emendas_valor_negativo = db.query(EmendaParlamentar).filter(
            or_(
                EmendaParlamentar.valor_emenda < 0,
                EmendaParlamentar.valor_empenhado < 0,
                EmendaParlamentar.valor_pago < 0
            )
        ).all()
        
        if emendas_valor_negativo:
            self.erro(f"Emendas com valores negativos: {len(emendas_valor_negativo)}")
            for emenda in emendas_valor_negativo[:5]:  # Mostrar primeiros 5
                self.erro(f"  - Emenda {emenda.id}: valor_emenda={emenda.valor_emenda}, valor_empenhado={emenda.valor_empenhado}, valor_pago={emenda.valor_pago}")
        
        # Verificar gastos com valores negativos e corrigir automaticamente
        gastos_valor_negativo = db.query(GastoParlamentar).filter(
            GastoParlamentar.valor_liquido < 0
        ).all()
        
        if gastos_valor_negativo:
            self.erro(f"Gastos com valores negativos: {len(gastos_valor_negativo)}")
            self._corrigir_gastos_negativos(gastos_valor_negativo, db)
        
        # Verificar datas futuras
        data_atual = datetime.now().date()
        gastos_futuros = db.query(GastoParlamentar).filter(
            GastoParlamentar.ano > data_atual.year
        ).count()
        
        if gastos_futuros > 0:
            self.alerta(f"Gastos com datas futuras: {gastos_futuros}")
        
        # Verificar nomes vazios
        deputados_nome_vazio = db.query(Deputado).filter(
            or_(
                Deputado.nome.is_(None),
                Deputado.nome == '',
                func.trim(Deputado.nome) == ''
            )
        ).count()
        
        if deputados_nome_vazio > 0:
            self.erro(f"Deputados com nome vazio: {deputados_nome_vazio}")

    def _validar_regras_negocio(self, db: Session):
        """
        Verifica regras de negócio específicas
        """
        print("\n📋 Validando regras de negócio...")
        
        # Verificar se valor pago é maior que valor empenhado
        emendas_pagamento_maior = db.query(EmendaParlamentar).filter(
            and_(
                EmendaParlamentar.valor_pago > EmendaParlamentar.valor_empenhado,
                EmendaParlamentar.valor_empenhado > 0
            )
        ).count()
        
        if emendas_pagamento_maior > 0:
            self.alerta(f"Emendas com pagamento maior que empenhado: {emendas_pagamento_maior}")
        
        # Verificar anos de emendas fora do esperado
        emendas_fora_ano = db.query(EmendaParlamentar).filter(
            or_(
                EmendaParlamentar.ano < 2020,
                EmendaParlamentar.ano > 2025
            )
        ).count()
        
        if emendas_fora_ano > 0:
            self.alerta(f"Emendas com anos fora do esperado (2020-2025): {emendas_fora_ano}")
        
        # Verificar gastos com mês inválido
        gastos_mes_invalido = db.query(GastoParlamentar).filter(
            or_(
                GastoParlamentar.mes < 1,
                GastoParlamentar.mes > 12
            )
        ).count()
        
        if gastos_mes_invalido > 0:
            self.erro(f"Gastos com mês inválido: {gastos_mes_invalido}")

    def _validar_duplicatas(self, db: Session):
        """
        Verifica existência de duplicatas
        """
        print("\n🔍 Validando duplicatas...")
        
        # Verificar deputados duplicados por API ID
        deps_duplicados_api = db.execute(text("""
            SELECT api_camara_id, COUNT(*) as count 
            FROM deputados 
            WHERE api_camara_id IS NOT NULL 
            GROUP BY api_camara_id 
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if deps_duplicados_api:
            self.erro(f"Deputados duplicados por API ID: {len(deps_duplicados_api)}")
        
        # Verificar emendas duplicadas
        emendas_duplicadas = db.execute(text("""
            SELECT api_camara_id, COUNT(*) as count 
            FROM emendas_parlamentares 
            WHERE api_camara_id IS NOT NULL 
            GROUP BY api_camara_id 
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if emendas_duplicadas:
            self.erro(f"Emendas duplicadas: {len(emendas_duplicadas)}")
        
        # Verificar CPFs duplicados
        cpfs_duplicados = db.execute(text("""
            SELECT cpf, COUNT(*) as count 
            FROM deputados 
            WHERE cpf IS NOT NULL AND cpf != '' 
            GROUP BY cpf 
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if cpfs_duplicados:
            self.alerta(f"CPFs duplicados: {len(cpfs_duplicados)}")

    def _analisar_completeza(self, db: Session):
        """
        Analisa a completeza dos dados
        """
        print("\n📈 Analisando completeza dos dados...")
        
        # Completeza de dados de deputados
        total_deputados = db.query(Deputado).count()
        
        if total_deputados > 0:
            deps_sem_email = db.query(Deputado).filter(
                or_(
                    Deputado.email.is_(None),
                    Deputado.email == ''
                )
            ).count()
            
            deps_sem_cpf = db.query(Deputado).filter(
                or_(
                    Deputado.cpf.is_(None),
                    Deputado.cpf == ''
                )
            ).count()
            
            deps_sem_foto = db.query(Deputado).filter(
                or_(
                    Deputado.foto_url.is_(None),
                    Deputado.foto_url == ''
                )
            ).count()
            
            self.estatisticas['completeza_deputados'] = {
                'total': total_deputados,
                'sem_email': deps_sem_email,
                'sem_cpf': deps_sem_cpf,
                'sem_foto': deps_sem_foto,
                'percentual_email': round((1 - deps_sem_email/total_deputados) * 100, 2),
                'percentual_cpf': round((1 - deps_sem_cpf/total_deputados) * 100, 2),
                'percentual_foto': round((1 - deps_sem_foto/total_deputados) * 100, 2)
            }
        
        # Completeza de dados de emendas
        total_emendas = db.query(EmendaParlamentar).count()
        
        if total_emendas > 0:
            emendas_sem_valor = db.query(EmendaParlamentar).filter(
                EmendaParlamentar.valor_emenda.is_(None)
            ).count()
            
            emendas_sem_beneficiario = db.query(EmendaParlamentar).filter(
                or_(
                    EmendaParlamentar.beneficiario_principal.is_(None),
                    EmendaParlamentar.beneficiario_principal == ''
                )
            ).count()
            
            self.estatisticas['completeza_emendas'] = {
                'total': total_emendas,
                'sem_valor': emendas_sem_valor,
                'sem_beneficiario': emendas_sem_beneficiario,
                'percentual_valor': round((1 - emendas_sem_valor/total_emendas) * 100, 2),
                'percentual_beneficiario': round((1 - emendas_sem_beneficiario/total_emendas) * 100, 2)
            }
        
        # Completeza de dados de gastos
        total_gastos = db.query(GastoParlamentar).count()
        
        if total_gastos > 0:
            gastos_sem_fornecedor = db.query(GastoParlamentar).filter(
                or_(
                    GastoParlamentar.fornecedor_nome.is_(None),
                    GastoParlamentar.fornecedor_nome == ''
                )
            ).count()
            
            gastos_sem_documento = db.query(GastoParlamentar).filter(
                or_(
                    GastoParlamentar.numero_documento.is_(None),
                    GastoParlamentar.numero_documento == ''
                )
            ).count()
            
            self.estatisticas['completeza_gastos'] = {
                'total': total_gastos,
                'sem_fornecedor': gastos_sem_fornecedor,
                'sem_documento': gastos_sem_documento,
                'percentual_fornecedor': round((1 - gastos_sem_fornecedor/total_gastos) * 100, 2),
                'percentual_documento': round((1 - gastos_sem_documento/total_gastos) * 100, 2)
            }

    def erro(self, mensagem: str):
        """Adiciona um erro à lista de erros"""
        self.erros.append(mensagem)
        print(f"   ❌ {mensagem}")

    def alerta(self, mensagem: str):
        """Adiciona um alerta à lista de alertas"""
        self.alertas.append(mensagem)
        print(f"   ⚠️ {mensagem}")

    def _gerar_relatorio(self) -> Dict[str, Any]:
        """
        Gera um relatório completo da validação
        """
        return {
            "data_validacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "resumo": {
                "total_erros": len(self.erros),
                "total_alertas": len(self.alertas),
                "status": "SUCESSO" if len(self.erros) == 0 else "ERROS_ENCONTRADOS"
            },
            "erros": self.erros,
            "alertas": self.alertas,
            "estatisticas": self.estatisticas,
            "recomendacoes": self._gerar_recomendacoes()
        }

    def _corrigir_gastos_negativos(self, gastos_negativos: List, db: Session):
        """
        Corrige automaticamente gastos com valores negativos
        """
        try:
            corrigidos = 0
            for gasto in gastos_negativos:
                # Converter valor negativo para positivo (provavelmente erro de sinal)
                if gasto.valor_liquido < 0:
                    valor_original = gasto.valor_liquido
                    gasto.valor_liquido = abs(gasto.valor_liquido)
                    
                    # Corrigir também valor_documento se for negativo
                    if gasto.valor_documento and gasto.valor_documento < 0:
                        gasto.valor_documento = abs(gasto.valor_documento)
                    
                    # Corrigir valor_glosa se for negativo
                    if gasto.valor_glosa and gasto.valor_glosa < 0:
                        gasto.valor_glosa = abs(gasto.valor_glosa)
                    
                    corrigidos += 1
                    print(f"      🔧 Corrigido gasto {gasto.id}: {valor_original} → {gasto.valor_liquido}")
            
            if corrigidos > 0:
                db.commit()
                print(f"      ✅ {corrigidos} gastos corrigidos automaticamente")
            
        except Exception as e:
            print(f"      ❌ Erro ao corrigir gastos: {e}")
            db.rollback()

    def _gerar_recomendacoes(self) -> List[str]:
        """
        Gera recomendações com base nos problemas encontrados
        """
        recomendacoes = []
        
        # Recomendações baseadas nos erros
        if any("duplicados" in erro for erro in self.erros):
            recomendacoes.append("Executar limpeza de duplicatas para garantir integridade dos dados")
        
        if any("valores negativos" in erro for erro in self.erros):
            recomendacoes.append("Revisar processos de importação para evitar valores negativos")
        
        if any("sem deputado" in erro for erro in self.erros):
            recomendacoes.append("Verificar integridade referencial e restaurar relacionamentos")
        
        # Recomendações baseadas nos alertas
        if any("completo" in alerta for alerta in self.alertas):
            recomendacoes.append("Melhorar processos de coleta para aumentar completeza dos dados")
        
        if not recomendacoes:
            recomendacoes.append("Dados parecem estar em bom estado. Continue com o monitoramento regular.")
        
        return recomendacoes

def main():
    """
    Função principal para execução standalone
    """
    print("🔍 VALIDAÇÃO DE DADOS - SISTEMA KRITIKOS")
    print("=" * 60)
    
    db_session = get_db_session()
    
    try:
        validador = ValidadorDados()
        relatorio = validador.executar_validacao_completa(db_session)
        
        # Exibir resumo final
        print(f"\n📋 RELATÓRIO FINAL")
        print("=" * 30)
        print(f"📅 Data: {relatorio['data_validacao']}")
        print(f"📊 Status: {relatorio['resumo']['status']}")
        print(f"❌ Erros: {relatorio['resumo']['total_erros']}")
        print(f"⚠️ Alertas: {relatorio['resumo']['total_alertas']}")
        
        # Exibir estatísticas de completeza
        if 'completeza_deputados' in relatorio['estatisticas']:
            comp_deps = relatorio['estatisticas']['completeza_deputados']
            print(f"\n👥 Completeza - Deputados:")
            print(f"   📧 Email: {comp_deps['percentual_email']}%")
            print(f"   🆔 CPF: {comp_deps['percentual_cpf']}%")
            print(f"   📸 Foto: {comp_deps['percentual_foto']}%")
        
        if 'completeza_emendas' in relatorio['estatisticas']:
            comp_emendas = relatorio['estatisticas']['completeza_emendas']
            print(f"\n📋 Completeza - Emendas:")
            print(f"   💰 Valor: {comp_emendas['percentual_valor']}%")
            print(f"   🎯 Beneficiário: {comp_emendas['percentual_beneficiario']}%")
        
        if 'completeza_gastos' in relatorio['estatisticas']:
            comp_gastos = relatorio['estatisticas']['completeza_gastos']
            print(f"\n💸 Completeza - Gastos:")
            print(f"   🏪 Fornecedor: {comp_gastos['percentual_fornecedor']}%")
            print(f"   📄 Documento: {comp_gastos['percentual_documento']}%")
        
        # Exibir recomendações
        if relatorio['recomendacoes']:
            print(f"\n💡 RECOMENDAÇÕES:")
            print("=" * 25)
            for i, rec in enumerate(relatorio['recomendacoes'], 1):
                print(f"{i}. {rec}")
        
        return relatorio
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE VALIDAÇÃO: {e}")
        db_session.rollback()
        return None
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
