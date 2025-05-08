import os
from fastapi import FastAPI, status, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.schema import Settings
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from backend.database import Session, ENGINE, connect
from backend.model import User
from fastapi.staticfiles import StaticFiles
from logging.handlers import TimedRotatingFileHandler
from fastapi_jwt_auth.exceptions import InvalidHeaderError, MissingTokenError, JWTDecodeError





import logging
from backend.routers.user import user_router
from backend.routers.mekeme import mekeme_router
from backend.routers.mahalla import mahalla_router
from backend.routers.sector import sector_router
from backend.routers.auth import auth_router
from backend.routers.tg_appeal import tg_appeal_router, tg_user_router
from backend.routers.appeal import appeal_router
from backend.routers.base_page import statistics_router

session = Session(bind=ENGINE)




app = FastAPI(
    # redoc_url=None,
    # docs_url=None,
    # debug=False,
    # tags = ['ME']
)


@AuthJWT.load_config
def get_config():
    return Settings()






app.include_router(auth_router)
app.include_router(user_router)
app.include_router(mekeme_router)
app.include_router(mahalla_router)
app.include_router(sector_router)
app.include_router(tg_user_router)
app.include_router(tg_appeal_router)
app.include_router(appeal_router)
app.include_router(statistics_router)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)




@app.get('/me', status_code=status.HTTP_200_OK)
async def user_me(session : Session = Depends(connect), Authorization: AuthJWT = Depends()):
    try:
        Authorization.jwt_required()
        login = Authorization.get_jwt_subject()

        user = session.query(User).filter(User.login == login).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        data = {
            "id": user.id,
            "fio": user.fio,
            "login": user.login,
            "phone": user.phone,
            "role": user.role,
            "mekemeId": user.mekeme_id,
        }
        return jsonable_encoder(data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

app.mount("/appeal-files", StaticFiles(directory="appeal-files"), name="appeal-files")


logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "user_log.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.handlers = []


handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, encoding="utf-8", backupCount=3)
handler.suffix = "%d-%m-%Y"

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    user_id = "Anonymous"

    try:
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            Authorize = AuthJWT()
            decoded_token = Authorize.get_raw_jwt(token)
            login = decoded_token.get("sub")

            user = session.query(User).filter(User.login == login).first()
            if user:
                user_id = user.id

    except (MissingTokenError, InvalidHeaderError, JWTDecodeError):
        user_id = "Anonymous"
    except Exception as e:
        logger.error(f"Неожиданная ошибка при разборе токена: {e}")
        user_id = "Anonymous"

    response = await call_next(request)

    try:
        logger.info(
            f"User ID: {user_id}, Method: {request.method}, URL: {request.url}, "
            f"Status: {response.status_code}"
        )
    except Exception as e:
        logger.error(f"Ошибка при записи логов: {e}")

    return response