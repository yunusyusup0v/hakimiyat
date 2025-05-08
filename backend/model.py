from backend.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLAEnum, DateTime, func, BIGINT, Boolean
from sqlalchemy.orm import relationship
from enum import Enum


class Appeal_Status(Enum):

    WAITING = "waiting"                  # MURAJAT TIYISLI  MEKEMEGE JIBERILDI MEKEME QABIL ETPEDI
    DECLINE = "decline"                  # MEKEME MURAJATTI (OTKAZ) QILGANI (MURAJAT BIZLERGE TIYISLI EMES)
    IN_PROGRESS = "in_progress"          # APPEAL IN PROGRESS
    CONFIRM = "confirm"                  # MEKEME MURAJATTI BOLDI (HAKIMIYATQA JIBERGENI)
    REJECTED = "rejected"                # HAKIMIYAT MURAJATTI QAYTARIP JIBERDI
    SUCCESS_DONE = "success_done"        # HAKIMIYAT MURAJATTI (УСПЕШНО) UNAMLI JAWDI
    TEXT_DONE = 'text_done'              # TUSINIK XAT PENEN JAWILDI
    CONFIRM_50 = "confirm_50"            # MEKEME MURAJATTI 50 % ISTEDI
    SUCCESS_50 = "success_50"            # HAKIMIYAT MURAJATTIN 50 % QABILLADI
    TIME_REQUEST = "time_request"        # MEKEME QOSIMSHA WAQIT SORAW
    TIME_EXTENDED = "time_extended"      # HAKIMIYAT WAQIT QOSIP BERID
    TIME_DENIED = "time_denied"          # HAKIMIYAT WAQQTI UZAYTIRIP BERMEDI
    ARCHIVE = "archive"                  # APPEAL ARXIV





class Gender(Enum):
    MALE = "male"
    FEMALE = "female"


class User_Status(Enum):
    USER = "user"
    ADMIN = "admin"
    CEO = "ceo"



class Sector(Base):
    __tablename__ = 'sector'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    mahalla = relationship('Mahalla', back_populates='sector')


class Mahalla(Base):
    __tablename__ = 'mahalla'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True)
    sector_id = Column(Integer, ForeignKey('sector.id'))

    sector = relationship('Sector', back_populates='mahalla')
    appeal = relationship('Appeal', back_populates='mahalla')


class Mekeme(Base):
    __tablename__ = 'mekeme'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    address = Column(String, nullable=False)

    user = relationship('User', back_populates='mekeme')
    appeal = relationship('Appeal', back_populates='mekeme')


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fio = Column(String, nullable=False)
    login = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    role = Column(SQLAEnum(User_Status), default=User_Status.USER)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now())

    mekeme_id = Column(Integer, ForeignKey('mekeme.id'))

    mekeme = relationship('Mekeme', back_populates='user')




class AppealHakimiyat(Base):
    __tablename__ = 'hakimiyat_appeal'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String)
    created_at = Column(DateTime, default=func.now())

    appeal_id = Column(Integer, ForeignKey('appeal.id'), nullable=False)

    appeal = relationship('Appeal', back_populates='hakimiyat_appeal')


class Appeal(Base):
    __tablename__ = 'appeal'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fio = Column(String, nullable=False)
    gender = Column(SQLAEnum(Gender), default=Gender.MALE)
    phone = Column(String, unique=True)
    doc_series = Column(String)
    doc_num = Column(String)
    address = Column(String)
    birthday = Column(DateTime)
    file_path = Column(String, default='appeal-files')
    text = Column(String)
    appeal_status = Column(SQLAEnum(Appeal_Status), default=Appeal_Status.WAITING)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime
                        )
    view = Column(Boolean, default=False)

    deadline = Column(DateTime)

    tg_appeal_id = Column(Integer, ForeignKey('tg_appeal.id'), nullable=True)
    mahalla_id = Column(Integer, ForeignKey('mahalla.id'))
    mekeme_id = Column(Integer, ForeignKey('mekeme.id'))

    views = relationship("AppealView", back_populates="appeal")
    tg_appeal = relationship("TgUserAppeal", back_populates="appeal", uselist=False)
    mekeme = relationship('Mekeme', back_populates='appeal')
    mahalla = relationship('Mahalla', back_populates='appeal')
    answer = relationship('AppealAnswer', back_populates='appeal', uselist=False)
    history = relationship('AppealHistory', back_populates='appeal', cascade="all, delete-orphan")
    hakimiyat_appeal = relationship('AppealHakimiyat', back_populates='appeal')


class AppealView(Base):
    __tablename__ = "appeal_view"

    id = Column(Integer, primary_key=True,  index=True, autoincrement=True)
    appeal_id = Column(Integer, ForeignKey("appeal.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    viewed_at = Column(DateTime, default=func.now())

    appeal = relationship("Appeal", back_populates="views")
    user = relationship("User")


class AppealHistory(Base):
    __tablename__ = 'appeal_history'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appeal_id = Column(Integer, ForeignKey('appeal.id'), nullable=False)
    text = Column(String)
    status = Column(String)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    time_file = Column(String)
    report_appeal_user = Column(String)
    report_government = Column(String)
    report_photo = Column(String)
    created_at = Column(DateTime, default=func.now())

    appeal = relationship("Appeal", back_populates="history")
    user = relationship("User")



class AppealAnswer(Base):
    __tablename__ = 'mekeme_appeal'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String)
    time_file = Column(String)
    report_appeal_user = Column(String)
    report_government = Column(String)
    report_photo = Column(String)

    created_at = Column(DateTime, default=func.now())

    appeal_id = Column(Integer, ForeignKey('appeal.id'), nullable=False)

    appeal = relationship('Appeal', back_populates='answer')






class Tg_user(Base):
    __tablename__ = "tg_user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tg_user_id = Column(BIGINT, nullable=False, unique=True)
    phone = Column(String)
    created_at = Column(DateTime, default=func.now())

    tg_appeal = relationship("TgUserAppeal", back_populates="tg_user", cascade="all, delete-orphan")




class TgAppealStatus(Enum):

    NEW = 'new'
    IN_PROGRESS = 'in_progress'
    CANCELED = 'canceled'
    DONE = 'done'
    ARCHIVE = "archive"
    REJECTED = "rejected"




class TgUserAppeal(Base):
    __tablename__ = "tg_appeal"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tg_user_id = Column(BIGINT, ForeignKey('tg_user.tg_user_id'), nullable=False)
    fio = Column(String, nullable=False)
    phone = Column(String)
    document = Column(String)
    birthday = Column(String)
    address = Column(String)
    mahalla = Column(String)
    text = Column(String)
    file_path = Column(String)


    tg_appeal_status = Column(SQLAEnum(TgAppealStatus), default=TgAppealStatus.NEW)

    created_at = Column(DateTime, default=func.now())

    appeal = relationship("Appeal", back_populates="tg_appeal")
    tg_user = relationship("Tg_user", back_populates="tg_appeal")





class TgAppealHistory(Base):
    __tablename__ = 'tg_appeal_history'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tg_appeal_status = Column(SQLAEnum(TgAppealStatus), default=TgAppealStatus.NEW)
    tg_appeal_id = Column(BIGINT, nullable=True)
    user_id = Column(Integer)
    text = Column(String)

    created_at = Column(DateTime, default=func.now())


