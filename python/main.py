#!/usr/bin/env python3
# Direct-run SLIC segmentation for tree-height raster
# Requires: rasterio scikit-image numpy affine

import math
import numpy as np
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from affine import Affine
from skimage.segmentation import slic

# --- CONFIG: edit if needed ---
IN_PATH = "/Users/kanoalindiwe/Downloads/Work/LF2023_EVH_240_HI/Tif/LH23_EVH_240.tif"
OUT_PATH = "/Users/kanoalindiwe/Downloads/Work/LH23_EVH_240_segments.tif"
N_SEGMENTS = 600       # fewer => larger regions
COMPACTNESS = 20.0     # higher => more spatially compact
SIGMA = 1.0            # Gaussian smoothing prior to SLIC
DOWNSCALE = 2          # 1 = full res; try 2 or 4 for speed on large rasters
# ------------------------------

def run_slic(in_path: str, out_path: str,
             n_segments: int, compactness: float, sigma: float,
             downscale: int = 1) -> None:
    # Read raster
    with rio.open(in_path) as src:
        arr = src.read(1, masked=False)
        nodata = src.nodata
        mask = np.ones_like(arr, dtype=bool) if nodata is None else (arr != nodata)

        # Optional downscale to speed segmentation
        if downscale > 1:
            scale = downscale
            new_h = math.ceil(src.height / scale)
            new_w = math.ceil(src.width / scale)
            arr_ds = src.read(
                1,
                out_shape=(new_h, new_w),
                resampling=Resampling.average
            )
            # Resample mask to the same target shape to avoid off-by-one mismatches
            mask_ds = src.read_masks(
                1,
                out_shape=(new_h, new_w),
                resampling=Resampling.nearest,
            ) > 0
            arr_for_seg = arr_ds
            seg_transform = src.transform * Affine.scale(scale)
            profile = src.profile
            crs = src.crs
        else:
            arr_for_seg = arr
            mask_ds = mask
            seg_transform = src.transform
            profile = src.profile
            crs = src.crs

    img = arr_for_seg.astype(np.float32)

    # Run SLIC on single-band image
    labels_small = slic(
        img,
        n_segments=n_segments,
        compactness=compactness,
        sigma=sigma,
        start_label=1,
        mask=mask_ds,
        channel_axis=None,
    )
    labels_small = np.where(mask_ds, labels_small, 0).astype(np.int32)

    # Upsample labels if downscaled
    if downscale > 1:
        # Reproject labels back to full resolution exactly
        with rio.open(in_path) as src:
            dst_h, dst_w = src.height, src.width
            out_transform = src.transform
            profile = src.profile
            crs = src.crs
        labels = np.zeros((dst_h, dst_w), dtype=np.int32)
        reproject(
            source=labels_small.astype(np.int32),
            destination=labels,
            src_transform=seg_transform,
            src_crs=crs,
            dst_transform=out_transform,
            dst_crs=crs,
            resampling=Resampling.nearest,
        )
        # reapply nodata outside mask
        with rio.open(in_path) as src:
            mask_full = np.ones((src.height, src.width), dtype=bool) if src.nodata is None else (src.read(1) != src.nodata)
        labels[~mask_full] = 0
    else:
        labels = labels_small
        with rio.open(in_path) as src:
            out_transform = src.transform
            profile = src.profile
            crs = src.crs

    # Write labeled GeoTIFF
    profile.update(dtype="int32", count=1, compress="LZW", nodata=0)
    with rio.open(out_path, "w", **profile) as dst:
        dst.write(labels, 1)
        dst.transform = out_transform
        dst.crs = crs

    print(f"Saved segment labels → {out_path}")
    print("Tip: lower N_SEGMENTS for larger regions; raise COMPACTNESS for tighter shapes.")


if __name__ == "__main__":
    run_slic(IN_PATH, OUT_PATH, N_SEGMENTS, COMPACTNESS, SIGMA, DOWNSCALE)