from backend.database import Base, ENGINE
from backend.model import User, User_Status,  Appeal_Status, Appeal, AppealAnswer, Mahalla, Mekeme, Gender, TgUserAppeal, Tg_user, AppealHakimiyat, AppealHistory, Sector, TgAppealHistory


Base.metadata.create_all(bind=ENGINE)