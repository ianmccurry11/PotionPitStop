from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from enum import Enum
from sqlalchemy import func


router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    # Use reflection to derive table schema. You can also code this in manually.
    metadata_obj = sqlalchemy.MetaData()
    carts = sqlalchemy.Table("carts", metadata_obj, autoload_with=db.engine)
    potions = sqlalchemy.Table("potions", metadata_obj, autoload_with=db.engine)
    potion_ledger = sqlalchemy.Table("potion_ledger", metadata_obj, autoload_with=db.engine)
    transactions = sqlalchemy.Table("transactions", metadata_obj, autoload_with=db.engine)

    if sort_col is search_sort_options.customer_name:
        order_by = carts.c.name
    elif sort_col is search_sort_options.item_sku:
        order_by = potions.c.name
    elif sort_col is search_sort_options.line_item_total:
        order_by = 'total'
    elif sort_col is search_sort_options.timestamp:
        order_by = transactions.c.created_at

    if sort_order is search_sort_order.asc:
        order_by = sqlalchemy.asc(order_by)
    elif sort_order is search_sort_order.desc:
        order_by = sqlalchemy.desc(order_by)

    if search_page != "":
        offset = int(search_page) 
    else:
        offset = 0
    if offset - 5 < 0:
        previous = "" 
    else: 
        previous = str(offset - 5)
        
    with db.engine.begin() as connection:
        stmt = (
            sqlalchemy.select(
                transactions.c.id,
                transactions.c.created_at,
                potions.c.sku,
                carts.c.name,
                potion_ledger.c.change,
                potions.c.price,
                func.abs((potion_ledger.c.change * potions.c.price)).label('total'),
            )
            .join(potion_ledger, potion_ledger.c.transaction_id == transactions.c.id)
            .join(potions, potions.c.sku == potion_ledger.c.potion_sku)
            .join(carts, carts.c.cart_id == potion_ledger.c.cart_id)
            .order_by(order_by, transactions.c.id)
            .offset(offset)
            .limit(5)
        )

        if customer_name != "":
            stmt = stmt.where(carts.c.name.ilike(f"%{customer_name}%"))
        
        if potion_sku != "":
            stmt = stmt.where(potions.c.sku.ilike(f"%{potion_sku}%"))

        list = []
        result = connection.execute(stmt)
        index = offset + 1
        for row in result:
            transaction_id, created_at, sku, name, change, price, total = row
            list.append({
                "line_item_id": index,
                "item_sku": sku,
                "customer_name": name,
                "line_item_total": total,
                "timestamp": created_at,
            })
            index += 1
        next = 0
        if len(list) == 5:
            next = str(offset + 5)
        else:
            next = ""
    
    return {    
        "previous": previous,
        "next": next,
        "results": list,
    }


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
                            INSERT INTO cart_items (cart_id, potion_sku, quantity)
                            SELECT :cart_id, :item_sku, :quantity
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
                                                       JOIN potions ON potions.sku = cart_items.potion_sku
                                                       WHERE cart_id = :cart_id
                                                       """), [{"cart_id": cart_id}]).scalar_one()
        total_gold = connection.execute(sqlalchemy.text("""
                                                       SELECT COALESCE(SUM(quantity*price),0) AS total_gold 
                                                       FROM cart_items 
                                                       JOIN potions ON potions.sku = cart_items.potion_sku
                                                       WHERE cart_id = :cart_id
                                                       """), [{"cart_id": cart_id}]).scalar_one()
        transaction_id = connection.execute(
                                sqlalchemy.text("""
                                                INSERT into transactions
                                                (description, cart_id) 
                                                VALUES 
                                                (CONCAT('SOLD :quantity POTIONS FOR :price GOLD, TO ', :name , ' - :cart_id'),cart_id)
                                                RETURNING
                                                id;
                                                """),
                                                [{ "cart_id": cart_id, "price": int(total_gold), "quantity": total_potions, "name": str(name)}]).scalar_one()

        connection.execute(
            sqlalchemy.text(
                        """
                        INSERT INTO
                        potion_ledger (cart_id, transaction_id, change, potion_sku)
                        SELECT
                        :cart_id, :trans_id, -cart_items.quantity, cart_items.potion_sku
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
