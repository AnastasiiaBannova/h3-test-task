from fastapi import APIRouter, Depends, HTTPException, Query, Response
from loguru import logger

from h3_test_task.api.dependencies import get_hex_dataset_service
from h3_test_task.services.errors import InvalidBorderError, InvalidHexIdxError, InvalidResolutionError
from h3_test_task.services.hex_dataset import HexDatasetService

router = APIRouter()


@router.get(path="/hex", response_model=list[list[str | int]])
async def get_by_parent(
    parent_hex: str,
    hex_dataset_service: HexDatasetService = Depends(get_hex_dataset_service),
) -> list[list[str | int]]:
    try:
        return hex_dataset_service.get_by_parent(parent_hex)
    except InvalidHexIdxError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:
        logger.error(f"Unknown error: {exc}")
        raise HTTPException(status_code=400, detail="Unknown error") from exc


@router.get(path="/avg", response_model=list[list[str | int]])
def get_avg(
    resolution: int = Query(ge=0, le=12),
    service: HexDatasetService = Depends(get_hex_dataset_service),
) -> list[list[str | int]]:
    try:
        return service.get_avg_by_resolution(resolution)
    except InvalidResolutionError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:
        logger.error(f"Unknown error: {exc}")
        raise HTTPException(status_code=400, detail="Unknown error") from exc


@router.get("/bbox", response_model=list[list[str | int]])
def get_bbox(
    border: str,
    service: HexDatasetService = Depends(get_hex_dataset_service),
) -> list[list[str | int]]:
    try:
        return service.get_by_bbox(border)
    except InvalidBorderError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:
        logger.error(f"Unknown error: {exc}")
        raise HTTPException(status_code=400, detail="Unknown error") from exc


@router.get("/bbox_kml")
def get_bbox_kml(
    border: str,
    service: HexDatasetService = Depends(get_hex_dataset_service),
) -> Response:
    try:
        kml_bytes = service.get_kml_by_bbox(border)
        return Response(
            content=kml_bytes,
            media_type="application/vnd.google-earth.kml+xml",
            headers={"Content-Disposition": 'attachment; filename="hex.kml"'},
        )
    except InvalidBorderError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:
        logger.error(f"Unknown error: {exc}")
        raise HTTPException(status_code=400, detail="Unknown error") from exc
