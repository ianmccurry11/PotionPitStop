from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class NewCart(BaseModel):
    customer: str

@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    with db.engine.begin() as connection:
        cart_id = connection.execute(
                    sqlalchemy.text(
                                    """
                                    INSERT INTO carts 
                                    (name) 
                                    VALUES 
                                    (:customer)
                                    RETURNING
                                    cart_id
                                    """),
                                    [{"customer": new_cart.customer}]).scalar_one()


    return {"cart_id": cart_id}

@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """
    with db.engine.begin() as connection:
        name = connection.execute(
                sqlalchemy.text(
                                """
                                SELECT name
                                FROM carts
                                WHERE cart_id = :cart_id
                                """),
                                [{"cart_id": cart_id}]).scalar_one()
    return name

class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                            """
                            INSERT INTO cart_items (cart_id, potion_id, quantity)
                            SELECT :cart_id, potions.potion_id, :quantity
                            FROM potions WHERE potions.sku = :item_sku
                            """),
                            [{"cart_id": cart_id, "quantity": cart_item.quantity, "item_sku": item_sku}])

    return "OK"

class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    total_pots, total_cost = 0, 0
    with db.engine.begin() as connection:
        name = connection.execute(sqlalchemy.text("SELECT name FROM carts WHERE cart_id = :id"),[{"id": cart_id}]).scalar_one()
        total_potions = connection.execute(sqlalchemy.text("""
                                                       SELECT COALESCE(SUM(quantity),0) AS total_potions 
                                                       FROM cart_items 
                                                       JOIN potions ON potions.potion_id = cart_items.potion_id 
                                                       WHERE cart_id = :cart_id
                                                       """), [{"cart_id": cart_id}]).scalar_one()
        total_gold = connection.execute(sqlalchemy.text("""
                                                       SELECT COALESCE(SUM(quantity*price),0) AS total_gold 
                                                       FROM cart_items 
                                                       JOIN potions ON potions.potion_id = cart_items.potion_id 
                                                       WHERE cart_id = :cart_id
                                                       """), [{"cart_id": cart_id}]).scalar_one()
        transaction_id = connection.execute(
                                sqlalchemy.text("""
                                                INSERT into transactions
                                                (description) 
                                                VALUES 
                                                (CONCAT('SOLD :quantity POTIONS FOR :price GOLD, TO ', :name , ' - :cart_id'))
                                                RETURNING
                                                id;
                                                """),
                                                [{ "cart_id": cart_id, "price": int(total_gold), "quantity": total_potions, "name": str(name)}]).scalar_one()

        connection.execute(
            sqlalchemy.text(
                        """
                        INSERT INTO
                        potion_ledger (cart_id, transaction_id, change, potion_id)
                        SELECT
                        :cart_id, :trans_id, -cart_items.quantity, cart_items.potion_id
                        FROM cart_items
                        WHERE cart_items.cart_id = :cart_id
                        
                        """),
                        [{"trans_id": transaction_id, "cart_id": cart_id}])

        connection.execute(
            sqlalchemy.text(
                        """
                        INSERT INTO
                        global_ledger (gold, transaction_id)
                        VALUES
                        (:gold, :trans_id)
                        """),
                        [{"trans_id": transaction_id, "gold": int(total_gold)}])
            
    print("SOLD " + str(total_potions) + " POTIONS, GOT " + str(total_gold) + " GOLD")
    return {"total_potions_bought": total_potions, "total_gold_paid": int(total_gold)}
