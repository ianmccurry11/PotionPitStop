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
        result = connection.execute(sqlalchemy.text("SELECT gold, red_ml, blue_ml, green_ml, dark_ml FROM globals")).first()
        result2 = connection.execute(sqlalchemy.text("SELECT SUM(invnetory) AS total_potions FROM potions")).scalar_one()
    num_ml = result.red_ml + result.blue_ml + result.green_ml + result.dark_ml
    
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
