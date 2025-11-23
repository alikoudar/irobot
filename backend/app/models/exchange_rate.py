"""Modèle ExchangeRate pour le suivi des taux de change."""
from sqlalchemy import Column, String, DateTime, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.session import Base


class ExchangeRate(Base):
    """
    Modèle pour stocker l'historique des taux de change.
    
    Utilisé pour convertir les coûts USD en XAF.
    Le taux est mis à jour quotidiennement via une tâche périodique.
    """
    
    __tablename__ = "exchange_rates"
    
    # Clé primaire
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Devises
    currency_from = Column(String(3), nullable=False, default="USD")
    currency_to = Column(String(3), nullable=False, default="XAF")
    
    # Taux de conversion (ex: 1 USD = 655.957 XAF)
    rate = Column(Numeric(20, 6), nullable=False)
    
    # Date de récupération depuis l'API externe
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Timestamp de création en base
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Index composite pour recherche efficace du dernier taux
    __table_args__ = (
        Index('ix_exchange_rates_currencies_fetched', 'currency_from', 'currency_to', 'fetched_at'),
    )
    
    def __repr__(self):
        return f"<ExchangeRate {self.currency_from}/{self.currency_to}: {self.rate} @ {self.fetched_at}>"
    
    @property
    def rate_float(self) -> float:
        """Retourne le taux en float pour les calculs."""
        return float(self.rate)