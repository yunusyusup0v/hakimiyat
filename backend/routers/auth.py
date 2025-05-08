from fastapi import HTTPException, status, Depends, APIRouter
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import InvalidHeaderError
from passlib.hash import bcrypt
from backend.database import Session, connect
from backend.model import User
from backend.schema import UserLoginSchema, UserRegisterSchema, UserResponse
import datetime




auth_router = APIRouter(prefix='/auth', tags=['AUTH'])


def verify(Authorization: AuthJWT = Depends(), session: Session = Depends(connect)):
    try:
        Authorization.jwt_required()

        user_login = Authorization.get_jwt_subject()
        user = session.query(User).filter(User.login == user_login).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )



@auth_router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(user: UserRegisterSchema, session: Session = Depends(connect)):
    check_user_login = session.query(User).filter(User.login == user.login).first()
    if check_user_login:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Пользователь с логином {user.login} уже существует")

    new_user = User(
        fio=user.fio,
        login=user.login,
        password=bcrypt.hash(user.password),
        phone=user.phone,
        role=user.role
    )
    session.add(new_user)
    session.commit()
    return {"message": "Пользователь успешно зарегистрирован"}



@auth_router.post('/login', status_code=status.HTTP_200_OK)
async def login(user: UserLoginSchema, session: Session = Depends(connect), Authorize: AuthJWT = Depends()):
    check_user = session.query(User).filter(User.login == user.login).first()
    if not check_user or not bcrypt.verify(user.password, check_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    if not check_user.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Аккаунт не активен")

    access_token = Authorize.create_access_token(subject=check_user.login, expires_time=datetime.timedelta(hours=1))
    refresh_token = Authorize.create_refresh_token(subject=check_user.login, expires_time=datetime.timedelta(hours=3))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }




@auth_router.post('/refresh', status_code=status.HTTP_200_OK)
async def refresh(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        login = Authorize.get_jwt_subject()

        if login is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        new_access_token = Authorize.create_access_token(subject=login, expires_time=datetime.timedelta(hours=1))

        return {
            "access_token": new_access_token
        }

    except InvalidHeaderError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

