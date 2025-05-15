from backend.db import engine, Base
from backend.models import tbLPLookup, tbLPFund, tbPCAP, tbLedger  # Import models to register them with Base

# Create all tables in the database
if __name__ == "__main__":
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")