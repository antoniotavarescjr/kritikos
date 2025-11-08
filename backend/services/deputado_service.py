"""
Services de negócio para Deputados
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from src.models.database import get_db
from src.models.politico_models import Deputado
from src.models.analise_models import ScoreDeputado
from schemas.deputado import DeputadoResponse, DeputadoList

logger = logging.getLogger(__name__)

class DeputadoService:
    """Service para operações relacionadas a deputados"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def listar_deputados(
        self,
        page: int = 1,
        per_page: int = 20,
        partido: Optional[str] = None,
        uf: Optional[str] = None,
        nome: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Listar deputados com paginação e filtros
        """
        try:
            # Query base
            query = self.db.query(Deputado)
            
            # Aplicar filtros
            if partido:
                # TODO: Implementar filtro por partido quando tiver a relação
                pass
            
            if uf:
                # TODO: Implementar filtro por UF quando tiver a relação
                pass
            
            if nome:
                query = query.filter(Deputado.nome.ilike(f"%{nome}%"))
            
            # Contar total
            total = query.count()
            
            # Aplicar paginação
            offset = (page - 1) * per_page
            deputados = query.offset(offset).limit(per_page).all()
            
            # Converter para response
            deputados_data = []
            for dep in deputados:
                # Buscar análise IDP se existir
                analise = self.db.query(ScoreDeputado).filter(
                    ScoreDeputado.deputado_id == dep.id
                ).first()
                
                dep_data = {
                    "id": dep.id,
                    "nome": dep.nome,
                    "sigla_partido": "",  # TODO: Obter do mandato atual
                    "sigla_uf": "",  # TODO: Obter do mandato atual
                    "url_foto": dep.foto_url or "",
                    "email": dep.email or "",
                    "idp": float(analise.score_final) if analise else 0.0,
                    "idp_ranking": 0,  # TODO: Implementar ranking
                    "total_gastos": 0.0,  # TODO: Implementar cálculo real
                    "total_emendas": 0,  # TODO: Implementar contagem real
                    "total_proposicoes": 0,  # TODO: Implementar contagem real
                    "status": "ativo",  # TODO: Implementar lógica real
                    "ultima_atualizacao": "2025-01-07T15:00:00Z"
                }
                deputados_data.append(dep_data)
            
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "data": deputados_data,
                "meta": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages
                },
                "links": {
                    "self": f"/api/deputados?page={page}&per_page={per_page}",
                    "next": f"/api/deputados?page={page + 1}&per_page={per_page}" if page < total_pages else None,
                    "prev": f"/api/deputados?page={page - 1}&per_page={per_page}" if page > 1 else None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao listar deputados: {e}")
            raise e
    
    def obter_deputado(self, deputado_id: int) -> Optional[Dict[str, Any]]:
        """
        Obter dados completos de um deputado específico
        """
        try:
            deputado = self.db.query(Deputado).filter(Deputado.id == deputado_id).first()
            
            if not deputado:
                return None
            
            # Buscar análise IDP
            analise = self.db.query(ScoreDeputado).filter(
                ScoreDeputado.deputado_id == deputado_id
            ).first()
            
            # TODO: Implementar cálculos reais de gastos, emendas, proposições
            return {
                "id": deputado.id,
                "nome": deputado.nome,
                "sigla_partido": "",  # TODO: Obter do mandato atual
                "sigla_uf": "",  # TODO: Obter do mandato atual
                "url_foto": deputado.foto_url or "",
                "email": deputado.email or "",
                "telefone": deputado.telefone or "",
                "gabinete": "",  # TODO: Obter do mandato atual
                "idp": float(analise.score_final) if analise else 0.0,
                "idp_ranking": 0,  # TODO: Implementar ranking
                "idp_desempenho_legislativo": float(analise.desempenho_legislativo) if analise else 0.0,
                "idp_relevancia_social": float(analise.relevancia_social) if analise else 0.0,
                "idp_responsabilidade_fiscal": float(analise.responsabilidade_fiscal) if analise else 0.0,
                "total_gastos": 0.0,  # TODO: Implementar
                "total_emendas": 0,  # TODO: Implementar
                "total_proposicoes": 0,  # TODO: Implementar
                "proposicoes_relevantes": 0,  # TODO: Implementar
                "media_score_par": 0.0,  # TODO: Implementar
                "status": "ativo",  # TODO: Implementar
                "ultima_atualizacao": "2025-01-07T15:00:00Z"
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter deputado {deputado_id}: {e}")
            raise e
    
    def obter_gastos_deputado(
        self,
        deputado_id: int,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Obter gastos parlamentares de um deputado
        """
        try:
            # TODO: Implementar consulta real à tabela de gastos
            # Por enquanto, retorna dados mock
            gastos_mock = [
                {
                    "id": 1,
                    "deputado_id": deputado_id,
                    "ano": ano or 2025,
                    "mes": mes or 1,
                    "tipo_despesa": "Passagens aéreas",
                    "valor": 2500.00,
                    "descricao": "Passagem Rio - Brasília",
                    "data_documento": "2025-01-05",
                    "fornecedor": "TAM Airlines"
                }
            ]
            
            return {
                "data": gastos_mock,
                "meta": {
                    "total": len(gastos_mock),
                    "page": page,
                    "per_page": per_page,
                    "total_pages": 1
                },
                "links": {
                    "self": f"/api/deputados/{deputado_id}/gastos?page={page}",
                    "next": None,
                    "prev": None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter gastos do deputado {deputado_id}: {e}")
            raise e
    
    def obter_emendas_deputado(
        self,
        deputado_id: int,
        ano: Optional[int] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Obter emendas parlamentares de um deputado
        """
        try:
            # TODO: Implementar consulta real à tabela de emendas
            # Por enquanto, retorna dados mock
            emendas_mock = [
                {
                    "id": 1,
                    "deputado_id": deputado_id,
                    "ano": ano or 2025,
                    "numero": "20250001",
                    "tipo": "Individual",
                    "valor_emenda": 100000.00,
                    "valor_empenhado": 85000.00,
                    "valor_liquidado": 70000.00,
                    "valor_pago": 50000.00,
                    "localidade": "Rio Branco - AC",
                    "funcao": "Saúde",
                    "subfuncao": "Atenção Básica",
                    "descricao": "Equipamentos para hospitais",
                    "status": "Em execução"
                }
            ]
            
            return {
                "data": emendas_mock,
                "meta": {
                    "total": len(emendas_mock),
                    "page": page,
                    "per_page": per_page,
                    "total_pages": 1
                },
                "links": {
                    "self": f"/api/deputados/{deputado_id}/emendas?page={page}",
                    "next": None,
                    "prev": None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter emendas do deputado {deputado_id}: {e}")
            raise e
    
    def obter_proposicoes_deputado(
        self,
        deputado_id: int,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Obter proposições de autoria de um deputado
        """
        try:
            # TODO: Implementar consulta real à tabela de proposições
            # Por enquanto, retorna dados mock
            proposicoes_mock = [
                {
                    "id": 1,
                    "deputado_id": deputado_id,
                    "tipo": "PL",
                    "numero": "1234/2025",
                    "ano": 2025,
                    "ementa": "Dispõe sobre políticas de educação ambiental",
                    "tem_analise": True,
                    "resumo": "Proposta que implementa educação ambiental nas escolas",
                    "score_par": 75.5,
                    "relevancia": "alta",
                    "data_apresentacao": "2025-01-05",
                    "situacao": "Em tramitação"
                }
            ]
            
            return {
                "data": proposicoes_mock,
                "meta": {
                    "total": len(proposicoes_mock),
                    "page": page,
                    "per_page": per_page,
                    "total_pages": 1
                },
                "links": {
                    "self": f"/api/deputados/{deputado_id}/proposicoes?page={page}",
                    "next": None,
                    "prev": None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter proposições do deputado {deputado_id}: {e}")
            raise e


def get_deputado_service() -> DeputadoService:
    """Factory function para obter instância do serviço"""
    db = next(get_db())
    try:
        return DeputadoService(db)
    finally:
        db.close()
