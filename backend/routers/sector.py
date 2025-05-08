from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from backend.model import  Sector, User, User_Status
from backend.database import Session, connect
from backend.routers.auth import verify
from backend.schema import SectorSchema



sector_router = APIRouter(prefix='/sector', tags=['SECTOR'])




@sector_router.post('', status_code=status.HTTP_200_OK)
async def create_sector(
    sector : SectorSchema,
    session : Session = Depends(connect),
    user : User = Depends(verify)
):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


        new_sector = Sector(
            name = sector.name
        )
        session.add(new_sector)
        session.commit()
        session.refresh(new_sector)


        data = {"message": f"Sector ID - [{new_sector.id}] created"}
        return jsonable_encoder(data)

    except HTTPException as http_excep:
        raise http_excep
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)




@sector_router.get('', status_code=status.HTTP_200_OK)
async def sector(session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        sector = session.query(Sector).all()

        data = [
            {
                "id" : item.id,
                "name" : item.name
            }
            for item in sector
        ]

        return jsonable_encoder(data)

    except HTTPException as http_excp:
        raise http_excp
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{e}")




@sector_router.get('/option', status_code=status.HTTP_200_OK)
async def sector(session : Session = Depends(connect), user : User = Depends(verify)):
    try:

        if user.role not in [User_Status.CEO, User_Status.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        sectors = session.query(Sector).all()

        return [{"label": f"{sector.name}", "value": str(sector.id)} for sector in sectors]


    except HTTPException as http_excp:
        raise http_excp
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"{e}")


