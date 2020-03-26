import config
import datetime

from sqlalchemy import create_engine, BigInteger, Boolean, Column, String, Integer, DateTime
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
    time = Column(DateTime)

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
    _id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
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


def get_week_table(chat_id):
    try:
        return SESSION.query(Ranking).filter(Ranking.time >= datetime.datetime.now() - datetime.timedelta(days=7), Ranking.chat == chat_id).all()
    except:
        return []
    finally:
        SESSION.close()


def get_total_table():
    try:
        return SESSION.query(Total).all()
    except:
        return []
    finally:
        SESSION.close()


def inc_or_new_user(user_id, user_name, score, chat, time):
    user = SESSION.query(Total).filter(
        Total.user_id == user_id, Total.chat == chat).first()
    if user:
        user.user_name = user_name
        user.score += score
    else:
        user = Total(user_id, user_name, score, chat)
        SESSION.add(user)
    entry = Ranking(user_id, user_name, score, chat, time)
    SESSION.add(entry)
    SESSION.commit()
    SESSION.close()
    return entry, user
