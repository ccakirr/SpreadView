from fastapi import APIRouter, HTTPException

from services.analysis import analyze


router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
)


@router.get("")
def get_pair_analysis(
    y: str,
    x: str,
    interval: str = "1d",
    window: int = 21,
):
    try:
        return analyze(
            y=y,
            x=x,
            interval=interval,
            window=window,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from e
