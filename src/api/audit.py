from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold, num_red_ml, num_blue_ml, num_green_ml, num_red_potions, num_blue_potions, num_green_potions FROM global_inventory")).first()
    num_pots = result.num_red_potions + result.num_blue_potions + result.num_green_potions
    num_ml = result.num_red_ml + result.num_blue_ml + result.num_green_ml
    
    return {"number_of_potions": num_pots, "ml_in_barrels": num_ml, "gold": result.gold}

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print(audit_explanation)

    return "OK"
