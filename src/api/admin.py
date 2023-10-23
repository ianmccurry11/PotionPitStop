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
                                                            TRUNCATE global_ledger;
                                                            TRUNCATE transactions;
                                                            INSERT into transactions
                                                            (description)
                                                            VALUES
                                                            ('Admin reset');
                                                            INSERT INTO
                                                            global_ledger (gold, red_ml, green_ml, blue_ml, dark_ml, transaction_id)
                                                            VALUES
                                                            (100, 0, 0, 0, 0,
                                                            (
                                                            SELECT id
                                                            FROM transactions
                                                            limit 1
                                                            ));
                                                            TRUNCATE potion_ledger;
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

