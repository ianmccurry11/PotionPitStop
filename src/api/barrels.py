import sys
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
        result = connection.execute(sqlalchemy.text("SELECT gold, num_red_ml, num_blue_ml, num_green_ml  FROM global_inventory"))

    gold = result[0]
    red_ml = result[1]
    blue_ml = result[2]
    green_ml = result[3]

    red = [100,0,0,0]
    blue = [0,0,100,0]
    green = [0,100,0,0]

    for barrel in barrels_delivered:
        if (barrel.potion_type == red):
            with db.engine.begin() as connection:
                result2 = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = {}, gold = {}"
                                                     .format(barrel.ml_per_barrel + red_ml, gold - barrel.price)))
        elif (barrel.potion_type == blue):
            with db.engine.begin() as connection:
                result2 = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_ml = {}, gold = {}"
                                                     .format(barrel.ml_per_barrel + blue_ml, gold - barrel.price)))
        elif (barrel.potion_type == green):
            with db.engine.begin() as connection:
                result2 = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = {}, gold = {}"
                                                     .format(barrel.ml_per_barrel + green_ml, gold - barrel.price)))



    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold, num_red_potions, num_blue_potions, num_green_potions  FROM global_inventory"))

    gold = result[0]
    red_pots = result[1]
    blue_pots = result[2]
    green_pots = result[3]

    red = [100,0,0,0]
    blue = [0,0,100,0]
    green = [0,100,0,0]

    cheapest = sys.maxint

    for barrel in wholesale_catalog:
        if (barrel.potion_type == red & red_pots < 10 & gold >= barrel.price):
            if(barrel.price < cheapest):
                    cheapest = barrel.price
                    sku = barrel.sku
        elif (barrel.potion_type == blue & blue_pots < 10 & gold >= barrel.price):
            if(barrel.price < cheapest):
                    cheapest = barrel.price
                    sku = barrel.sku
        elif (barrel.potion_type == green & green_pots < 10 & gold >= barrel.price):
            if(barrel.price < cheapest):
                    cheapest = barrel.price
                    sku = barrel.sku

    if(sku == None):
        return []

    return [
        {
            "sku": sku,
            "quantity": 1,
        }
    ]
