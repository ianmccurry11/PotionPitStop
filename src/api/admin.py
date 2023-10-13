from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text("""
                                                            UPDATE globals 
                                                            SET
                                                            red_ml = 0, blue_ml = 0, green_ml = 0, dark_ml = 0, gold = 100, potion_inventory = 0;
                                                            UPDATE potions
                                                            SET
                                                            inventory = 0;
                                                            TRUNCATE carts;
                                                            TRUNCATE cart_items;
                                                            """))

    return "OK"


@router.get("/shop_info/")
def get_shop_info():
    """ """

    # TODO: Change me!
    return {
        "shop_name": "Concoction Costco",
        "shop_owner": "Ian",
    }

