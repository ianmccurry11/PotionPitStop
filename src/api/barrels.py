import sys
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
import logging
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

    gold_paid = 0
    red_ml = 0
    blue_ml = 0
    green_ml = 0
    dark_ml = 0

    red   = [1, 0, 0, 0]
    green = [0, 1, 0, 0]
    blue  = [0, 0, 1, 0]
    dark  = [0, 0, 0, 1]

    for barrel_delivered in barrels_delivered:
        gold_paid += barrel_delivered.price * barrel_delivered.quantity
        print(barrel_delivered)
        if barrel_delivered.potion_type == [1,0,0,0]:
            red_ml += barrel_delivered.ml_per_barrel * barrel_delivered.quantity
        elif barrel_delivered.potion_type == [0,1,0,0]:
            green_ml += barrel_delivered.ml_per_barrel * barrel_delivered.quantity
        elif barrel_delivered.potion_type == [0,0,1,0]:
            blue_ml += barrel_delivered.ml_per_barrel * barrel_delivered.quantity
        elif barrel_delivered.potion_type == [0,0,0,1]:
            dark_ml += barrel_delivered.ml_per_barrel * barrel_delivered.quantity
        else:
             raise Exception("Invalid potion type with potion type" + str(barrel_delivered.potion_type))
        
    print(f"gold_paid: {gold_paid} red_ml:{red_ml} blue_ml: {blue_ml} green_ml: {green_ml} dark_ml: {dark_ml}")

    with db.engine.begin() as connection:
        trans_id = connection.execute(
                        sqlalchemy.text("""
                                        INSERT into transactions
                                        (description)
                                        VALUES 
                                        ('RECIEVED BARREL DELIVERY')
                                        RETURNING 
                                        id;
                                        """)).scalar_one()
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO
                global_ledger (gold, red_ml, green_ml, blue_ml, dark_ml, transaction_id)
                VALUES
                (:gold, :red, :green, :blue, :dark, :trans_id);
                """),
            [{"red": red_ml, "green": green_ml, "blue": blue_ml, "dark": dark_ml, "gold": -gold_paid, "trans_id": trans_id}])

    return "OK"

class Barrel_plan(BaseModel):
    sku: str
    quantity: int

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT SUM(gold) AS gold, SUM(red_ml) AS red, SUM(green_ml) AS green, SUM(blue_ml) AS blue, SUM(dark_ml) AS dark FROM global_ledger")).first()

    gold = result.gold
    red_ml = result.red
    green_ml = result.green
    blue_ml = result.blue
    dark_ml = result.dark

    r_best, r_gold, r_sku, red   = 0, 0, None, [1,0,0,0]
    g_best, g_gold, g_sku, green = 0, 0, None, [0,1,0,0]
    b_best, b_gold, b_sku, blue  = 0, 0, None, [0,0,1,0]
    d_best, d_gold, d_sku, dark  = 0, 0, None, [0,0,0,1]

    barrels = []

    for barrel in wholesale_catalog:
        if (barrel.potion_type == dark and gold >= barrel.price and dark_ml < 2000):
            if(barrel.ml_per_barrel/barrel.price > d_best):
                    d_best = barrel.ml_per_barrel/barrel.price
                    d_sku = barrel.sku
                    d_gold = barrel.price
        elif (barrel.potion_type == blue and gold >= barrel.price and blue_ml < 2000):
            if(barrel.ml_per_barrel/barrel.price > b_best):
                    b_best = barrel.ml_per_barrel/barrel.price
                    b_sku = barrel.sku
                    b_gold = barrel.price
        elif (barrel.potion_type == green and gold >= barrel.price and green_ml < 2000):
            if(barrel.ml_per_barrel/barrel.price > g_best):
                    g_best = barrel.ml_per_barrel/barrel.price
                    g_sku = barrel.sku
                    g_gold = barrel.price
        elif (barrel.potion_type == red and gold >= barrel.price and red_ml < 2000):
            if(barrel.ml_per_barrel/barrel.price > r_best):
                    r_best = barrel.ml_per_barrel/barrel.price
                    r_sku = barrel.sku
                    r_gold = barrel.price

    if(d_sku is not None and d_gold <= gold):
        barrels.append(Barrel_plan(sku= d_sku,quantity= 1))
        gold -= r_gold
    if(r_sku is not None and r_gold <= gold):
        barrels.append(Barrel_plan(sku= r_sku,quantity= 1))
        gold -= r_gold
    if(b_sku is not None and g_gold <= gold):
        barrels.append(Barrel_plan(sku= b_sku,quantity= 1))
        gold -= b_gold
    if(g_sku is not None and b_gold <= gold):
        barrels.append(Barrel_plan(sku= g_sku,quantity= 1))
        gold -= g_gold


    
    if(len(barrels) <= 0):
        print("RETURNED EMPTY BARREL PLAN")
        return()
    else:
        print("PLANNING BARRELS\n")
        print(barrels)
        return barrels
