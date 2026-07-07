"""Turn a Köppen-Geiger classification GeoTIFF into arid-climate polygons for the peach wash.

Source raster (CC-BY 4.0): Beck et al. 2018, "Present and future Köppen-Geiger climate
classification maps at 1-km resolution". Download Beck_KG_V1.zip from figshare
(https://ndownloader.figshare.com/files/12407516) and pass the 1-km present GeoTIFF
'Beck_KG_V1_present_0p0083.tif'. build() decimates the raster to ~target_deg on read (nearest,
categorical) so the 1-km grid stays tractable to vectorise; a coarser raster is read as-is.

    python scripts/build_arid.py path/to/Beck_KG_V1_present_0p0083.tif data/arid.geojson

Class ids 4=BWh 5=BWk 6=BSh 7=BSk are the arid 'B' climates (deserts + semi-arid steppe); the
steppe classes are what make Australia read as mostly arid. If a different Köppen release is used,
verify its legend still maps 4-7 to BW/BS before building.
"""
import sys
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.enums import Resampling
import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import unary_union

ARID_CLASSES = (4, 5, 6, 7)

def arid_class_mask(grid: np.ndarray) -> np.ndarray:
    return np.isin(grid, ARID_CLASSES)


def decimation_factor(native_deg: float, target_deg: float) -> int:
    """Integer read-decimation so the raster grid is ~target_deg. Never upsamples a coarse raster."""
    return max(1, round(target_deg / native_deg))


def drop_specks(geom, min_area_deg2: float):
    """Remove sub-polygons smaller than min_area_deg2 (CRS units^2). Returns a (Multi)Polygon."""
    parts = list(geom.geoms) if geom.geom_type.startswith("Multi") else [geom]
    kept = [p for p in parts if p.area >= min_area_deg2]
    return unary_union(kept) if kept else geom


def clean(geom, clean_deg: float, simplify_deg: float, min_area_deg2: float):
    """Symmetric close (fill hairline gaps/holes, no net grow/shrink) -> drop specks -> light simplify."""
    closed = geom.buffer(clean_deg).buffer(-clean_deg)
    return drop_specks(closed, min_area_deg2).simplify(simplify_deg)

def build(tif_path: str, out_path: str, target_deg: float = 0.05, simplify_deg: float = 0.03,
          clean_deg: float = 0.05, min_area_deg2: float = 0.1):
    with rasterio.open(tif_path) as src:
        factor = decimation_factor(abs(src.transform.a), target_deg)
        out_h, out_w = src.height // factor, src.width // factor
        band = src.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)
        transform = src.transform * src.transform.scale(src.width / out_w, src.height / out_h)
        crs = src.crs
    mask = arid_class_mask(band).astype(np.uint8)
    polys = [shape(g) for g, val in shapes(mask, mask=mask.astype(bool), transform=transform)
             if val == 1]
    gdf = gpd.GeoDataFrame(geometry=polys, crs=crs).to_crs(4326)
    merged = gdf.union_all() if hasattr(gdf, "union_all") else gdf.unary_union
    merged = clean(merged, clean_deg, simplify_deg, min_area_deg2)
    out = gpd.GeoDataFrame(geometry=[merged], crs=4326)
    out.to_file(out_path, driver="GeoJSON")
    n_regions = len(merged.geoms) if merged.geom_type.startswith("Multi") else 1
    print(f"wrote {out_path}  ({len(polys)} raw polys -> {n_regions} region(s))")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
