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
    next = 0

    # Use reflection to derive table schema. You can also code this in manually.
    metadata_obj = sqlalchemy.MetaData()
    carts = sqlalchemy.Table("carts", metadata_obj, autoload_with=db.engine)
    potions = sqlalchemy.Table("potions", metadata_obj, autoload_with=db.engine)
    potion_ledger = sqlalchemy.Table("potion_ledger", metadata_obj, autoload_with=db.engine)
    transactions = sqlalchemy.Table("transactions", metadata_obj, autoload_with=db.engine)

    with db.engine.begin() as connection:
        where_message = ""
        if customer_name != "" and potion_sku != "":
            where_message = f"WHERE carts.customer ILIKE '%{customer_name}%' AND cart_items.potion_sku ILIKE '%{potion_sku}%'"
        elif customer_name != "":
            where_message = f"WHERE carts.customer ILIKE '%{customer_name}%'"
        elif potion_sku != "":
            where_message = f"WHERE cart_items.sku ILIKE '%{potion_sku}%'"

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
            .join(transactions, transactions.c.id == potion_ledger.c.transaction_id)
            .offset(offset)
            .order_by(order_by, transactions.c.transaction_id)
            .limit(5)
        )

        if customer_name != "":
            stmt = stmt.where(carts.c.name.ilike(f"%{customer_name}%"))
        
        if potion_sku != "":
            stmt = stmt.where(potions.c.sku.ilike(f"%{potion_sku}%"))

        res = []
        result = connection.execute(stmt)
        index = offset + 1
        for row in result:
            transaction_id, created_at, sku, name, change, price, total = row
            res.append({
                "line_item_id": index,
                "item_sku": sku,
                "customer_name": name,
                "line_item_total": total,
                "timestamp": created_at,
            })
            index += 1
        if len(res) == 5:
            next = str(offset + 5)
        else:
            next = ""
    
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {    
        "previous": previous,
        "next": next,
        "results": res,
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
