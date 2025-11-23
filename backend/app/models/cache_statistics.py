# -*- coding: utf-8 -*-
"""
Modèle CacheStatistics pour les statistiques journalières du cache.

Sprint 6 - Phase 1 : Modèles Cache
CORRIGÉ : Gestion des None dans les méthodes increment
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Date, Integer, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class CacheStatistics(Base):
    """
    Statistiques journalières agrégées du système de cache.
    
    Une entrée par jour pour suivre les performances du cache :
    - Taux de hit/miss
    - Tokens et coûts économisés
    - Tendances d'utilisation
    """
    
    __tablename__ = "cache_statistics"
    
    # Identifiant unique
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identifiant unique des statistiques"
    )
    
    # Date des statistiques (une entrée par jour)
    date = Column(
        Date,
        nullable=False,
        unique=True,
        index=True,
        comment="Date des statistiques (YYYY-MM-DD)"
    )
    
    # Métriques de requêtes
    total_requests = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Nombre total de requêtes ce jour"
    )
    
    cache_hits = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Nombre de hits cache"
    )
    
    cache_misses = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Nombre de misses cache"
    )
    
    hit_rate = Column(
        Numeric(5, 2),
        nullable=False,
        default=0.0,
        comment="Taux de hit en pourcentage (0-100)"
    )
    
    # Économies réalisées
    tokens_saved = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Nombre total de tokens économisés"
    )
    
    cost_saved_usd = Column(
        Numeric(10, 4),
        nullable=False,
        default=0.0,
        comment="Économies totales en USD"
    )
    
    cost_saved_xaf = Column(
        Numeric(12, 2),
        nullable=False,
        default=0.0,
        comment="Économies totales en XAF"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Date de création de l'enregistrement"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Date de dernière mise à jour"
    )
    
    # Index pour optimisation
    __table_args__ = (
        # Index sur la date pour les requêtes temporelles
        Index("idx_cache_statistics_date", "date"),
        # Index pour les rapports par période
        Index("idx_cache_statistics_date_desc", date.desc()),
        {
            "comment": "Statistiques journalières agrégées du cache"
        }
    )
    
    def __init__(self, **kwargs):
        """Initialise les statistiques avec des valeurs par défaut sûres."""
        super().__init__(**kwargs)
        # S'assurer que toutes les valeurs numériques sont initialisées
        if self.total_requests is None:
            self.total_requests = 0
        if self.cache_hits is None:
            self.cache_hits = 0
        if self.cache_misses is None:
            self.cache_misses = 0
        if self.hit_rate is None:
            self.hit_rate = Decimal("0.0")
        if self.tokens_saved is None:
            self.tokens_saved = 0
        if self.cost_saved_usd is None:
            self.cost_saved_usd = Decimal("0.0")
        if self.cost_saved_xaf is None:
            self.cost_saved_xaf = Decimal("0.0")
    
    def __repr__(self) -> str:
        """Représentation textuelle des statistiques."""
        return (
            f"<CacheStatistics(date={self.date}, "
            f"requests={self.total_requests}, "
            f"hit_rate={self.hit_rate}%)>"
        )
    
    def calculate_hit_rate(self) -> float:
        """Calcule et met à jour le taux de hit."""
        total = self.total_requests or 0
        hits = self.cache_hits or 0
        
        if total > 0:
            self.hit_rate = round((hits / total) * 100, 2)
        else:
            self.hit_rate = 0.0
        return float(self.hit_rate)
    
    def increment_hit(
        self,
        tokens: int = 0,
        cost_usd: float = 0.0,
        cost_xaf: float = 0.0
    ) -> None:
        """
        Enregistre un hit cache et met à jour les métriques.
        
        Args:
            tokens: Nombre de tokens économisés
            cost_usd: Coût économisé en USD
            cost_xaf: Coût économisé en XAF
        """
        # Utiliser (valeur or 0) pour gérer les None
        self.total_requests = (self.total_requests or 0) + 1
        self.cache_hits = (self.cache_hits or 0) + 1
        self.tokens_saved = (self.tokens_saved or 0) + tokens
        self.cost_saved_usd = float(self.cost_saved_usd or 0) + cost_usd
        self.cost_saved_xaf = float(self.cost_saved_xaf or 0) + cost_xaf
        self.calculate_hit_rate()
        self.updated_at = datetime.utcnow()
    
    def increment_miss(self) -> None:
        """Enregistre un miss cache et met à jour les métriques."""
        # Utiliser (valeur or 0) pour gérer les None
        self.total_requests = (self.total_requests or 0) + 1
        self.cache_misses = (self.cache_misses or 0) + 1
        self.calculate_hit_rate()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convertit le modèle en dictionnaire."""
        return {
            "id": str(self.id),
            "date": self.date.isoformat() if self.date else None,
            "total_requests": self.total_requests or 0,
            "cache_hits": self.cache_hits or 0,
            "cache_misses": self.cache_misses or 0,
            "hit_rate": float(self.hit_rate) if self.hit_rate else 0.0,
            "tokens_saved": self.tokens_saved or 0,
            "cost_saved_usd": float(self.cost_saved_usd) if self.cost_saved_usd else 0.0,
            "cost_saved_xaf": float(self.cost_saved_xaf) if self.cost_saved_xaf else 0.0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_summary(cls, stats_list: list) -> dict:
        """
        Calcule un résumé à partir d'une liste de statistiques.
        
        Args:
            stats_list: Liste d'objets CacheStatistics
            
        Returns:
            Dictionnaire avec les totaux et moyennes
        """
        if not stats_list:
            return {
                "period_days": 0,
                "total_requests": 0,
                "total_hits": 0,
                "total_misses": 0,
                "avg_hit_rate": 0.0,
                "total_tokens_saved": 0,
                "total_cost_saved_usd": 0.0,
                "total_cost_saved_xaf": 0.0
            }
        
        total_requests = sum((s.total_requests or 0) for s in stats_list)
        total_hits = sum((s.cache_hits or 0) for s in stats_list)
        total_misses = sum((s.cache_misses or 0) for s in stats_list)
        avg_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "period_days": len(stats_list),
            "total_requests": total_requests,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "avg_hit_rate": round(avg_hit_rate, 2),
            "total_tokens_saved": sum((s.tokens_saved or 0) for s in stats_list),
            "total_cost_saved_usd": round(
                sum(float(s.cost_saved_usd or 0) for s in stats_list), 4
            ),
            "total_cost_saved_xaf": round(
                sum(float(s.cost_saved_xaf or 0) for s in stats_list), 2
            )
        }