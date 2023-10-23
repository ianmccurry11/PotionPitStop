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
        result = connection.execute(sqlalchemy.text("SELECT SUM(gold) AS gold, COALESCE(SUM(red_ml + blue_ml + green_ml + dark_ml), 0) AS ml FROM global_ledger")).first()
        result2 = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(change), 0) AS total_potions FROM potion_ledger")).scalar_one()
    num_ml = result.ml
    
    return {"number_of_potions": result2, "ml_in_barrels": num_ml, "gold": result.gold}

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
