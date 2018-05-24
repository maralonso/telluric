import os
import math
import rasterio
import numpy as np
from rasterio import shutil as sh
from rasterio.enums import Resampling, MaskFlags
from tempfile import TemporaryDirectory


def _calc_overviews_factors(one, blocksize=256):
    res = max(one.width, one.height)
    f = math.floor(math.log2(res / blocksize))
    factors = [2**i for i in range(1, f + 2)]
    return factors


def _mask_from_masked_array(data):
    mask = data.mask[0].copy()
    for i in range(1, len(data.mask)):
        mask = np.logical_or(mask, data.mask[i])
    mask = (~mask * 255).astype('uint8')
    return mask


def _has_mask(rast):
    for flags in rast.mask_flag_enums:
        if MaskFlags.per_dataset in flags:
            return True
    return False


def convert_to_cog(source_file, destination_file):
    """Convert source file to a Cloud Optimized GeoTiff new file.

    :param destination_file: path to the new raster
    :param destination_file: path to the new raster
    """
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, 'temp.tif')
            sh.copy(source_file, temp_file, tiled=True, compress='DEFLATE', photometric='MINISBLACK')
            with rasterio.open(temp_file, 'r+') as dest:
                if not _has_mask(dest):
                    mask = dest.dataset_mask()
                    dest.write_mask(mask)

                factors = _calc_overviews_factors(dest)
                dest.build_overviews(factors, resampling=Resampling.cubic)
                dest.update_tags(ns='rio_overview', resampling='cubic')

            sh.copy(temp_file, destination_file,
                    COPY_SRC_OVERVIEWS=True, tiled=True, compress='DEFLATE', photometric='MINISBLACK')
