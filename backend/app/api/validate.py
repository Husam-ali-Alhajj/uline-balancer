from fastapi import APIRouter

from app.schemas.problem import ProblemInput
from app.schemas.run import ValidateResponse
from app.services.instance import summarize

router = APIRouter(tags=["validate"])


@router.post("/validate", response_model=ValidateResponse)
def validate(problem: ProblemInput) -> ValidateResponse:
    """Dry run: validates the input and returns cycle time and minimum stations (no GA).

    Invalid input never reaches this body: FastAPI returns 422 in the standard error format.
    """
    return ValidateResponse(valid=True, instance=summarize(problem))
