"""
Modèle SystemConfig amélioré.

Ajouts par rapport à la version existante:
- category: pour regrouper les configs (pricing, models, chunking, etc.)
- is_sensitive: pour masquer les valeurs sensibles dans l'API
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.session import Base


class SystemConfig(Base):
    """
    Configuration système dynamique.
    
    Stocke toutes les configurations modifiables par l'admin:
    - Tarifs Mistral
    - Paramètres de chunking
    - Paramètres d'embedding
    - Paramètres de recherche
    - Limites d'upload
    - Taux de change
    """
    
    __tablename__ = "system_configs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Configuration
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    
    # Catégorie pour regroupement (pricing, models, chunking, embedding, search, upload, cache, exchange_rate)
    category = Column(String(50), nullable=False, default="other", index=True)
    
    # Indique si la valeur est sensible (ne pas afficher dans les logs/API publique)
    is_sensitive = Column(Boolean, default=False, nullable=False)
    
    # Qui a fait la dernière modification
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<SystemConfig {self.key}>"
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convertit la config en dictionnaire.
        
        Args:
            include_sensitive: Inclure les valeurs sensibles
            
        Returns:
            Dict avec les données de la config
        """
        result = {
            "id": str(self.id),
            "key": self.key,
            "description": self.description,
            "category": self.category,
            "is_sensitive": self.is_sensitive,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if self.is_sensitive and not include_sensitive:
            result["value"] = "***HIDDEN***"
        else:
            result["value"] = self.value
        
        return result