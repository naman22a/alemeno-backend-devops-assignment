from sqlmodel import create_engine

postgresql_url = 'postgresql://postgres:postgres@localhost:5432/db'
engine = create_engine(postgresql_url)
