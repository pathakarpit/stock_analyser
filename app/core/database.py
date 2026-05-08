import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv()

def get_db_engine():
    """Creates and returns the SQLAlchemy database engine."""
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    # Construct the connection URL
    database_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Create the engine
    engine = create_engine(database_url)
    print(engine)
    return engine

# Create a singleton instance to be imported by other modules
engine = get_db_engine()