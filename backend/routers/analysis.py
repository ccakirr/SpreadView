from fastapi import APIRouter

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
    return analyze(
        y=y,
        x=x,
        interval=interval,
        window=window,
    )
