from fastapi.encoders import jsonable_encoder
from backend.model import Appeal, User, User_Status, Appeal_Status, Mekeme, TgUserAppeal
from fastapi import APIRouter, Depends, status, HTTPException
from backend.database import Session, connect
from backend.routers.auth import verify
from sqlalchemy import  or_, func
from datetime import datetime, date, timedelta







statistics_router = APIRouter(prefix='/statistics', tags=["STATISTICS"])



@statistics_router.get('', status_code=status.HTTP_200_OK)
async def statistics(session : Session = Depends(connect), user : User = Depends(verify)):
    try:
        if user.role in [User_Status.CEO, User_Status.ADMIN]:
            appeals_query = session.query(Appeal)
        else:
            appeals_query = session.query(Appeal).filter(Appeal.mekeme_id == user.mekeme_id)

        all_appeals = appeals_query.count()
        done_appeals = appeals_query.filter(Appeal.appeal_status == Appeal_Status.SUCCESS_DONE).count() + appeals_query.filter(Appeal.appeal_status == Appeal_Status.TEXT_DONE).count()
        waiting_appeals = appeals_query.filter(Appeal.appeal_status == Appeal_Status.WAITING).count()
        rejected_appeals = appeals_query.filter(Appeal.appeal_status == Appeal_Status.REJECTED).count()
        time_request = appeals_query.filter(Appeal.appeal_status == Appeal_Status.TIME_REQUEST).count()
        archive_appeals = appeals_query.filter(Appeal.appeal_status == Appeal_Status.ARCHIVE).count()

        confirm_appeals = appeals_query.filter(
            or_(
                Appeal.appeal_status == Appeal_Status.CONFIRM,
                Appeal.appeal_status == Appeal_Status.CONFIRM_50
            )
        ).count()

        today = date.today()
        today_appeals = appeals_query.filter(
            Appeal.created_at >= datetime.combine(today, datetime.min.time()),
            Appeal.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
        ).count()

        yesterday_start = datetime.now() - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday_start.date(), datetime.min.time())
        yesterday_end = datetime.combine(yesterday_start.date(), datetime.max.time())

        yesterday_appeals = appeals_query.filter(
            Appeal.created_at >= yesterday_start,
            Appeal.created_at <= yesterday_end
        ).count()



        first_day_of_month = datetime(datetime.now().year, datetime.now().month, 1)
        next_month = datetime.now().month % 12 + 1
        year_for_next_month = datetime.now().year if next_month > 1 else datetime.now().year + 1
        last_day_of_month = datetime(year_for_next_month, next_month, 1) - timedelta(days=1)

        current_month_appeals = appeals_query.filter(
            Appeal.created_at >= first_day_of_month,
            Appeal.created_at <= last_day_of_month
        ).count()


        first_day_of_year = datetime(datetime.now().year, 1, 1)
        last_day_of_year = datetime(datetime.now().year, 12, 31, 23, 59, 59, 999999)

        current_year_appeals = appeals_query.filter(
            Appeal.created_at >= first_day_of_year,
            Appeal.created_at <= last_day_of_year
        ).count()


        tg_appeals = session.query(TgUserAppeal).count()

        data = {
            "all_appeals": all_appeals,
            "done_appeals": done_appeals,
            "waiting_appeals": waiting_appeals,
            "rejected_appeals": rejected_appeals,
            "time_requests": time_request,
            "archive_appeals": archive_appeals,
            "confirm_appeals": confirm_appeals,
            "today_appeals": today_appeals,
            "yesterday_appeals": yesterday_appeals,
            "month_appeals": current_month_appeals,
            "year_appeals": current_year_appeals,
            "tg_appeals" : tg_appeals if user.role in [User_Status.CEO, User_Status.ADMIN] else ""
        }

        return jsonable_encoder(data)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{e}")





@statistics_router.get('/mekeme', status_code=status.HTTP_200_OK)
async def mekeme(session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        mekeme_stats = []

        mekeme_stats = session.query(Mekeme.id, Mekeme.name, func.count(Appeal.id).label('appeal_count')).join(Appeal, Mekeme.id == Appeal.mekeme_id) \
            .group_by(Mekeme.id, Mekeme.name) \
            .order_by(func.count(Appeal.id).desc()) \
            .limit(5) \
            .all()

        if not mekeme_stats:
            return HTTPException(status_code=404)

        result = [
            {"mekeme_id": row[0], "mekeme_name": row[1], "total_appeals": row[2]}
            for row in mekeme_stats
        ]

        return result


    except HTTPException as http_exc:
            raise http_exc
    except Exception as e:
        raise HTTPException(status_code=400)