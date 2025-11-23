# -*- coding: utf-8 -*-
"""
Modèle QueryCache - Cache des questions et réponses du chatbot.

Ce modèle stocke les questions posées par les utilisateurs avec leurs
réponses générées, permettant un cache à 2 niveaux :
- Niveau 1 : Correspondance exacte (via query_hash)
- Niveau 2 : Similarité sémantique (via query_embedding)

Sprint 6 - Phase 1 : Modèles Cache
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Any

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    Numeric,
    Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class QueryCache(Base):
    """
    Modèle pour le cache des questions/réponses.
    
    Permet de stocker les requêtes utilisateur et leurs réponses pour éviter
    de recalculer les mêmes réponses via le pipeline RAG complet.
    
    Attributes:
        id: Identifiant unique (UUID)
        query_text: Texte original de la question
        query_hash: Hash SHA-256 de la question (pour correspondance exacte)
        query_embedding: Vecteur embedding de la question (pour similarité)
        response: Réponse générée par le LLM
        sources: Liste des sources utilisées (documents, pages, chunks)
        token_count: Nombre de tokens de la réponse
        cost_saved_usd: Coût économisé en USD à chaque hit
        cost_saved_xaf: Coût économisé en XAF à chaque hit
        hit_count: Nombre de fois que ce cache a été utilisé
        last_hit_at: Date du dernier hit cache
        expires_at: Date d'expiration (TTL 7 jours par défaut)
        created_at: Date de création
        updated_at: Date de dernière modification
    """
    
    __tablename__ = "query_cache"
    
    # Clé primaire
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identifiant unique du cache"
    )
    
    # Données de la question
    query_text = Column(
        Text,
        nullable=False,
        comment="Texte original de la question posée"
    )
    
    query_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Hash SHA-256 de la question pour correspondance exacte"
    )
    
    query_embedding = Column(
        JSONB,
        nullable=True,
        comment="Vecteur embedding de la question pour recherche par similarité"
    )
    
    # Données de la réponse
    response = Column(
        Text,
        nullable=False,
        comment="Réponse générée par le LLM"
    )
    
    sources = Column(
        JSONB,
        nullable=True,
        default=list,
        comment="Liste des sources utilisées (document_id, title, page, chunk_index)"
    )
    
    # Métriques de coût
    token_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Nombre de tokens de la réponse"
    )
    
    cost_saved_usd = Column(
        Numeric(10, 6),
        nullable=False,
        default=0.0,
        comment="Coût économisé en USD par hit cache"
    )
    
    cost_saved_xaf = Column(
        Numeric(12, 2),
        nullable=False,
        default=0.0,
        comment="Coût économisé en XAF par hit cache"
    )
    
    # Statistiques d'utilisation
    hit_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Nombre de fois que ce cache a été utilisé"
    )
    
    last_hit_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date et heure du dernier hit cache"
    )
    
    # TTL (Time To Live)
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(days=7),
        index=True,
        comment="Date d'expiration du cache (TTL 7 jours)"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Date de création"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Date de dernière modification"
    )
    
    # Relations
    document_maps = relationship(
        "CacheDocumentMap",
        back_populates="cache",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Index composites pour optimisation
    __table_args__ = (
        # Index pour la recherche par hash (cache L1)
        Index("idx_query_cache_hash", "query_hash"),
        # Index pour le nettoyage des caches expirés
        Index("idx_query_cache_expires_at", "expires_at"),
        # Index pour les statistiques
        Index("idx_query_cache_created_at", "created_at"),
        {
            "comment": "Cache des questions/réponses pour le chatbot RAG"
        }
    )
    
    def __repr__(self) -> str:
        """Représentation textuelle du cache."""
        query_preview = self.query_text[:50] + "..." if len(self.query_text) > 50 else self.query_text
        return f"<QueryCache(id={self.id}, query='{query_preview}', hits={self.hit_count})>"
    
    def is_expired(self) -> bool:
        """Vérifie si le cache est expiré."""
        return datetime.utcnow() > self.expires_at if self.expires_at else True
    
    def increment_hit(self) -> None:
        """Incrémente le compteur de hits et met à jour last_hit_at."""
        self.hit_count += 1
        self.last_hit_at = datetime.utcnow()
    
    def reset_ttl(self, days: int = 7) -> None:
        """Réinitialise le TTL du cache."""
        self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.updated_at = datetime.utcnow()
    
    def get_document_ids(self) -> List[str]:
        """Retourne la liste des IDs de documents utilisés."""
        return [dm.document_id for dm in self.document_maps]
    
    def to_dict(self) -> dict:
        """Convertit le modèle en dictionnaire."""
        return {
            "id": str(self.id),
            "query_text": self.query_text,
            "query_hash": self.query_hash,
            "response": self.response,
            "sources": self.sources,
            "token_count": self.token_count,
            "cost_saved_usd": float(self.cost_saved_usd) if self.cost_saved_usd else 0.0,
            "cost_saved_xaf": float(self.cost_saved_xaf) if self.cost_saved_xaf else 0.0,
            "hit_count": self.hit_count,
            "last_hit_at": self.last_hit_at.isoformat() if self.last_hit_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_expired": self.is_expired()
        }