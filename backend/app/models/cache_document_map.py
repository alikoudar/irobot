# -*- coding: utf-8 -*-
"""
Modèle CacheDocumentMap - Mapping entre cache et documents.

Ce modèle établit la relation many-to-many entre les entrées de cache
et les documents utilisés pour générer les réponses. Cette relation
est essentielle pour l'invalidation intelligente du cache lors de
la modification ou suppression d'un document.

Sprint 6 - Phase 1 : Modèles Cache
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class CacheDocumentMap(Base):
    """
    Modèle de mapping cache ↔ documents.
    
    Permet de :
    - Lier chaque entrée de cache aux documents qui ont servi à générer la réponse
    - Invalider automatiquement le cache quand un document est modifié/supprimé
    - Analyser quels documents sont les plus fréquemment utilisés dans les réponses
    
    Attributes:
        id: Identifiant unique (UUID)
        cache_id: Référence vers l'entrée de cache (FK -> query_cache.id)
        document_id: Référence vers le document utilisé (FK -> documents.id)
        created_at: Date de création du mapping
    """
    
    __tablename__ = "cache_document_map"
    
    # Clé primaire
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identifiant unique du mapping"
    )
    
    # Clé étrangère vers query_cache
    cache_id = Column(
        UUID(as_uuid=True),
        ForeignKey("query_cache.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Référence vers l'entrée de cache"
    )
    
    # Clé étrangère vers documents
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Référence vers le document utilisé"
    )
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Date de création du mapping"
    )
    
    # Relations
    cache = relationship(
        "QueryCache",
        back_populates="document_maps"
    )
    
    document = relationship(
        "Document",
        backref="cache_maps"
    )
    
    # Index et contraintes
    __table_args__ = (
        # Index composite pour recherche rapide par cache_id
        Index("idx_cache_document_map_cache_id", "cache_id"),
        # Index composite pour recherche par document_id (invalidation)
        Index("idx_cache_document_map_document_id", "document_id"),
        # Contrainte d'unicité pour éviter les doublons
        Index(
            "idx_cache_document_map_unique",
            "cache_id",
            "document_id",
            unique=True
        ),
        {
            "comment": "Mapping entre entrées de cache et documents utilisés"
        }
    )
    
    def __repr__(self) -> str:
        """Représentation textuelle du mapping."""
        return f"<CacheDocumentMap(cache_id={self.cache_id}, document_id={self.document_id})>"
    
    def to_dict(self) -> dict:
        """Convertit le modèle en dictionnaire."""
        return {
            "id": str(self.id),
            "cache_id": str(self.cache_id),
            "document_id": str(self.document_id),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }