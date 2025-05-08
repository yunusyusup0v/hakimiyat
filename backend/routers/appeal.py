import os, re, aiofiles, uuid, datetime, logging
import pandas as pd
from sqlalchemy import desc
from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile, Query, Response
from starlette.responses import StreamingResponse
from backend.database import Session, connect
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from backend.model import Tg_user, Appeal_Status, Appeal, AppealHistory,  AppealAnswer, User, User_Status, AppealHakimiyat, TgUserAppeal, TgAppealStatus, AppealView, TgAppealHistory
from typing import Optional, Union
from backend.schema import AppealCreateSchema, AppealAnswerCreateSchema, AppealHakimiyatSchema, AppealUpdateSchema
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from openpyxl.styles import Alignment

from backend.routers.auth import verify




appeal_router = APIRouter(prefix='/appeal', tags=['APPEAL'])

UPLOAD_DIR = "appeal-files/"


font_path = os.path.join(os.path.dirname(__file__), '..', 'DejaVuSans.ttf')
font_path = os.path.abspath(font_path)


pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))


def strip_html_tags(text):
    if text:
        clean = re.sub(r'<[^>]*>', '', text)
        return clean
    return text


def get_text_width(c, text, font_size=12):
    c.setFont("DejaVuSans", font_size)
    return c.stringWidth(text)


def wrap_text(c, text, max_width):
    c.setFont("DejaVuSans", 12)
    lines = []
    words = text.split()
    current_line = words[0]
    for word in words[1:]:
        if get_text_width(c, current_line + " " + word) <= max_width:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines


@appeal_router.get('/pdf/{id}', status_code=200)
async def download_pdf(id: int, session: Session = Depends(connect),  user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        appeal = session.query(Appeal).filter(Appeal.id == id).first()
        if not appeal:
            raise HTTPException(status_code=404, detail="Appeal not found")

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        page_width, page_height = letter

        c.setFont("DejaVuSans", 12)
        c.drawCentredString(page_width / 2, 750, "QON'IRAT HA'KIMLIGI")
        c.drawCentredString(page_width / 2, 735, "«QON'IRAT MURAJAATI» platformasi arqali kelip tusken murajaat")

        y_position = 700
        headers = [
            ("ID", appeal.id),
            ("FAA", appeal.fio),
            ("JINS", appeal.gender.value if appeal.gender else "N/A"),
            ("TELEFON NOMER", appeal.phone),
            ("PASSPORT SERIYA", appeal.doc_series),
            ("PASSPORT NOMER", appeal.doc_num),
            ("ADDRESS", appeal.address),
            ("TUWILG'AN KU'N", appeal.birthday.strftime("%Y.%m.%d") if appeal.birthday else "N/A"),
            ("JUWAPKER SHO'LKEM", appeal.mekeme.name if appeal.mekeme else "N/A"),
            ("KELIP TU'SKEN WAQTI", appeal.created_at.strftime("%d.%m.%Y %H:%M")),
            ("MA'HA'LLE", appeal.mahalla.name if appeal.mahalla else "N/A"),
            ("SEKTOR", appeal.mahalla.sector.name if appeal.mahalla and appeal.mahalla.sector else "N/A")
        ]

        col_widths = [30, 150, 400]
        line_height = 20

        for i, (header, value) in enumerate(headers, start=1):
            wrapped_text = wrap_text(c, str(value), col_widths[2]) if isinstance(value, str) else [str(value)]
            for line in wrapped_text:

                c.rect(50, y_position, col_widths[0], line_height)
                c.rect(80, y_position, col_widths[1], line_height)
                c.rect(230, y_position, col_widths[2], line_height)
                c.rect(50, y_position, sum(col_widths), line_height)
                c.drawString(55, y_position + 5, str(i))
                c.drawString(85, y_position + 5, str(header))
                c.drawString(235, y_position + 5, line)
                y_position -= line_height

        c.setFont("DejaVuSans", 14)
        y_position -= 20
        c.drawCentredString(page_width / 2, y_position, "MURAJAAT XAT")
        y_position -= 20

        appeal_text = strip_html_tags(appeal.text)
        wrapped_text = wrap_text(c, appeal_text, 500)

        text_y_position = y_position - 30
        for line in wrapped_text:
            text_width = get_text_width(c, line)
            c.drawString((page_width - text_width) / 2, text_y_position, line)
            text_y_position -= line_height

        c.showPage()
        c.save()

        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=appeal_{id}.pdf"
        })

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=400)





def parse_date(date_str):
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail=f"Неверный формат даты: {date_str}")




@appeal_router.get('/excel', status_code=200)
async def download_appeals_excel(
        mekeme_id: Optional[int] = Query(None),
        from_date: Optional[str] = Query(None),
        to_date: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        session: Session = Depends(connect),
        user : User = Depends(verify)):
    try:



        appeals_query = session.query(Appeal)
        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            appeals_query = appeals_query.filter(Appeal.mekeme_id == user.mekeme_id)

        if mekeme_id:
            appeals_query = appeals_query.filter(Appeal.mekeme_id == mekeme_id)
        if from_date:
            from_date = parse_date(from_date).replace(hour=0, minute=0, second=0)
            appeals_query = appeals_query.filter(Appeal.created_at >= from_date)
        if to_date:
            to_date = parse_date(to_date).replace(hour=23, minute=59, second=59)
            appeals_query = appeals_query.filter(Appeal.created_at <= to_date)
        if status:
            if status == 'done':
                appeals_query = appeals_query.filter(
                    Appeal.appeal_status.in_([Appeal_Status.SUCCESS_DONE, Appeal_Status.TEXT_DONE]))
            else:
                appeals_query = appeals_query.filter(Appeal.appeal_status == status.upper())

        appeals_query = appeals_query.order_by(Appeal.id.desc())
        appeals = appeals_query.all()

        if not appeals:
            raise HTTPException(status_code=404, detail="Данные не найдены для выгрузки.")

        data = [
            {
                "ID": appeal.id,
                "ФИО": appeal.fio,
                "Пол": 'erkek' if appeal.gender.value == 'male' else "ayel",
                "Телефон номер": appeal.phone,
                "Серия документа": appeal.doc_series,
                "Документ №": appeal.doc_num,
                "Махалля" : appeal.mahalla.name,
                "Адрес": appeal.address,
                "Дата рождения": appeal.birthday.strftime('%d.%m.%Y'),
                "Создано": appeal.created_at.strftime('%H:%M %d.%m.%Y'),
                "Статус" : appeal.appeal_status.value,
                "сектор" : appeal.mahalla.sector.name,
                "Организация (куда отправлено обращение гражданина)" : appeal.mekeme.name
            }
            for appeal in appeals
        ]

        df = pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Appeals', index=False)
            worksheet = writer.sheets['Appeals']

            for column_cells in worksheet.columns:
                max_length = max(len(str(cell.value)) for cell in column_cells)
                column_letter = column_cells[0].column_letter
                worksheet.column_dimensions[column_letter].width = max_length + 5
                for cell in column_cells:
                    if cell.column_letter == 'I':
                        cell.alignment = Alignment(wrap_text=True, vertical='top', horizontal='left')
                    else:
                        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')

            for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
                text_cell = row[8]
                if isinstance(text_cell.value, str) and len(text_cell.value) > 50:
                    line_count = text_cell.value.count('\n') + 1
                    worksheet.row_dimensions[text_cell.row].height = max(20, line_count * 20)

        output.seek(0)

        headers = {
            'Content-Disposition': 'attachment; filename="appeals.xlsx"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        return Response(content=output.getvalue(), headers=headers,
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


    except Exception as e:
        raise HTTPException(status_code=400)












MAX_FILE_SIZE = 20 * 1024 * 1024






@appeal_router.post('/file', status_code=status.HTTP_200_OK)
async def upload_file(user : User = Depends(verify), file: Optional[UploadFile] = File(...)):
    try:

        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Превышен лимит размера файла: {MAX_FILE_SIZE // (1024 * 1024)} МБ."
            )

        file_format = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_format}"
        file_location = os.path.join(UPLOAD_DIR, unique_filename)

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        async with aiofiles.open(file_location, "wb") as f:
            await f.write(await file.read())

        return {"file_path": file_location}

    except HTTPException as http:
        raise http

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)






logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@appeal_router.get('', status_code=200)
async def get_appeals(
        limit: int = Query(10, ge=1),
        page: int = Query(1, ge=1),
        mekeme_id: Optional[int] = Query(None),
        from_date: Optional[str] = Query(None),
        to_date: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        appeal : Union[int, str] = Query(None),
        session : Session = Depends(connect),
        user : User = Depends(verify)
):
    try:



        if user.role in [User_Status.CEO, User_Status.ADMIN]:
            appeals_query = session.query(Appeal)
        else:
            appeals_query = session.query(Appeal).filter(Appeal.mekeme_id == user.mekeme_id)

        if isinstance(appeal, int):
            appeals_query = appeals_query.filter(Appeal.id == appeal)

        elif isinstance(appeal, str):
            appeals_query = appeals_query.filter(Appeal.fio.ilike(f"%{appeal}%"))

        if mekeme_id:
            appeals_query = appeals_query.filter(Appeal.mekeme_id == mekeme_id)

        if from_date:
            from_date = datetime.strptime(from_date, "%d.%m.%y").replace(hour=0, minute=0, second=0)
            appeals_query = appeals_query.filter(Appeal.created_at >= from_date)

        if to_date:
            to_date = datetime.strptime(to_date, "%d.%m.%y").replace(hour=23, minute=59, second=59)
            appeals_query = appeals_query.filter(Appeal.created_at <= to_date)

        if status:

            if status == 'done':
                appeals_query = appeals_query.filter(
                    Appeal.appeal_status.in_([Appeal_Status.SUCCESS_DONE, Appeal_Status.TEXT_DONE])
                )
            else:
                try:

                    status_enum = Appeal_Status[status.upper()]
                    appeals_query = appeals_query.filter(Appeal.appeal_status == status_enum)
                except KeyError:
                    raise HTTPException(status_code=400, detail="Invalid appeal status")

        appeals_query = appeals_query.order_by(Appeal.id.desc())

        total = appeals_query.count()
        skip = (page - 1) * limit
        appeals = appeals_query.offset(skip).limit(limit).all()

        dataa = [
            {
                "id": appeal.id,
                "address": f"{appeal.mahalla.name} - {appeal.address}",
                "deadline" : appeal.deadline,
                "text": appeal.text,
                "phone": appeal.phone,
                "appeal_status": appeal.appeal_status,
                "created_at": appeal.created_at.strftime("%d:%m:%Y %H:%M"),
                "tg_appeal_id": appeal.tg_appeal_id if appeal.tg_appeal_id else None,
                "fio": appeal.fio
            }
        for appeal in appeals
        ]

        pagination = {
            "page": page,
            "limit": limit,
            "total": total
        }
        data = {
            "data": dataa,
            "pagination": pagination
        }

        return jsonable_encoder(data)

    except Exception as e:
        raise HTTPException(status_code=400)





@appeal_router.get('/{id}', status_code=200)
async def get_appeal(id: int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:
        if not verify:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        appeal = session.query(Appeal).filter(Appeal.id == id).first()
        if not appeal:
            raise HTTPException(status_code=404, detail="Обращение не найдено")

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            if user.mekeme_id != appeal.mekeme_id:
                raise HTTPException(status_code=403)

        check_view = session.query(AppealView).filter_by(appeal_id=appeal.id, user_id=user.id).first()
        if not check_view:
            new_view = AppealView(appeal_id=appeal.id, user_id=user.id)
            session.add(new_view)

            if not appeal.view:
                appeal.view = True

            session.commit()

        viewers = [
            {   "user_id" : view.user.id,
                "user": view.user.fio,
                "time": view.viewed_at.strftime("%d-%m-%Y %H:%M")
            }
            for view in appeal.views
        ]


        data = {
            "id": appeal.id,
            "fio": appeal.fio,
            "gender": appeal.gender.value,
            "phone": appeal.phone,
            "doc_series": appeal.doc_series,
            "doc_num": appeal.doc_num,
            "address": appeal.address,
            "birthday": appeal.birthday,
            "file_path": appeal.file_path,
            "text": appeal.text,
            "created_at": appeal.created_at,
            "updated_at": appeal.updated_at,
            "mahalla": appeal.mahalla.name if appeal.mahalla else None,
            "mahalla_id": appeal.mahalla_id,
            "mekeme": appeal.mekeme.name if appeal.mekeme else None,
            "mekeme_id": appeal.mekeme_id,
            "appeal_status": appeal.appeal_status.value,
            "deadline": appeal.deadline,
            "view": appeal.view,
            "tg_appeal_id" : appeal.tg_appeal_id if appeal.tg_appeal_id else None
        }

        response = {
                "data" : data,
                "view" : viewers
            }

        return jsonable_encoder(response)

    except HTTPException as http_err:
        raise http_err

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)







@appeal_router.post("", status_code=status.HTTP_201_CREATED)
async def create_appeal(appeal: AppealCreateSchema, session: Session = Depends(connect), user : User = Depends(verify)):
    try:


        if not user or (user.role not in [User_Status.CEO, User_Status.ADMIN]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


        tg_appeal = session.query(TgUserAppeal).filter(TgUserAppeal.id == appeal.tg_appeal_id).first()
        if tg_appeal and tg_appeal.tg_appeal_status == TgAppealStatus.CANCELED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This appeal was canceled.")


        if appeal.tg_appeal_id is not None:
            check_appeal = session.query(Appeal).filter(Appeal.tg_appeal_id == appeal.tg_appeal_id).first()
            if check_appeal:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Appeal with this tg_appeal_id already exists.")


        new_appeal = Appeal(
            fio=appeal.fio,
            gender=appeal.gender,
            phone=appeal.phone,
            doc_series=appeal.doc_series,
            doc_num=appeal.doc_num,
            birthday=appeal.birthday,
            address=appeal.address,
            text=appeal.text,
            mahalla_id=appeal.mahalla_id,
            mekeme_id=appeal.mekeme_id,
            file_path=appeal.file_path,
            tg_appeal_id=appeal.tg_appeal_id
        )

        session.add(new_appeal)
        session.flush()


        appeal_history = AppealHistory(
            appeal_id=new_appeal.id,
            user_id=user.id,
            status=Appeal_Status.WAITING.value,
            text='MURAJAAT JARATILDI'
        )

        session.add(appeal_history)


        if appeal.tg_appeal_id:
            tg_history = TgAppealHistory(
                tg_appeal_id=new_appeal.tg_appeal_id,
                text=f"Murajat {new_appeal.mekeme.name} g'a jiberildi",
                tg_appeal_status=TgAppealStatus.IN_PROGRESS,
                user_id=user.id
            )
            tg_appeal.tg_appeal_status = TgAppealStatus.IN_PROGRESS
            session.add(tg_history)

        if appeal.deadline:
            new_appeal.deadline = appeal.deadline

        new_appeal.deadline = new_appeal.created_at + timedelta(days=15)


        session.commit()
        session.refresh(new_appeal)



        return {
            "id": new_appeal.id,
            "fio": new_appeal.fio,
            "gender": new_appeal.gender,
            "phone": new_appeal.phone,
            "doc_series": new_appeal.doc_series,
            "doc_num": new_appeal.doc_num,
            "birthday": new_appeal.birthday,
            "address": new_appeal.address,
            "text": new_appeal.text,
            "mahalla_id": new_appeal.mahalla_id,
            "mekeme_id": new_appeal.mekeme_id,
            "file_path": new_appeal.file_path,
            "tg_appeal_id": new_appeal.tg_appeal_id
        }

    except HTTPException as http:
        raise http

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error: {e}")








@appeal_router.post('/mekeme-appeal', status_code=status.HTTP_200_OK)
async def mekeme_appeal_answer(
    appeal: AppealAnswerCreateSchema,
    session : Session = Depends(connect),
    user : User = Depends(verify)
):
    try:


        check_appeal = session.query(Appeal).filter(Appeal.id == appeal.appeal_id).first()



        if check_appeal.mekeme_id != user.mekeme_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


        if check_appeal.appeal_status == Appeal_Status.SUCCESS_DONE or check_appeal.appeal_status == Appeal_Status.TEXT_DONE:
            if appeal.appeal_status is not None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"вы не сможете ничего изменить... это уже закрытое обращение")

        if check_appeal.appeal_status == Appeal_Status.CONFIRM_50:

            if appeal.appeal_status not in  [Appeal_Status.CONFIRM, ]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if appeal.appeal_status == Appeal_Status.CONFIRM:
                check_appeal.appeal_status = Appeal_Status.CONFIRM



        if check_appeal.appeal_status == Appeal_Status.TIME_REQUEST:

            if appeal.appeal_status not in [Appeal_Status.CONFIRM_50, Appeal_Status.CONFIRM]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if appeal.appeal_status == Appeal_Status.CONFIRM_50:
                check_appeal.appeal_status = Appeal_Status.CONFIRM_50

            if appeal.appeal_status == Appeal_Status.CONFIRM:
                check_appeal.appeal_status = Appeal_Status.CONFIRM



        if check_appeal.appeal_status == Appeal_Status.REJECTED:
            if appeal.appeal_status not in [Appeal_Status.CONFIRM, Appeal_Status.CONFIRM_50, Appeal_Status.IN_PROGRESS, Appeal_Status.TIME_REQUEST]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if appeal.appeal_status == Appeal_Status.CONFIRM:
                check_appeal.appeal_status = Appeal_Status.CONFIRM

            if appeal.appeal_status == Appeal_Status.CONFIRM_50:
                check_appeal.appeal_status = Appeal_Status.CONFIRM_50

            if appeal.appeal_status == Appeal_Status.TIME_REQUEST:
                check_appeal.appeal_status = Appeal_Status.TIME_REQUEST








        if check_appeal.appeal_status == Appeal_Status.IN_PROGRESS:

            if appeal.appeal_status not in [Appeal_Status.TIME_REQUEST, Appeal_Status.CONFIRM_50,
                                            Appeal_Status.CONFIRM]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if appeal.appeal_status == Appeal_Status.TIME_REQUEST:
                check_appeal.appeal_status = Appeal_Status.TIME_REQUEST

            if appeal.appeal_status == Appeal_Status.CONFIRM_50:
                check_appeal.appeal_status = Appeal_Status.CONFIRM_50

            if appeal.appeal_status == Appeal_Status.CONFIRM:
                check_appeal.appeal_status = Appeal_Status.CONFIRM





        if check_appeal.appeal_status == Appeal_Status.WAITING:
            if appeal.appeal_status not in [Appeal_Status.IN_PROGRESS, Appeal_Status.DECLINE]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if appeal.appeal_status == Appeal_Status.IN_PROGRESS:
                check_appeal.appeal_status = Appeal_Status.IN_PROGRESS

            if appeal.appeal_status == Appeal_Status.DECLINE:
                check_appeal.appeal_status = Appeal_Status.DECLINE




        new_app_answer = AppealAnswer(
            appeal_id=appeal.appeal_id,
            text=appeal.text,
            time_file=appeal.time_file,
            report_appeal_user=appeal.report_appeal_user,
            report_government=appeal.report_government,
            report_photo=appeal.report_photo
        )

        session.add(new_app_answer)


        appeal_history = AppealHistory(
            appeal_id=appeal.appeal_id,
            user_id=user.id,
            status=appeal.appeal_status.value,
            text=appeal.text,
            time_file=appeal.time_file,
            report_appeal_user=appeal.report_appeal_user,
            report_government=appeal.report_government,
            report_photo=appeal.report_photo
        )
        session.add(appeal_history)
        session.commit()

        return new_app_answer

    except HTTPException as http:
        raise http
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)



from telegram import Bot
token = os.getenv("BOT_TOKEN")
bot = Bot(token=token)



@appeal_router.post('/hakimiyat-appeal', status_code=status.HTTP_200_OK)
async def hakimiyat_appeal(appeal: AppealHakimiyatSchema, session : Session = Depends(connect), user : User = Depends(verify)):
    try:
        if user.role not in [User_Status.ADMIN, User_Status.CEO]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        check_appeal = session.query(Appeal).filter(Appeal.id == appeal.appeal_id).first()
        tg_appeal = session.query(TgUserAppeal).filter(TgUserAppeal.id == check_appeal.tg_appeal_id).first()

        if check_appeal.appeal_status == Appeal_Status.SUCCESS_DONE or check_appeal.appeal_status == Appeal_Status.TEXT_DONE:
            if appeal.appeal_status is not None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"вы не сможете ничего изменить... это уже закрытое обращение")


        if check_appeal.appeal_status == Appeal_Status.WAITING or check_appeal.appeal_status == Appeal_Status.DECLINE:
            if appeal.appeal_status == Appeal_Status.ARCHIVE:
                check_appeal.appeal_status = Appeal_Status.ARCHIVE

            if tg_appeal and check_appeal.appeal_status == Appeal_Status.ARCHIVE:
                tg_appeal.tg_appeal_status = TgAppealStatus.ARCHIVE
                tg_history = TgAppealHistory(
                    tg_appeal_id=check_appeal.tg_appeal_id,
                    text="Murajat arxivke tusti",
                    tg_appeal_status=TgAppealStatus.ARCHIVE,
                    user_id=user.id
                )
                session.add(tg_history)
                session.commit()



        if check_appeal.appeal_status == Appeal_Status.TIME_REQUEST:
            if appeal.appeal_status not in [Appeal_Status.TIME_EXTENDED, Appeal_Status.TIME_DENIED]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if appeal.appeal_status == Appeal_Status.TIME_EXTENDED:
                if not appeal.time:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"так как вы выбрали продлить время нужно выбрать время")
                check_appeal.deadline = appeal.time
                check_appeal.appeal_status = Appeal_Status.IN_PROGRESS

            if appeal.appeal_status == Appeal_Status.TIME_DENIED:
                check_appeal.appeal_status = Appeal_Status.IN_PROGRESS


        if check_appeal.appeal_status in [Appeal_Status.CONFIRM, Appeal_Status.CONFIRM_50]:
            if appeal.appeal_status not in [Appeal_Status.SUCCESS_50, Appeal_Status.SUCCESS_DONE, Appeal_Status.TEXT_DONE, Appeal_Status.REJECTED]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if appeal.appeal_status == Appeal_Status.SUCCESS_50:
                check_appeal.appeal_status = Appeal_Status.IN_PROGRESS

            if appeal.appeal_status == Appeal_Status.REJECTED:
                check_appeal.appeal_status = Appeal_Status.REJECTED
                if tg_appeal:
                    tg_appeal.tg_appeal_status = TgAppealStatus.REJECTED

            if appeal.appeal_status == Appeal_Status.SUCCESS_DONE:
                check_appeal.appeal_status = Appeal_Status.SUCCESS_DONE

            if appeal.appeal_status == Appeal_Status.TEXT_DONE:
                check_appeal.appeal_status = Appeal_Status.TEXT_DONE

            if tg_appeal and check_appeal.appeal_status == Appeal_Status.TEXT_DONE or check_appeal.appeal_status == Appeal_Status.SUCCESS_DONE:
                if tg_appeal:
                    tg_appeal.tg_appeal_status = TgAppealStatus.DONE

                    tg_user = session.query(Tg_user).filter(Tg_user.tg_user_id == tg_appeal.tg_user_id).first()


                last_answer = (
                    session.query(AppealAnswer)
                    .filter(AppealAnswer.appeal_id == check_appeal.id)
                    .order_by(AppealAnswer.created_at.desc())
                    .first()
                )

                if last_answer is not None and last_answer.report_appeal_user:
                    pdf_path = f"{last_answer.report_appeal_user}"

                    try:

                        with open(pdf_path, 'rb') as pdf_file:
                            await bot.send_document(chat_id=tg_user.tg_user_id, document=pdf_file, caption=f"{check_appeal.id} sanli murajaatin'zig'a ha'kimiyat ta'repinen juwap")
                    except Exception as e:
                        pass

                else:
                    pass

                tg_history = TgAppealHistory(
                    tg_appeal_id=check_appeal.tg_appeal_id,
                    text="Murajat juwmaqlandi",
                    tg_appeal_status=TgAppealStatus.DONE,
                    user_id=user.id
                )
                session.add(tg_history)
                session.commit()


            if appeal.appeal_status == Appeal_Status.REJECTED:
                check_appeal.appeal_status = Appeal_Status.REJECTED

            if tg_appeal and check_appeal.appeal_status == Appeal_Status.REJECTED:
                tg_appeal.tg_appeal_status = TgAppealStatus.REJECTED

                tg_history = TgAppealHistory(
                    tg_appeal_id=check_appeal.tg_appeal_id,
                    text=f"Murajat ha'kimiyat tarepinen {check_appeal.mekeme.name} mekemege qaytarip jiberildi",
                    tg_appeal_status=TgAppealStatus.REJECTED,
                    user_id=user.id
                )
                session.add(tg_history)
                session.commit()



        if check_appeal.appeal_status == Appeal_Status.DECLINE:
            if appeal.appeal_status == Appeal_Status.IN_PROGRESS:
                check_appeal.appeal_status = Appeal_Status.IN_PROGRESS


        new_hakim_answer = AppealHakimiyat(
            appeal_id=appeal.appeal_id,
            text=appeal.text
        )
        session.add(new_hakim_answer)
        session.commit()


        appeal_history = AppealHistory(
            appeal_id=appeal.appeal_id,
            user_id=user.id,
            status=appeal.appeal_status.value,
            text=new_hakim_answer.text
        )
        session.add(appeal_history)
        session.commit()

        return new_hakim_answer

    except HTTPException as http:
        raise http
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)






