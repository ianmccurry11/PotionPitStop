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
        print('POTIONS BEING DELIVERED\n')
        print(potions_delivered)

        red_ml = sum(potion.quantity * potion.potion_type[0] for potion in potions_delivered)
        green_ml = sum(potion.quantity * potion.potion_type[1] for potion in potions_delivered)
        blue_ml = sum(potion.quantity * potion.potion_type[2] for potion in potions_delivered)
        dark_ml = sum(potion.quantity * potion.potion_type[3] for potion in potions_delivered)
        trans_id = connection.execute(
                    sqlalchemy.text("""
                                    INSERT into transactions
                                    (description)
                                    VALUES 
                                    ('MAKING POTIONS')
                                    RETURNING 
                                    id;
                                    """)).scalar_one()
        for potions_delivered in potions_delivered:

            potion_sku = connection.execute(
                            sqlalchemy.text("""
                                            SELECT 
                                            sku
                                            FROM potions
                                            WHERE potion_type = :type
                                            """),[{"type": potions_delivered.potion_type}]).scalar_one()
            connection.execute(
                sqlalchemy.text(
                    """
                    INSERT into potion_ledger
                    (transaction_id, potion_sku, change)
                    VALUES
                    (:trans_id, :potion_sku, :quantity)
                    """),
                [{"quantity": potions_delivered.quantity, "potion_sku": potion_sku, "trans_id": trans_id}])

        connection.execute(
            sqlalchemy.text(
                    """
                    INSERT INTO
                    global_ledger (gold, red_ml, green_ml, blue_ml, dark_ml, transaction_id)
                    VALUES
                    (0, :red, :green, :blue, :dark, :trans_id);
                    """),
            [{"red": -red_ml, "green": -green_ml, "blue": -blue_ml, "dark": -dark_ml, "trans_id": trans_id}])

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(
                        sqlalchemy.text("SELECT SUM(gold) AS gold, SUM(red_ml) AS red, SUM(green_ml) AS green, SUM(blue_ml) AS blue, SUM(dark_ml) AS dark FROM global_ledger")).first()
        possible_potions = connection.execute(
                                sqlalchemy.text("SELECT * FROM potions  ORDER by potion_id DESC")).all()
        total_potions = connection.execute(
                            sqlalchemy.text("SELECT COALESCE(SUM(change), 0) FROM potion_ledger")).scalar_one()
    total_pots = total_potions
    staged = 0
    potions  = []
    red_ml   = result.red
    green_ml = result.green
    blue_ml  = result.blue
    dark_ml  = result.dark

    for potion in possible_potions:
        while total_pots < 300 and staged < 25 and potion.potion_type[0] <= red_ml and potion.potion_type[1] <= green_ml and potion.potion_type[2] <= blue_ml and potion.potion_type[3] <= dark_ml:
            staged   += 1
            red_ml   -= potion.potion_type[0]
            green_ml -= potion.potion_type[1]
            blue_ml  -= potion.potion_type[2]
            dark_ml  -= potion.potion_type[3]
            total_pots += 1
        if staged > 0:
            potions.append(PotionInventory(potion_type= potion.potion_type, quantity= staged))
        staged = 0

    if len(potions) <= 0:
        print("NO POTIONS PLANNED")
        return()
    else:
        print(potions)
        return potions
