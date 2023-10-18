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
    
    with db.engine.begin() as connection:
        print(potions_delivered)

        red_ml = sum(potion.quantity * potion.potion_type[0] for potion in potions_delivered)
        green_ml = sum(potion.quantity * potion.potion_type[1] for potion in potions_delivered)
        blue_ml = sum(potion.quantity * potion.potion_type[2] for potion in potions_delivered)
        dark_ml = sum(potion.quantity * potion.potion_type[3] for potion in potions_delivered)

        for potions_delivered in potions_delivered:
            connection.execute(
                sqlalchemy.text(
                    """
                    UPDATE potions
                    SET inventory = inventory + :quantity
                    WHERE potion_type = :potion_type;
                    UPDATE globals
                    SET potion_inventory = potion_inventory + :quantity
                    """),
                [{"quantity": potions_delivered.quantity, "potion_type": potions_delivered.potion_type}])

        connection.execute(
            sqlalchemy.text(
                    """
                    UPDATE globals SET 
                    red_ml = red_ml - :red_ml,
                    green_ml = green_ml - :green_ml,
                    blue_ml = blue_ml - :blue_ml,
                    dark_ml = dark_ml - :dark_ml
                    """),
            [{"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml}])

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT red_ml, blue_ml, green_ml, dark_ml FROM globals")).first()
        possible_potions = connection.execute(
                                sqlalchemy.text(
                                    """
                                    SELECT * 
                                    FROM potions 
                                    ORDER by 
                                    potion_id DESC
                                    """)).all()

    staged = 0
    potions  = []
    red_ml   = result.red_ml
    green_ml = result.green_ml
    blue_ml  = result.blue_ml
    dark_ml  = result.dark_ml

    for potion in possible_potions:
        while potion.inventory + staged < 100 and potion.potion_type[0] <= red_ml and potion.potion_type[1] <= green_ml and potion.potion_type[2] <= blue_ml and potion.potion_type[3] <= dark_ml:
            staged   += 1
            red_ml   -= potion.potion_type[0]
            green_ml -= potion.potion_type[1]
            blue_ml  -= potion.potion_type[2]
            dark_ml  -= potion.potion_type[3]
        if staged > 0:
            potions.append(PotionInventory(potion_type= potion.potion_type, quantity= staged))
        staged = 0

    if len(potions) <= 0:
        print("NO POTIONS PLANNED")
        return()
    else:
        print(potions)
        return potions
