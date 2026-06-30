from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base


class AppSetting(Base):
    """
    Key-value store for encrypted application settings.
    Values are Fernet-encrypted with the app's SECRET_KEY before storage.
    """
    __tablename__ = "app_settings"

    key        = Column(String(100), primary_key=True)
    value      = Column(Text, nullable=False)          # encrypted ciphertext
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
