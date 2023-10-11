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
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_blue_ml, num_green_ml, num_red_potions, num_blue_potions, num_green_potions FROM global_inventory")).first()
    
    red_ml = result.num_red_ml
    blue_ml = result.num_blue_ml
    green_ml = result.num_green_ml

    red_pots = result.num_red_potions
    blue_pots = result.num_blue_potions
    green_pots = result.num_green_potions

    red = [1,0,0,0]
    blue = [0,0,1,0]
    green = [0,1,0,0]

    for potion in potions_delivered:
        if(potion.potion_type == red):
            quant = potion.quantity
            if(red_ml >= quant*100):
                with db.engine.begin() as connection:
                    result2 = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = {}, num_red_potions = {}"
                                                .format(red_ml - quant * 100, red_pots + quant)))
                red_ml -= quant*100
        if(potion.potion_type == blue):
            quant = potion.quantity
            if(blue_ml >= quant*100):
                with db.engine.begin() as connection:
                    result2 = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_ml = {}, num_blue_potions = {}"
                                                .format(blue_ml - quant * 100, blue_pots + quant)))
                blue_ml -= quant*100
        if(potion.potion_type == green):
            quant = potion.quantity
            if(green_ml >= quant):
                with db.engine.begin() as connection:
                    result2 = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = {}, num_green_potions = {}"
                                                .format(green_ml - quant * 100, green_pots + quant)))
                green_ml -= quant*100

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_blue_ml, num_green_ml FROM global_inventory")).first()

    count = 0

    red_ml = result.num_red_ml
    blue_ml = result.num_blue_ml
    green_ml = result.num_green_ml

    red = [1,0,0,0]
    blue = [0,0,1,0]
    green = [0,1,0,0]

    potions = []

    red_quan = (int)(red_ml/100)
    blue_quan = (int)(blue_ml/100)
    green_quan = (int)(green_ml/100)

    if (red_quan > 0):
        count+=1
        temp = PotionInventory(potion_type=red,quantity=red_quan)
        potions.append(temp)
    if (blue_quan > 0):
        count+=1
        temp = PotionInventory(potion_type=blue,quantity=blue_quan)
        potions.append(temp)
    if (green_quan > 0):
        count+=1
        temp = PotionInventory(potion_type=green,quantity=green_quan)
        potions.append(temp)
        
    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.
    if(count == 0):
        print("NO POTIONS PLANNED")
        return()
    print(potions)
    return potions
