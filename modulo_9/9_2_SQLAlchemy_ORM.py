from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Log(Base):
    __tablename__ = 'log'
    id = Column(Integer, primary_key=True)
    time = Column(DateTime)

# uso
engine = create_engine('sqlite:///log.db')
Session = sessionmaker(bind=engine)
session = Session()

new_log = Log(message="Backup completo")
session.add(new_log)
session.commit()


