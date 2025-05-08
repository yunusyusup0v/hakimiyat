import os
import uuid
from typing import Optional
from fastapi import APIRouter,  HTTPException, status, UploadFile, File, Form, Query, Depends
from sqlalchemy import desc
from backend.database import Session, connect
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from backend.model import Tg_user, TgUserAppeal, User, User_Status, TgAppealStatus, TgAppealHistory, Appeal, Appeal_Status, AppealAnswer
from backend.schema import Tg_User_Schema, TgUserCreateRequest, TgAppealSortSchema
from datetime import datetime
from .appeal import strip_html_tags
from .auth import verify

tg_user_router = APIRouter(prefix='/tg-user', tags=['TG_USER'])
tg_appeal_router = APIRouter(prefix='/tg-appeal', tags=['TG APPEAL'])



@tg_user_router.post("/test")
async def create_tg_user(request: TgUserCreateRequest, session : Session = Depends(connect)):
    try:
        tg_user_id = request.tg_user_id
        user = session.query(Tg_user).filter(Tg_user.tg_user_id == tg_user_id).first()

        if user:
            return HTTPException(status_code=status.HTTP_200_OK, detail=f"message : Tg user id - {tg_user_id} already exsist")
        else:
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"message: TG_USER ID - {tg_user_id} NOT FOUND")


    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="что то пошло не так")


@tg_user_router.post("", status_code=status.HTTP_201_CREATED)
async def create_tg_user(user: Tg_User_Schema, session : Session = Depends(connect)):
    try:
        check_user = session.query(Tg_user).filter(Tg_user.tg_user_id == user.tg_user_id).first()
        if check_user:
            raise HTTPException(status_code=400, detail=f"User with this {user.tg_user_id} already exists")

        new_user = Tg_user(
            tg_user_id=user.tg_user_id,
            phone=user.phone,
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user

    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="что то пошло не так")

token = os.getenv("BOT_TOKEN")




from telegram import Bot
TELEGRAM_BOT_TOKEN = f"{token}"
bot = Bot(token=TELEGRAM_BOT_TOKEN)





@tg_user_router.get('/appeal', status_code=status.HTTP_200_OK)
async def appeal(
    id: int = Query(...),
    appeal_id: Optional[int] = Query(None),
    session : Session = Depends(connect)
):
    try:
        tg_appeal = session.query(TgUserAppeal).filter(TgUserAppeal.tg_user_id == id).all()

        tg_appeal_ids = [item.id for item in tg_appeal]
        appeal = session.query(Appeal).filter(Appeal.tg_appeal_id.in_(tg_appeal_ids)).all()


        if appeal_id is not None:
            check_appeal = session.query(Appeal).filter(Appeal.id == appeal_id).first()

            if not check_appeal or check_appeal.tg_appeal_id not in tg_appeal_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")


            if check_appeal.appeal_status == Appeal_Status.DONE:
                last_answer = (
                    session.query(AppealAnswer)
                    .filter(AppealAnswer.appeal_id == check_appeal.id)
                    .order_by(AppealAnswer.created_at.desc())
                    .first()
                )

                if last_answer and last_answer.report_appeal_user:
                    pdf_path = last_answer.report_appeal_user

                    try:
                        with open(pdf_path, 'rb') as pdf_file:
                            await bot.send_document(
                                chat_id=id,
                                document=pdf_file,
                                caption=f"N - {appeal_id} sanli murajaatin'zig'a ha'kimiyat ta'repinen juwap"
                            )
                    except FileNotFoundError:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Файл не найден для указанной апелляции"
                        )


        appeal_ids = [a.tg_appeal_id for a in appeal]
        tg_appeal_all = [ta for ta in tg_appeal if ta.id not in appeal_ids]

        tg_appeal_list = [
            {
                "id": tg.id,
                "document": tg.document,
                "text": strip_html_tags(tg.text),
                "status": tg.tg_appeal_status,
                "fio": tg.fio,
                "phone": f"+998{tg.phone}" if len(tg.phone) == 9 else tg.phone,
                "birthday": tg.birthday,
                "mahalla": tg.mahalla,
                "created_at": tg.created_at.strftime("%d.%m.%Y %H:%M"),
            }
            for tg in tg_appeal_all
        ]

        appeal_list = [
            {
                "phone": f"+998{a.phone}" if len(a.phone) == 9 else a.phone,
                "status": a.appeal_status,
                "created_at": a.created_at.strftime("%d.%m.%Y %H:%M"),
                "fio": a.fio,
                "document": f"{a.doc_series} {a.doc_num}",
                "id": a.id,
                "birthday": (
                    a.birthday.strftime("%d.%m.%Y") if isinstance(a.birthday, datetime)
                    else datetime.fromisoformat(a.birthday).strftime("%d.%m.%Y")
                    if isinstance(a.birthday, str) else None
                ),
                "text": a.text,
            }
            for a in appeal
        ]

        results = tg_appeal_list + appeal_list

        return results
    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="что то пошло не так")


#### -------------------------------------------------------------------------------------------------------------------





#### -------------------------------------------------------------------------------------------------------------------
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



MAX_FILE_SIZE = 10 * 1024 * 1024





