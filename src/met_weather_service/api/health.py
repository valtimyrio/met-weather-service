from fastapi import APIRouter

router = APIRouter(tags=["service"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
