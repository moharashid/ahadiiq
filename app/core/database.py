from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# create a connection to the database
engine = create_engine(settings.db_url)

# creates a factory of session objects
SessionLocal  = sessionmaker(bind=engine)

def get_db():
    
    db = SessionLocal()
    try:
        # hand the session to the route (caller), then pause here
        yield db
    finally:
        
        # end the session, releasing its connection back to the pool
        db.close()
