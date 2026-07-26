from collections import defaultdict
from functools import cached_property
from statistics import median

import h3
from geopy.distance import distance
from loguru import logger
from shapely import Polygon
from shapely.prepared import prep

from h3_test_task.core.settings import settings
from h3_test_task.models.hex import HexModel
from h3_test_task.services.errors import InvalidHexIdxError, InvalidResolutionError, InvalidBorderError


class HexDatasetService:
    KML_NAMESPACE = "http://www.opengis.net/kml/2.2"

    def __init__(self):
        # Cache
        self._parent_hex: dict[str, list[list[str, int, int]]] = {}  # key - parent hex
        self._avg_by_resolution: dict[int, list[list[str, int, int]]] = {}  # key - resolution
        self._bbox: dict[str, list[list[str, int, int]]] = {}  # key - raw border string

    @cached_property
    def _dataset(self) -> list[HexModel]:
        logger.info(
            f"Generating dataset, resolution: {settings.hex_resolution}, "
            f"center: ({settings.area.center.lat}, {settings.area.center.lon}), "
            f"radius: {settings.area.radius}",
        )

        cells = self._cells_in_circle()

        result = []
        for cell in cells:
            int_value = h3.str_to_int(cell)
            result.append(
                HexModel(
                    h3_index=cell,
                    level=(int_value // 512 % 74) - 120,
                    cell_id=(int_value // 512 % 100) + 1,
                )
            )

        return result

    @cached_property
    def _hex_idx(self) -> dict[str, HexModel]:
        return {hex_obj.h3_index: hex_obj for hex_obj in self._dataset}

    def get_by_parent(self, parent_hex: str) -> list[list[str | int]]:
        if not h3.is_valid_cell(parent_hex):
            raise InvalidHexIdxError(f"'{parent_hex}' is not a valid hex index")

        cached = self._parent_hex.get(parent_hex)
        if cached is not None:
            return cached

        parent_resolution = h3.get_resolution(parent_hex)

        if parent_resolution > settings.hex_resolution:
            hex_objects = []
        elif parent_resolution == settings.hex_resolution:
            hex_obj = self._hex_idx.get(parent_hex)
            hex_objects = [hex_obj] if hex_obj else []
        else:
            children = h3.cell_to_children(parent_hex, settings.hex_resolution)
            hex_objects = [self._hex_idx[child] for child in children if child in self._hex_idx]

        result = [hex_obj.as_list() for hex_obj in hex_objects]
        self._parent_hex[parent_hex] = result
        return result

    def get_avg_by_resolution(self, resolution: int) -> list[list[str | int]]:
        if not 0 <= resolution <= settings.hex_resolution:
            raise InvalidResolutionError(
                f"Resolution must be in range from 0 to {settings.hex_resolution}, got {resolution}"
            )

        cached = self._avg_by_resolution.get(resolution)
        if cached is not None:
            return cached

        groups: dict[tuple[str, int], list[int]] = defaultdict(list)

        for hex_obj in self._dataset:
            parent_hex = (
                hex_obj.h3_index
                if resolution == settings.hex_resolution
                else h3.cell_to_parent(hex_obj.h3_index, resolution)
            )
            groups[(parent_hex, hex_obj.cell_id)].append(hex_obj.level)

        result = [
            [parent_hex, median(levels), cell_id]
            for (parent_hex, cell_id), levels in groups.items()
        ]

        self._avg_by_resolution[resolution] = result
        return result

    def get_by_bbox(self, border: str) -> list[list[str | int]]:
        cached = self._bbox.get(border)
        if cached is not None:
            return cached

        border_points = self._parse_border(border)
        border_shape = Polygon([(lon, lat) for lat, lon in border_points])

        if not border_shape.is_valid or border_shape.is_empty:
            raise InvalidBorderError(f"'{border}' does not describe a valid polygon")

        potential_hex_ids = set(h3.polygon_to_cells(h3.LatLngPoly(border_points), settings.hex_resolution))
        hex_objs = (self._hex_idx[idx] for idx in potential_hex_ids if idx in self._hex_idx)

        prepared_border = prep(border_shape)

        result = []
        for hex_obj in hex_objs:
            boundary = h3.cell_to_boundary(hex_obj.h3_index)
            hex_shape = Polygon([(lon, lat) for lat, lon in boundary])
            if prepared_border.covers(hex_shape):
                result.append(hex_obj.as_list())

        self._bbox[border] = result
        return result

    def get_kml_by_bbox(self, border: str) -> bytes:
        records = self._bbox.get(border)
        if records is None:
            records = self.get_by_bbox(border)

        return self._build_kml(records)

    def _build_kml(self, records: list[list[str | int]]) -> bytes:
        placemarks = "".join(
            self._placemark_kml(h3_index, level, cell_id) for h3_index, level, cell_id in records
        )

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<kml xmlns="{self.KML_NAMESPACE}"><Document><name>H3 hexagons</name>'
            f"{placemarks}</Document></kml>"
        ).encode("utf-8")

    def _placemark_kml(self, h3_index: str, level: int, cell_id: int) -> str:
        boundary = h3.cell_to_boundary(h3_index)
        closed_boundary = (*boundary, boundary[0])
        coordinates = " ".join(f"{lon},{lat},0" for lat, lon in closed_boundary)

        return (
            f"<Placemark><name>{h3_index}</name>"
            "<ExtendedData>"
            f'<Data name="level"><value>{level}</value></Data>'
            f'<Data name="cell_id"><value>{cell_id}</value></Data>'
            "</ExtendedData>"
            f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{coordinates}"
            "</coordinates></LinearRing></outerBoundaryIs></Polygon>"
            "</Placemark>"
        )

    def _parse_border(self, border: str) -> list[tuple[float, float]]:
        points = []

        for point_coordinates in border.split(","):
            try:
                lat_str, lon_str = point_coordinates.strip().split("/")
                lat, lon = float(lat_str), float(lon_str)
            except ValueError as exc:
                raise InvalidBorderError(
                    f"Invalid coordinates in border: '{point_coordinates}', expected 'lat/lon'"
                ) from exc

            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise InvalidBorderError(f"Point  out of range: lat={lat}, lon={lon}")

            points.append((lat, lon))

        if len(points) < 3:
            raise InvalidBorderError(
                f"Border must contain at least 3 points to form a polygon, got {len(points)}"
            )

        return points

    def _cells_in_circle(self) -> list[str]:
        polygon = self._circle_polygon()
        return list(h3.polygon_to_cells(polygon, settings.hex_resolution))

    def _circle_polygon(self) -> h3.LatLngPoly:
        points = []

        for angle in range(0, 360, 5):  # 5 degree steps
            point = distance(meters=settings.area.radius).destination(
                (settings.area.center.lat, settings.area.center.lon),
                bearing=angle,
            )
            points.append((point.latitude, point.longitude))

        return h3.LatLngPoly(points)
