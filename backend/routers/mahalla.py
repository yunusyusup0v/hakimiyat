from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from backend.model import User_Status, Mahalla, User, Sector
from backend.routers.auth import verify
from backend.schema import CreateMahallaSchema, UpdateMahallaSchema, MahallaOption
from backend.database import Session, connect
from typing import List


mahalla_router = APIRouter(prefix='/mahalla', tags=['MAHALLA'])


@mahalla_router.get('', status_code=status.HTTP_200_OK)
async def mahallaa(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    session : Session = Depends(connect),
    user : User = Depends(verify)
):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        skip = (page - 1) * limit

        total_mahalla = session.query(Mahalla).count()
        all_mahalla = session.query(Mahalla).offset(skip).limit(limit).all()

        pagination = {
            "limit" : limit,
            "page" : page,
            "total": total_mahalla,
        }

        data = [
            {"id": mahalla.id, "name": mahalla.name, "sector": mahalla.sector.name if mahalla.sector else None}
            for mahalla in all_mahalla
        ]

        response = {
            "data": data,
            "pagination": pagination
        }

        return jsonable_encoder(response)


    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)






@mahalla_router.get('/option', status_code=status.HTTP_200_OK, response_model=List[MahallaOption])
async def option(session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{user.fio} YOU ARE NOT ADMIN")

        mahallalar = session.query(Mahalla.id, Mahalla.name).all()

        return [{"value" : mahalla.id, "label" : mahalla.name} for mahalla in mahallalar]

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)






@mahalla_router.get('/{id}', status_code=status.HTTP_200_OK)
async def get_mahalla(id : int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:
        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        mahalla = session.query(Mahalla).filter(Mahalla.id == id).first()

        if mahalla is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return {"id" : mahalla.id, "name" : mahalla.name, "sector_id" : mahalla.sector_id}

    except HTTPException as http:
        raise http
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)






@mahalla_router.post('', status_code=status.HTTP_201_CREATED)
async def create_mahalla(mahalla: CreateMahallaSchema, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if not user or user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        sector = session.query(Sector).filter(Sector.id == mahalla.sector_id).first()
        if not sector:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sector not found")

        check_mahalla = session.query(Mahalla).filter(Mahalla.name == mahalla.name).first()

        if check_mahalla:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
                "message": "already_exsist",
                "name": mahalla.name
            })

        new_mahalla = Mahalla(
            name=mahalla.name,
            sector_id=mahalla.sector_id
        )

        session.add(new_mahalla)
        session.commit()

        data = {
            "message": f"{new_mahalla.name} created"
        }
        return jsonable_encoder(data)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)





@mahalla_router.patch('/{id}', status_code=status.HTTP_200_OK)
async def update_mahalla(id: int, mahalla: UpdateMahallaSchema, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


        check_mahalla = session.query(Mahalla).filter(Mahalla.id == id).first()

        if not check_mahalla:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        if mahalla.name:
            existing_mahalla = session.query(Mahalla).filter(Mahalla.name == mahalla.name, Mahalla.id != id).first()
            if existing_mahalla:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={
                    "message": "already_exists",
                    "name": mahalla.name
                })


        for key, value in mahalla.dict(exclude_unset=True).items():
            setattr(check_mahalla, key, value)

        session.commit()

        data = {f"{check_mahalla.name} mahalla updated successfully": f"{jsonable_encoder(check_mahalla)}"}
        return jsonable_encoder(data)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)







@mahalla_router.delete('/{id}', status_code=status.HTTP_200_OK)
async def delete_mahalla(id: int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        check_mahalla = session.query(Mahalla).filter(Mahalla.id == id).first()

        if not check_mahalla:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        session.delete(check_mahalla)
        session.commit()

        data = {
            "message" : f"{check_mahalla.name} deleted successfully"
        }
        return jsonable_encoder(data)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)