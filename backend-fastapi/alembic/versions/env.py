from app.database.base import Base, TimestampMixin
import app.models 

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)