import bcrypt
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from backend.model import User, User_Status
from backend.database import Session, connect
from backend.routers.auth import verify
from backend.schema import UserRegisterSchema, UserUpdateSchema, UserResponse
from bcrypt import hashpw, gensalt
from typing import Optional


user_router = APIRouter(prefix='/user', tags=['USER'])




@user_router.get('', status_code=status.HTTP_200_OK)
async def users_all(
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    role: Optional[User_Status] = Query(None),
    session: Session = Depends(connect),
    user: UserResponse = Depends(verify)
):
    try:
        # Проверяем роль пользователя
        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        # Логика пагинации
        skip = (page - 1) * limit

        query = session.query(User)

        if role:
            query = query.filter(User.role == role)
        else:
            query = query.filter(User.role != User_Status.CEO)

        if is_active is not None:
            query = query.filter(User.is_active == ("true" if is_active else "false"))

        users = query.offset(skip).limit(limit).all()
        total_users = query.count()

        data = [
            {
                "id": user.id,
                "fio": user.fio,
                "phone": user.phone,
                "login": user.login,
                "role": user.role,
                "mekeme": user.mekeme.name if user.mekeme_id is not None else "",
                "is_active": user.is_active
            }
            for user in users
        ]

        pagination = {
            "total": total_users,
            "limit": limit
        }

        return {"data": data, "pagination": pagination}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)



@user_router.get('/option', status_code=status.HTTP_200_OK)
async def option(session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user is None or user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        users = session.query(User).filter(
            User.role == User_Status.USER
        ).all()

        data =  [
            {
                "value": str(user.id),
                "label": f"{user.fio} {user.mekeme.name if user.mekeme else ""}",
            }
            for user in users
        ]

        return jsonable_encoder(data)


    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)




@user_router.get('/{id}', status_code=status.HTTP_200_OK)
async def user(id : int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        check_user = session.query(User).filter(User.id == id).first()

        data = {
            "id": check_user.id,
            "fio": check_user.fio,
            "login": check_user.login,
            "phone": check_user.phone,
            "role": check_user.role,
            "mekeme_id": check_user.mekeme_id,
            "is_active" : check_user.is_active
        }
        return jsonable_encoder(data)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)



@user_router.post('', status_code=status.HTTP_201_CREATED)
async def create(user: UserRegisterSchema, session: Session = Depends(connect), user_verify : User = Depends(verify)):
    try:

        if user_verify.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        check_user_login = session.query(User).filter(User.login == user.login).first()
        check_user_phone = session.query(User).filter(User.phone == user.phone).first()

        if check_user_login:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={
                "message": "already_exsist",
                "login": user.login
            })

        if check_user_phone:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={
                "message": "already_exsist",
                "login": user.phone
            })

        salt = gensalt()
        hashed_password = hashpw(user.password.encode('utf-8'), salt)


        is_active = True if user.role in [User_Status.CEO, User_Status.ADMIN] else False

        new_user = User(
            fio=user.fio,
            login=user.login,
            password=hashed_password.decode('utf-8'),
            phone=user.phone,
            role=user.role,
            is_active=is_active,
            mekeme_id=user.mekeme_id if user.mekeme_id is not None else None,
        )

        session.add(new_user)
        session.commit()

        return {"detail": "User created successfully"}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)








@user_router.patch('/{id}', status_code=status.HTTP_200_OK)
async def update(id: int, user: UserUpdateSchema, session : Session = Depends(connect), user_verify : User = Depends(verify)):
    try:

        if user_verify.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


        check_user = session.query(User).filter(User.id == id).first()


        if user.login and user.login != check_user.login:
            existing_login_user = session.query(User).filter(User.login == user.login).first()
            if existing_login_user:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={
                    "message": "already_exists",
                    "login": user.login
                })

        if user.phone and user.phone != check_user.phone:
            existing_phone_user = session.query(User).filter(User.phone == user.phone).first()
            if existing_phone_user:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={
                    "message": "already_exists",
                    "phone": user.phone
                })


        if user.password:
            hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
            check_user.password = hashed_password.decode('utf-8')


        for key, value in user.dict(exclude_unset=True).items():
            if key != 'password':
                setattr(check_user, key, value)

        if check_user.mekeme_id is None:
            check_user.is_active = False
        else:
            check_user.is_active = True


        if user.is_active == False:
            check_user.is_active = False
            check_user.mekeme_id = None

        if user.is_active == True:
            check_user.is_active = True


        session.commit()

        data = {
            f"{check_user.fio} updated": f"{check_user}"
        }
        return jsonable_encoder(data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)





@user_router.delete('/{id}', status_code=status.HTTP_200_OK)
async def delete_user(id : int, session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        check_user = session.query(User).filter(User.id == id).first()

        if not check_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        session.delete(check_user)
        session.commit()

        data = {
            "message" : f"{check_user.fio} deleted successfully"
        }

        return jsonable_encoder(data)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
