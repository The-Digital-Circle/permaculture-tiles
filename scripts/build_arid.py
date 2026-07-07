"""Turn a Köppen-Geiger classification GeoTIFF into simplified 'arid' polygons for the peach wash.

Source raster (CC-BY 4.0): Beck et al. 2018, "Present and future Köppen-Geiger climate
classification maps at 1-km resolution" — use the 0.5° 'Beck_KG_V1_present_0p5.tif' (small; coarse
is ample at z0-8). Download it manually and pass its path.

    python scripts/build_arid.py path/to/Beck_KG_V1_present_0p5.tif data/arid.geojson

Class ids 4=BWh 5=BWk 6=BSh 7=BSk are the arid 'B' climates.
"""
import sys
import numpy as np
import rasterio
from rasterio.features import shapes
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

def build(tif_path: str, out_path: str, simplify_deg: float = 0.4, smooth_deg: float = 0.5):
    with rasterio.open(tif_path) as src:
        band = src.read(1)
        transform = src.transform
        crs = src.crs
    mask = arid_class_mask(band).astype(np.uint8)
    polys = [shape(geom) for geom, val in shapes(mask, mask=mask.astype(bool), transform=transform)
             if val == 1]
    gdf = gpd.GeoDataFrame(geometry=polys, crs=crs).to_crs(4326)
    # dissolve, simplify, and smooth (buffer out+in) so deserts read as deliberate soft regions
    merged = gdf.union_all() if hasattr(gdf, "union_all") else gdf.unary_union
    merged = merged.simplify(simplify_deg).buffer(smooth_deg).buffer(-smooth_deg * 0.7)
    out = gpd.GeoDataFrame(geometry=[merged], crs=4326)
    out.to_file(out_path, driver="GeoJSON")
    print(f"wrote {out_path}")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