@appeal_router.get('/history/{id}', status_code=200)
async def history(id: int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        appeals = []

        if user.role in [User_Status.CEO, User_Status.ADMIN]:
            appeals = session.query(AppealHistory).filter(AppealHistory.appeal_id == id).order_by(
                desc(AppealHistory.id)).all()
        elif user.mekeme_id:
            appeals = (
                session.query(AppealHistory)
                .join(Appeal, Appeal.id == AppealHistory.appeal_id)
                .filter(
                    AppealHistory.appeal_id == id,
                    Appeal.mekeme_id == user.mekeme_id
                )
                .order_by(desc(AppealHistory.id))
                .all()
            )


        data = []
        for appeal in appeals:
            user = session.query(User).filter(User.id == appeal.user_id).first()



            data.append({
                "id": appeal.id,
                "text": appeal.text,
                "status": appeal.status,
                "user": f"{user.mekeme.name} - {user.fio}" if user.mekeme_id else user.fio,
                "user_id": user.id,
                "time_file" : appeal.time_file,
                "report_appeal_user": appeal.report_appeal_user if appeal.report_appeal_user else None,
                "report_government": appeal.report_government if appeal.report_government else None,
                "report_photo": appeal.report_photo if appeal.report_photo else None,
                "created": appeal.created_at.strftime("%d.%m.%Y %H:%M"),
                "message_owned": (user.mekeme_id == user.mekeme_id if user.role in [User_Status.CEO, User_Status.ADMIN] else user.id == user.id)

            })

        return jsonable_encoder(data)

    except HTTPException as http:
        raise http
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)




@appeal_router.patch('/{id}', status_code=status.HTTP_200_OK)
async def update_appeal(id: int,  appeal: AppealUpdateSchema, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.ADMIN, User_Status.CEO]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        check_appeal = session.query(Appeal).filter(Appeal.id == id).first()

        for key, value in appeal.dict(exclude_unset=True).items():
            if hasattr(check_appeal, key):
                setattr(check_appeal, key, value)

        check_appeal.updated_at = datetime.utcnow()

        appeal_history = AppealHistory(
            appeal_id=check_appeal.id,
            user_id=user.id,
            text=f"{user.fio} ta'repinen o'zgeris kiritildi"
        )

        session.add(appeal_history)
        session.commit()
        return HTTPException(status_code=status.HTTP_200_OK)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)