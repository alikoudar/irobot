"""UUID type compatible avec SQLite et PostgreSQL."""
from sqlalchemy import TypeDecorator, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid


class GUID(TypeDecorator):
    """
    Type UUID compatible avec SQLite et PostgreSQL.
    
    Utilise UUID natif pour PostgreSQL, String(36) pour SQLite.
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Choix du type selon la base de données."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        """Conversion Python -> DB."""
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value) if isinstance(value, str) else value
        else:
            # SQLite : convertir en string
            if isinstance(value, uuid.UUID):
                return str(value)
            elif isinstance(value, str):
                return value
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        """Conversion DB -> Python."""
        if value is None:
            return value
        elif isinstance(value, uuid.UUID):
            return value
        else:
            # Convertir string -> UUID
            return uuid.UUID(value) if value else None