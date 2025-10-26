#!/usr/bin/env python3
"""
Coletor Estendido de Emendas Orçamentárias
Configuração para cobertura máxima e período estendido (06/2025 - hoje)
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "src"))
# --- Fim do Bloco ---

# Importar coletor existente
from src.etl.coleta_emendas_transparencia import ColetorEmendasTransparencia
from models.db_utils import get_db_session

class ColetorEmendasEstendido(ColetorEmendasTransparencia):
    """
    Coletor estendido com configurações otimizadas para cobertura máxima
    """
    
    def __init__(self):
        """Inicializa o coletor estendido"""
        super().__init__()
        print("🚀 COLETOR ESTENDIDO DE EMENDAS INICIALIZADO")
        print("=" * 60)
        
        # Configurações estendidas
        self.configuracoes = {
            'limite_por_ano': 2000,  # Aumentado para cobertura máxima
            'timeout_requisicao': 60,   # Timeout aumentado
            'delay_entre_requisicoes': 1.0,  # 1 segundo entre requisições
            'max_tentativas': 3,        # Máximo de tentativas
            'pagina_maxima': 200        # Limite de segurança
        }
        
        print(f"📊 CONFIGURAÇÕES ESTENDIDAS:")
        print(f"   🎯 Limite por ano: {self.configuracoes['limite_por_ano']}")
        print(f"   ⏱️ Timeout: {self.configuracoes['timeout_requisicao']}s")
        print(f"   ⏳ Delay: {self.configuracoes['delay_entre_requisicoes']}s")
        print(f"   🔄 Máx tentativas: {self.configuracoes['max_tentativas']}")
        print(f"   📄 Página máxima: {self.configuracoes['pagina_maxima']}")

    def fazer_requisicao_com_retry(self, params: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Faz requisição com sistema de retry robusto
        """
        for tentativa in range(self.configuracoes['max_tentativas']):
            try:
                import requests
                response = requests.get(
                    self.base_url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=self.configuracoes['timeout_requisicao']
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and 'dados' in data:
                        return data['dados']
                    else:
                        return data
                elif response.status_code == 429:  # Rate limit
                    wait_time = (tentativa + 1) * 5
                    print(f"      ⏳ Rate limit. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"      ❌ Erro HTTP {response.status_code}: {response.text[:200]}")
                    if tentativa < self.configuracoes['max_tentativas'] - 1:
                        time.sleep(2 ** tentativa)  # Exponential backoff
                    continue
                    
            except Exception as e:
                print(f"      ❌ Erro na requisição (tentativa {tentativa + 1}): {e}")
                if tentativa < self.configuracoes['max_tentativas'] - 1:
                    time.sleep(2 ** tentativa)
                continue
        
        return None

    def buscar_emendas_ano_estendido(self, ano: int) -> List[Dict]:
        """
        Busca emendas de um ano com cobertura máxima
        """
        print(f"   🔍 Buscando emendas de {ano} (cobertura máxima)")
        
        todas_emendas = []
        pagina = 1
        sem_resultados_consecutivos = 0
        
        while pagina <= self.configuracoes['pagina_maxima']:
            params = {
                'ano': ano,
                'pagina': pagina,
                'itens': 100  # Máximo permitido pela API
            }
            
            emendas_pagina = self.fazer_requisicao_com_retry(params)
            
            if not emendas_pagina:
                sem_resultados_consecutivos += 1
                if sem_resultados_consecutivos >= 3:
                    print(f"      🛑 3 páginas sem resultados. Parando busca.")
                    break
                print(f"      ⚠️ Página {pagina} vazia. Tentando próxima...")
                pagina += 1
                continue
            
            if len(emendas_pagina) == 0:
                sem_resultados_consecutivos += 1
                if sem_resultados_consecutivos >= 3:
                    break
                pagina += 1
                continue
            
            # Reset contador se encontrou resultados
            sem_resultados_consecutivos = 0
            
            todas_emendas.extend(emendas_pagina)
            print(f"      📄 Página {pagina}: +{len(emendas_pagina)} emendas (total: {len(todas_emendas)})")
            
            # Verificar se atingiu o limite configurado
            if len(todas_emendas) >= self.configuracoes['limite_por_ano']:
                print(f"      🎯 Limite de {self.configuracoes['limite_por_ano']} emendas atingido")
                todas_emendas = todas_emendas[:self.configuracoes['limite_por_ano']]
                break
            
            # Se retornou menos que o solicitado, pode ser o fim
            if len(emendas_pagina) < 100:
                print(f"      🏁 Última página (menos de 100 resultados)")
                break
            
            pagina += 1
            
            # Rate limiting configurado
            time.sleep(self.configuracoes['delay_entre_requisicoes'])
        
        print(f"      ✅ Total encontrado: {len(todas_emendas)} emendas de {ano}")
        return todas_emendas

    def coletar_periodo_estendido(self) -> Dict[str, Any]:
        """
        Coleta emendas para o período estendido (06/2025 - hoje)
        """
        print(f"\n🚀 COLETA ESTENDIDA DE EMENDAS")
        print("=" * 70)
        print(f"📅 Período: Junho/2025 a Outubro/2025")
        print(f"🎯 Objetivo: Cobertura máxima com fallback inteligente")
        
        # Usar sessão do banco
        db_session = get_db_session()
        
        resultados = {
            'data_coleta': datetime.now().isoformat(),
            'periodo': '06/2025 a 10/2025',
            'configuracoes': self.configuracoes,
            'resultados_por_ano': {},
            'total_geral': {
                'emendas_encontradas': 0,
                'emendas_salvas': 0,
                'valor_total': 0.0,
                'erros': 0
            }
        }
        
        try:
            # Estratégia de coleta: tentar 2025 primeiro, depois fallback para anos disponíveis
            anos_para_coletar = [
                {'ano': 2025, 'prioridade': 'alta', 'descricao': 'Período principal (Jun-Out)'},
                {'ano': 2024, 'prioridade': 'media', 'descricao': 'Fallback ano anterior'},
                {'ano': 2023, 'prioridade': 'media', 'descricao': 'Fallback histórico'},
                {'ano': 2022, 'prioridade': 'baixa', 'descricao': 'Fallback antigo'},
                {'ano': 2021, 'prioridade': 'baixa', 'descricao': 'Fallback base'}
            ]
            
            for ano_info in anos_para_coletar:
                ano = ano_info['ano']
                print(f"\n{'='*60}")
                print(f"🎯 COLETANDO {ano_info['descricao'].upper()}")
                print(f"📅 Ano: {ano} | Prioridade: {ano_info['prioridade']}")
                print(f"{'='*60}")
                
                try:
                    # Buscar emendas do ano
                    emendas = self.buscar_emendas_ano_estendido(ano)
                    
                    if not emendas:
                        print(f"   ⚠️ Nenhuma emenda encontrada para {ano}")
                        resultados['resultados_por_ano'][ano] = {
                            'encontradas': 0,
                            'salvas': 0,
                            'valor_total': 0.0,
                            'erros': 0,
                            'status': 'vazio'
                        }
                        continue
                    
                    # Salvar emendas
                    print(f"\n💾 SALVANDO {len(emendas)} EMENDAS DE {ano}")
                    print("-" * 50)
                    
                    salvas = 0
                    valor_total = 0.0
                    erros = 0
                    
                    for i, emenda_data in enumerate(emendas, 1):
                        print(f"   📄 Processando {i}/{len(emendas)}: {emenda_data.get('codigoEmenda', 'N/A')}")
                        
                        try:
                            emenda = self.salvar_emenda_transparencia(emenda_data, db_session)
                            if emenda:
                                salvas += 1
                                valor_total += float(emenda.valor_emenda or 0)
                        except Exception as e:
                            print(f"      ❌ Erro ao salvar: {e}")
                            erros += 1
                            continue
                        
                        # Progresso a cada 50 emendas
                        if i % 50 == 0:
                            print(f"      📊 Progresso: {i}/{len(emendas)} ({i/len(emendas)*100:.1f}%)")
                        
                        # Rate limiting
                        time.sleep(0.2)
                    
                    # Gerar ranking para o ano
                    if salvas > 0:
                        try:
                            self.gerar_ranking_emendas_transparencia(ano, db_session)
                            print(f"   🏆 Ranking gerado para {ano}")
                        except Exception as e:
                            print(f"   ⚠️ Erro ao gerar ranking: {e}")
                    
                    # Consolidar resultados do ano
                    resultados['resultados_por_ano'][ano] = {
                        'encontradas': len(emendas),
                        'salvas': salvas,
                        'valor_total': valor_total,
                        'erros': erros,
                        'status': 'sucesso' if salvas > 0 else 'falha'
                    }
                    
                    # Atualizar total geral
                    resultados['total_geral']['emendas_encontradas'] += len(emendas)
                    resultados['total_geral']['emendas_salvas'] += salvas
                    resultados['total_geral']['valor_total'] += valor_total
                    resultados['total_geral']['erros'] += erros
                    
                    print(f"\n📋 RESUMO {ano}:")
                    print(f"   ✅ Encontradas: {len(emendas)}")
                    print(f"   💾 Salvas: {salvas}")
                    print(f"   💰 Valor: R$ {valor_total:,.2f}")
                    print(f"   ❌ Erros: {erros}")
                    
                    # Se encontrou muitas emendas em 2025, pode parar por aqui
                    if ano == 2025 and salvas > 100:
                        print(f"\n🎉 SUCESSO! Encontradas {salvas} emendas em 2025!")
                        print(f"   📊 Cobertura satisfatória para o hackathon")
                        break
                    
                except Exception as e:
                    print(f"❌ Erro geral na coleta de {ano}: {e}")
                    resultados['resultados_por_ano'][ano] = {
                        'encontradas': 0,
                        'salvas': 0,
                        'valor_total': 0.0,
                        'erros': 1,
                        'status': 'erro_geral',
                        'erro': str(e)
                    }
                    resultados['total_geral']['erros'] += 1
                    continue
            
            # Commit final de todas as alterações
            try:
                db_session.commit()
                print(f"\n✅ Todas as alterações salvas no banco!")
            except Exception as e:
                print(f"❌ Erro no commit final: {e}")
                db_session.rollback()
                resultados['total_geral']['erros'] += 1
            
        except Exception as e:
            print(f"❌ Erro geral na coleta: {e}")
            db_session.rollback()
            resultados['total_geral']['erros'] += 1
        
        finally:
            db_session.close()
        
        # Resumo final
        print(f"\n{'='*70}")
        print(f"🏁 RESUMO FINAL DA COLETA ESTENDIDA")
        print(f"{'='*70}")
        print(f"📅 Período: {resultados['periodo']}")
        print(f"📊 Total encontrado: {resultados['total_geral']['emendas_encontradas']} emendas")
        print(f"💾 Total salvo: {resultados['total_geral']['emendas_salvas']} emendas")
        print(f"💰 Valor total: R$ {resultados['total_geral']['valor_total']:,.2f}")
        print(f"❌ Total erros: {resultados['total_geral']['erros']}")
        
        # Status final
        if resultados['total_geral']['emendas_salvas'] > 0:
            print(f"\n🎉 COLETA CONCLUÍDA COM SUCESSO!")
            print(f"   ✅ Sistema pronto para o hackathon")
            print(f"   📊 Dados disponíveis para análise")
        else:
            print(f"\n⚠️ COLETA CONCLUÍDA COM ALERTAS!")
            print(f"   🔧 Verificar configurações e disponibilidade da API")
        
        return resultados

def main():
    """
    Função principal para execução standalone
    """
    print("🚀 COLETOR ESTENDIDO DE EMENDAS ORÇAMENTÁRIAS")
    print("=" * 70)
    print("📋 Configuração para cobertura máxima e período estendido")
    print("🎯 Período: Junho/2025 a Outubro/2025")
    print("🔧 Preparado para extensão pós-hackathon")
    print("=" * 70)
    
    try:
        # Inicializar coletor estendido
        coletor = ColetorEmendasEstendido()
        
        # Executar coleta estendida
        resultados = coletor.coletar_periodo_estendido()
        
        # Salvar resultados em JSON para auditoria
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"relatorio_coleta_estendida_{timestamp}.json"
        caminho_arquivo = Path(__file__).parent / nome_arquivo
        
        import json
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📁 Relatório salvo: {caminho_arquivo}")
        print(f"🎉 Coleta estendida concluída com sucesso!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE COLETA ESTENDIDA: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
