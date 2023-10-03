from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    print(barrels_delivered)

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, gold FROM global_inventory"))

    num_red_ml = result[0]
    gold = result[1]

    with db.engine.begin() as connection:
        result2 = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = {}, gold = {}"
                                                     .format(barrels_delivered[0].ml_per_barrel + num_red_ml, gold - barrels_delivered[0].price)))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions, gold FROM global_inventory"))

    num_red_pots = result[0]
    gold = result[1]

    if(num_red_pots < 10):
        for barrel in wholesale_catalog:
            if(barrel.potion_type[0] == 100 & gold >= barrel.price):
                sku = barrel.sku
                break

    if(sku == None):
        return []

    return [
        {
            "sku": sku,
            "quantity": 1,
        }
    ]
