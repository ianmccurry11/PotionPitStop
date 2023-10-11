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

class item(BaseModel):
    sku: str
    quantity: int
    price: int


class info(BaseModel):
    customer: str
    items: list[item]

class NewCart(BaseModel):
    customer: str

info_dict = {}
cart_id = -1

@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    global cart_id
    cart_id += 1

    temp = info(customer=new_cart.customer,items=[])
    info_dict[cart_id] = temp

    return {"cart_id": cart_id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """
    global info_dict
    if(len(info_dict) > cart_id):
        temp2 = info_dict[cart_id].customer
        return {temp2}
    else:
        return {None}

class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    global info_dict

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions, num_blue_potions, num_green_potions FROM global_inventory")).first()

    red_pots = result.num_red_potions
    blue_pots = result.num_blue_potions
    green_pots = result.num_green_potions

    if(item_sku == "RED_POTION_0"):
        instock = red_pots
    elif(item_sku == "BLUE_POTION_0"):
        instock = blue_pots
    elif(item_sku == "GREEN_POTION_0"):
        instock = green_pots
    else:
        return "ITEM SKU NOT FOUND"

    if(check_stock(instock=instock, requested=cart_item.quantity) == False):
        return "NOT ENOUGH OF ITEM IN STOCK"

    item1 = item(sku= item_sku,quantity=cart_item.quantity,price=50)
    info_dict[cart_id].items.append(item1)

    return "OK"

def check_stock(instock: int, requested: int):
    if(instock < requested):
        return False
    else:
        return True

class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions, num_blue_potions, num_green_potions, gold FROM global_inventory")).first()
    
    red_pots = result.num_red_potions
    blue_pots = result.num_blue_potions
    green_pots = result.num_green_potions
    gold = result.gold

    global info_dict
    total_pots = 0
    total_cost = 0

    file1 = open("Payments.txt", "a") 
    file1.write("payment = {} from {}\n".format(cart_checkout.payment,info_dict[cart_id].customer))
    file1.close() 

    file2 = open("Ledger.txt", "a") 
    
    for item1 in info_dict[cart_id].items:
        if(item1.sku == "RED_POTION_0" and item1.quantity <= red_pots):
            print("SELLING RED POTION")
            with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_potions = {}"
                                             .format(red_pots - item1.quantity)))
                red_pots -= item1.quantity
                total_pots += item1.quantity
                total_cost += item1.quantity * item1.price
                file2.write("just sold {} red pots to {}\n".format(item1.quantity, info_dict[cart_id].customer))
        elif(item1.sku == "BLUE_POTION_0" and item1.quantity <= blue_pots):
            print("SELLING BLUE POTION")
            with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_potions = {}"
                                             .format(blue_pots - item1.quantity)))
                blue_pots -= item1.quantity
                total_pots += item1.quantity
                total_cost += item1.quantity * item1.price
                file2.write("just sold {} blue pots to {}\n".format(item1.quantity,info_dict[cart_id].customer))
        elif(item1.sku == "GREEN_POTION_0" and item1.quantity <= green_pots):
            print("SELLING GREEN POTION")
            with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = {}"
                                             .format(green_pots - item1.quantity)))
                green_pots -= item1.quantity
                total_pots += item1.quantity
                total_cost += item1.quantity * item1.price
                file2.write("just sold {} green pots to {}\n".format(item1.quantity,info_dict[cart_id].customer))

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = {}"
                                    .format(gold + total_cost)))

    file2.close() 

    return {"total_potions_bought": total_pots, "total_gold_paid": total_cost}
