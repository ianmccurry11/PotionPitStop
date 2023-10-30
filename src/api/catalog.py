from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    # Can return a max of 20 items.
    with db.engine.begin() as connection:
        Potion_Inventory = connection.execute(sqlalchemy.text("SELECT * FROM potions")).all()
    

    
        catalog = []
        count = 0

        for potion in Potion_Inventory:
            pot_inventory = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(change), 0) FROM potion_ledger WHERE potion_sku = :potion_sku"),[{"potion_sku": potion.sku}]).scalar_one()
            if int(pot_inventory) > 0 and len(catalog) < 20:
                count += 1
                catalog.append({
                            "sku": potion.sku,
                            "name": potion.name,
                            "quantity": int(pot_inventory),
                            "price": potion.price,
                            "potion_type": potion.potion_type,
                            })
            if count >= 6:
                break

    if len(catalog) <= 0:
        print("NO INVENTORY FOR CATALOG")
        return ()
    else:
        print(catalog)
        return catalog