@tg_appeal_router.post('', status_code=status.HTTP_201_CREATED)
async def create_tg_user_appeal(
    tg_user_id: int = Form(...),
    fio: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    document: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    mahalla: Optional[str] = Form(None),
    birthday: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    session : Session = Depends(connect),
    file: Optional[UploadFile] = File(None)
):
    if file:
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Размер файла превышает допустимый лимит {MAX_FILE_SIZE // (1024 * 1024)} MB"
            )

    try:
        user = session.query(Tg_user).filter(Tg_user.tg_user_id == tg_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"TG_USER ID {tg_user_id} not found")

        file_location = None

        if file:
            upload_dir = "appeal-files"
            os.makedirs(upload_dir, exist_ok=True)


            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_location = os.path.join(upload_dir, unique_filename)

            with open(file_location, "wb") as buffer:
                buffer.write(await file.read())

        new_appeal = TgUserAppeal(
            tg_user_id=tg_user_id,
            fio=fio,
            phone=phone,
            document=document,
            address=address,
            mahalla=mahalla,
            birthday=birthday,
            file_path=file_location,
            text=text
        )
        session.add(new_appeal)
        session.commit()
        session.refresh(new_appeal)


        tg_history = TgAppealHistory(
            tg_appeal_id=new_appeal.id,
            text="TELEGRAMNAN JAN'A MURAJAAT KELIP TU'STI"
        )
        session.add(tg_history)
        session.commit()

        return jsonable_encoder(new_appeal)

    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)






@tg_appeal_router.get('', status_code=status.HTTP_200_OK)
async def get_tg_appeals(
    status: Optional[TgAppealStatus] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = Query(10, ge=1),
    page: int = Query(1, ge=1),
    session : Session = Depends(connect),
    user : User = Depends(verify)
):
    try:

        if user:
            if user.role not in [User_Status.CEO, User_Status.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN)

        from_datetime = datetime.strptime(from_date, '%d.%m.%y') if from_date else None
        to_datetime = datetime.strptime(to_date, '%d.%m.%y') if to_date else None


        query = session.query(TgUserAppeal)


        if status:
            query = query.filter(TgUserAppeal.tg_appeal_status == status)
        if from_datetime:
            query = query.filter(TgUserAppeal.created_at >= from_datetime)
        if to_datetime:
            query = query.filter(TgUserAppeal.created_at <= to_datetime)


        total_tg_appeals = query.count()


        query = query.order_by(desc(TgUserAppeal.id))


        skip = (page - 1) * limit
        appeals = query.offset(skip).limit(limit).all()

        list1 = [
            {
                "id": appeal.id,
                "fio": appeal.fio,
                "phone": appeal.phone,
                "text": appeal.text,
                "tg_appeal_status": appeal.tg_appeal_status,
                "created_at": appeal.created_at.strftime("%d.%m.%Y %H:%M")
            }
            for appeal in appeals
        ]

        data = {
            "data": list1,
            "pagination": {
                "total": total_tg_appeals,
                "limit": limit,
                "page": page
            }
        }

        return jsonable_encoder(data)

    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=400)






@tg_appeal_router.get('/{id}', status_code=status.HTTP_200_OK)
async def get_appeal(id: int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        tg = session.query(TgUserAppeal).filter(TgUserAppeal.id == id).first()
        appeal = session.query(Appeal).filter(Appeal.tg_appeal_id == tg.id).first()

        data =  {

                "address" : tg.address,
                "birthday" : tg.birthday,
                "created_at" : tg.created_at,
                "document" : tg.document,
                "file_path" : tg.file_path,
                "fio" : tg.fio,
                "id" : tg.id,
                "mahalla" : tg.mahalla,
                "phone" : tg.phone,
                "text" : tg.text,
                "tg_appeal_status" : tg.tg_appeal_status,
                "tg_user_id" : tg.tg_user_id,
                "appeal_id" : appeal.id if appeal else ""

        }



        return jsonable_encoder(data)

    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)







@tg_appeal_router.patch('/sort/{id}', status_code=status.HTTP_200_OK)
async def sort_appeal(id: int, appeal_sort: TgAppealSortSchema, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        tg_appeal_sort = session.query(TgUserAppeal).filter(TgUserAppeal.id == id).first()
        if not tg_appeal_sort:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TgUserAppeal not found")


        tg_appeal_sort.tg_appeal_status = appeal_sort.tg_appeal_status


        tg_history = TgAppealHistory(
            tg_appeal_id=tg_appeal_sort.id,
            tg_appeal_status=appeal_sort.tg_appeal_status,
            user_id=user.id,
            text=appeal_sort.text
        )
        session.add(tg_history)
        session.commit()

    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)










@tg_appeal_router.get('/history/{id}', status_code=status.HTTP_200_OK)
async def tg_appeal_history(id: int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if not user or user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        history = session.query(TgAppealHistory).filter(TgAppealHistory.tg_appeal_id == id).all()
        if not history:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


        data = [
            {
                "id": entry.id,
                "tg_appeal_id": entry.tg_appeal_id,
                "user": session.query(User).filter(User.id == entry.user_id).first().fio if entry.user_id else None,
                "text": entry.text,
                "status": entry.tg_appeal_status,
                "date": entry.created_at.strftime("%d.%m.%Y %H:%M"),
            }
            for entry in history
        ]

        return jsonable_encoder(data)

    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
