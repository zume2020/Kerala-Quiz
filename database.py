import config
import datetime

from sqlalchemy import create_engine, BigInteger, Boolean, Column, String, Integer, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session


def start() -> scoped_session:
    engine = create_engine(config.DB_URI)
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


try:
    BASE = declarative_base()
    SESSION = start()

except AttributeError as e:
    print("DB_URI is not configured!")
    raise e


class Ranking(BASE):
    __tablename__ = "ranking"
    _id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    user_name = Column(String)
    score = Column(Integer)
    chat = Column(BigInteger)
    time = Column(Time)

    def __init__(
            self,
            user_id,
            user_name,
            score,
            chat,
            time):
        self.user_id = user_id
        self.user_name = user_name
        self.score = score
        self.chat = chat
        self.time = time


class Total(BASE):
    __tablename__ = "total"
    user_id = Column(BigInteger, primary_key=True)
    user_name = Column(String)
    score = Column(Integer)
    chat = Column(BigInteger)

    def __init__(
            self,
            user_id,
            user_name,
            score,
            chat):
        self.user_id = user_id
        self.user_name = user_name
        self.score = score
        self.chat = chat


Total.__table__.create(checkfirst=True)
Ranking.__table__.create(checkfirst=True)


def get_week_table():
    try:
        return SESSION.query(Ranking).filter_by(Ranking.time <= datetime.datetime.now() - datetime.timedelta(days=7))
    except:
        raise Exception
    finally:
        SESSION.close()


def get_total_table():
    try:
        return SESSION.query(Total).get()
    except:
        raise Exception
    finally:
        SESSION.close()


def inc_or_new_user(user_id, user_name, score, chat, time):
    try:
        user = SESSION.query(Total).get(user_id, Total.chat == chat)
        user.score += score
    except:
        user = Total(user_id, user_name, score, chat)
        SESSION.add(user)
    finally:
        entry = Ranking(user_id, user_name, score, chat, time)
        SESSION.add(entry)
        SESSION.commit()
        SESSION.close()
        return entry, user
