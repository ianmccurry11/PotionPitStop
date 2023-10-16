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
    print("Payment:" + cart_checkout.payment)
    total_pots, total_cost = 0, 0
    with db.engine.begin() as connection:
        total_potions = connection.execute(sqlalchemy.text("""
                                                       SELECT SUM(quantity) AS total_potions 
                                                       FROM cart_items 
                                                       JOIN potions ON potions.potion_id = cart_items.potion_id 
                                                       WHERE cart_id = :cart_id
                                                       """), [{"cart_id": cart_id}]).scalar_one()
        total_gold = connection.execute(sqlalchemy.text("""
                                                       SELECT SUM(quantity*price) AS total_gold 
                                                       FROM cart_items 
                                                       JOIN potions ON potions.potion_id = cart_items.potion_id 
                                                       WHERE cart_id = :cart_id
                                                       """), [{"cart_id": cart_id}]).scalar_one()
        connection.execute(
            sqlalchemy.text(
                        """
                        UPDATE potions
                        SET inventory = inventory - cart_items.quantity 
                        FROM cart_items
                        WHERE potions.potion_id = cart_items.potion_id and cart_items.cart_id = :cart_id;
                        UPDATE globals
                        SET gold = gold + :total_gold, potion_inventory = potion_inventory - :total_potions
                        """),
                        [{"cart_id": cart_id, "total_gold": int(total_gold), "total_potions": total_potions}])
            
    print("SOLD " + str(total_potions) + "POTIONS")
    return {"total_potions_bought": total_potions, "total_gold_paid": int(total_gold)}
