import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List
from backend.model import Appeal_Status, User_Status, Gender, TgAppealStatus
from datetime import date, datetime


load_dotenv()



key = os.getenv('SECRET_KEY')
al = os.getenv('ALGHORITM')

class Settings(BaseModel):
    authjwt_secret_key: str = f"{key}"
    authjwt_algorithm: str = f"{al}"


class UserResponse(BaseModel):
    id : int
    fio : str
    login : str
    phone : str
    role : User_Status
    mekeme_id : int


class UserRegisterSchema(BaseModel):
    fio : str
    login : str
    password: str
    phone: str
    role : User_Status
    mekeme_id : Optional[int]

    class Config:
        orm_mode = True



class UserLoginSchema(BaseModel):
    login : str
    password: str



class UserUpdateSchema(BaseModel):
    fio : Optional[str]
    login: Optional[str]
    password : Optional[str]
    phone: Optional[str]
    role: User_Status = User_Status.USER
    mekeme_id : Optional[int]
    is_active : Optional[bool]




# ------- MEKEME -----
#
class MekemeCreateSchema(BaseModel):

    name : str
    address : str
    user_ids : Optional[List[int]]


class MekemeUpdateSchema(BaseModel):
    name: Optional[str]
    address: Optional[str]
    user_ids : Optional[List[int]]


class MekemeOption(BaseModel):
    value : str
    label : str


# -----  Mahalla --------


class CreateMahallaSchema(BaseModel):
    sector_id : Optional[int]
    name : Optional[str]

class UpdateMahallaSchema(BaseModel):
    sector_id : Optional[int]
    name : Optional[str]


class MahallaOption(BaseModel):
    value : str
    label : str



class SectorSchema(BaseModel):
    name : Optional[str]



class Tg_User_Schema(BaseModel):
    tg_user_id : int
    phone : Optional[str]


class TgUserAppealSchema(BaseModel):
    tg_user_id : int
    fio : str
    phone : Optional[str]
    document : Optional[str]
    address : Optional[str]
    mahalla : Optional[str]
    birthday : date
    text : Optional[str]




class TgUserCreateRequest(BaseModel):
    tg_user_id: int

class TgAppealSortSchema(BaseModel):
    text : Optional[str]
    tg_appeal_status : Optional[TgAppealStatus]



class AppealCreateSchema(BaseModel):
    fio : str
    gender : Optional[Gender]
    phone : str
    doc_series : str
    doc_num : str
    address: Optional[str]
    birthday : Optional[datetime]
    text : Optional[str]
    mahalla_id : Optional[int]
    mekeme_id : Optional[int]
    file_path : Optional[str]
    tg_appeal_id : Optional[int]
    deadline : Optional[datetime]

    class Config:
        orm_mode = True




class AppealUpdateSchema(BaseModel):
    fio : Optional[str]
    gender : Optional[Gender]
    phone : Optional[str]
    doc_series : Optional[str]
    doc_num : Optional[str]
    address : Optional[str]
    birthday : Optional[datetime]
    text : Optional[str]
    mahalla_id : Optional[int]
    mekeme_id : Optional[int]
    file_path : Optional[str]



class AppealAnswerCreateSchema(BaseModel):
    appeal_id : int
    text : Optional[str]
    time_file : Optional[str]
    appeal_status : Optional[Appeal_Status]
    report_appeal_user : Optional[str]
    report_government : Optional[str]
    report_photo : Optional[str]

    class Config:
        orm_mode = True


class AppealHakimiyatSchema(BaseModel):
    appeal_id : int
    appeal_status: Optional[Appeal_Status]
    text : Optional[str]
    time: Optional[datetime]


    class Config:
        orm_mode = True



class AppealViewSchema(BaseModel):
    appeal_id : Optional[int]
    user_id : Optional[int]
    viewed_at : Optional[int]