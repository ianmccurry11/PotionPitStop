from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print(potions_delivered)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_red_potions FROM global_inventory"))
    
    red_ml = result[0]
    red_pots = result[1]
    quant = potions_delivered[0].quantity

    with db.engine.begin() as connection:
        result2 = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = {}, num_red_potions = {}"
                                                     .format(red_ml - quant * 10, red_pots + quant)))


    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_blue_ml, num_green_ml FROM global_inventory"))

    red_ml = result[0]
    blue_ml = result[1]
    green_ml = result[2]

    red = [100,0,0,0]
    blue = [0,0,100,0]
    green = [0,100,0,0]

    potions = list[PotionInventory]

    red_quan = (int)(red_ml/100)
    blue_quan = (int)(blue_ml/100)
    green_quan = (int)(green_ml/100)

    if (red_quan > 0):
        potions.append(
            {
                "potion_type": red,
                "quantity": red_quan,
            }
            )
    if (blue_quan > 0):
        potions.append(
            {
                "potion_type": blue,
                "quantity": red_quan,
            }
            )
    if (green_quan > 0):
        potions.append(
            {
                "potion_type": green,
                "quantity": red_quan,
            }
            )
        
    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

    return [
        potions
        ]
