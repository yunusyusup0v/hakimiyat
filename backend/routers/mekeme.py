from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from backend.model import User, User_Status, Mekeme
from backend.database import Session, connect
from backend.routers.auth import verify
from backend.schema import MekemeCreateSchema, MekemeUpdateSchema



mekeme_router = APIRouter(prefix='/mekeme', tags=['MEKEME'])



@mekeme_router.get('', status_code=status.HTTP_200_OK)
async def get_mekeme_all(page : int = Query(1, ge=1),  limit : int = Query(10, ge=1), session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        skip = (page-1) * limit

        mekemeler = session.query(Mekeme).offset(skip).limit(limit).all()

        data_mekeme = [
            {
                "id" : mekeme.id,
                "name" : mekeme.name,
                "address" : mekeme.address
            }
            for mekeme in mekemeler
        ]

        all_mekeme = session.query(Mekeme).count()
        pagination = {
            "limit": limit,
            "page" : page,
            "total" : all_mekeme
        }

        data = {
            "data" : data_mekeme,
            "pagination" : pagination
        }

        return jsonable_encoder(data)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)



@mekeme_router.get('/option', status_code=status.HTTP_200_OK)
async def option(session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        mekemeler = session.query(Mekeme.id, Mekeme.name).all()

        return [{"value" : mekeme.id, "label" : mekeme.name} for mekeme in mekemeler]

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)




@mekeme_router.get('/{id}', status_code=status.HTTP_200_OK)
async def get_mekeme_id(id : int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        mekeme = session.query(Mekeme).filter(Mekeme.id == id).first()

        mekeme_user = session.query(User).filter(User.mekeme_id == mekeme.id).all()

        users = mekeme.user

        workers_ids = [str(user.id) for user in mekeme_user]
        data = {
            "name" : mekeme.name,
            "address" : mekeme.address,
            "user_ids" : workers_ids,
            "user" : [{"id" : user.id, "fio" : user.fio, "phone" : user.phone} for user in users]
        }
        return jsonable_encoder(data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)



@mekeme_router.post('', status_code=status.HTTP_201_CREATED)
async def create_mekeme(mekeme: MekemeCreateSchema, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        check_mekeme = session.query(Mekeme).filter(Mekeme.name == mekeme.name).first()

        if check_mekeme:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
                "message" : "already_exsist",
                "name" : mekeme.name
            })

        new_mekeme = Mekeme(
            name=mekeme.name,
            address=mekeme.address
        )

        session.add(new_mekeme)
        session.commit()


        if mekeme.user_ids:
            users = session.query(User).filter(
                User.id.in_(mekeme.user_ids),
                User.role == User_Status.USER,
                User.mekeme_id == None
            ).all()

            for user in users:
                user.mekeme_id = new_mekeme.id
                user.is_active = True
                session.add(user)

        session.commit()


        data = {
            "message": f"{new_mekeme.name} mekeme created",
        }
        return jsonable_encoder(data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)




@mekeme_router.patch('/{id}', status_code=status.HTTP_200_OK)
async def update_mekeme(id: int, mekeme_schema: MekemeUpdateSchema, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        mekeme = session.query(Mekeme).filter(Mekeme.id == id).first()

        if mekeme.name:
            check_mekeme = session.query(Mekeme).filter(Mekeme.name == mekeme.name).first()
            if check_mekeme and check_mekeme.id != id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
                "message" : "already_exsist",
                "name" : mekeme.name
            })


        for key, value in mekeme_schema.dict(exclude_unset=True).items():
            setattr(mekeme, key, value)


        if mekeme.user_ids is not None:
            old_users = session.query(User).filter(User.mekeme_id == mekeme.id).all()


            for user in old_users:
                user.mekeme_id = None
                user.is_active = False

            session.commit()

            new_users = session.query(User).filter(User.id.in_(mekeme.user_ids)).all()
            for user in new_users:
                user.mekeme_id = mekeme.id
                user.is_active = True


        session.commit()

        data = {
            f"{mekeme.name} updated successfully": f"{mekeme}"
        }
        return jsonable_encoder(data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)





@mekeme_router.delete('/{id}', status_code=status.HTTP_200_OK)
async def delete(id : int, session : Session = Depends(connect),  user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        check_mekeme = session.query(Mekeme).filter(Mekeme.id == id).first()


        session.delete(check_mekeme)
        session.commit()

        data = {
            "message": f"{check_mekeme.name} deleted successfully"
        }
        return jsonable_encoder(data)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)