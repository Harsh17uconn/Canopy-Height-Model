""""Original code by Harshana Wedegedara"""
import os
import json
import multiprocessing
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import pdal
import logging

# Configure logging
logging.basicConfig(
    filename="chm_processing.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Helper functions
def read_raster(file_path):
    with rasterio.open(file_path) as src:
        array = src.read(1)
        transform = src.transform
        crs = src.crs
    return array, transform, crs

def resample_dem_to_1m(dem_path):
    with rasterio.open(dem_path) as dem:
        transform, width, height = calculate_default_transform(
            dem.crs, dem.crs, dem.width, dem.height, *dem.bounds, resolution=1
        )
        resampled_dem = np.empty((height, width), dtype=np.float32)
        reproject(
            source=rasterio.band(dem, 1),
            destination=resampled_dem,
            src_transform=dem.transform,
            src_crs=dem.crs,
            dst_transform=transform,
            dst_crs=dem.crs,
            resampling=Resampling.bilinear
        )
    return resampled_dem, transform, dem.crs

def create_dsm_chm(las_file, dem_path, output_folder_dsm, output_folder_chm, worker_id):
    """
    Generate DSM and CHM from a LAS file and corresponding DEM.
    Includes only first returns and classifications 3, 4, and 5.
    """
    file_basename = os.path.splitext(os.path.basename(las_file))[0]
    dem_array, dem_transform, dem_crs = resample_dem_to_1m(dem_path)

    # Define DSM output path
    dsm_output_path = os.path.join(output_folder_dsm, f"{file_basename}_worker_{worker_id}.tif")
    dsm_pipeline = [
        {"type": "readers.las", "filename": las_file},
        {"type": "filters.range", "limits": "Classification[3:5],ReturnNumber[1:1]"},
        {"type": "filters.reprojection", "out_srs": str(dem_crs)},
        {"type": "writers.gdal", 
         "filename": dsm_output_path,  
         "output_type": "max", 
         "radius": 1,  
         "resolution": 1, 
         "nodata": -9999, 
         "gdaldriver": "GTiff"}
    ]

    # Execute DSM pipeline and save directly to file (no in-memory storage)
    dsm_pipeline_obj = pdal.Pipeline(json.dumps(dsm_pipeline))
    dsm_pipeline_obj.execute()

    # Read DSM from file for CHM calculation
    with rasterio.open(dsm_output_path) as dsm:
        dsm_data = dsm.read(1)

        if dsm_data.shape != dem_array.shape:
            dsm_resampled = np.empty(dem_array.shape, dtype=np.float32)
            reproject(
                source=dsm_data,
                destination=dsm_resampled,
                src_transform=dsm.transform,
                src_crs=dsm.crs,
                dst_transform=dem_transform,
                dst_crs=dem_crs,
                resampling=Resampling.bilinear
            )
            dsm_data = dsm_resampled

    # Calculate CHM
    chm_data = dsm_data - dem_array
    chm_data[(dsm_data == -9999) | (dem_array == -9999)] = -9999
    chm_data[chm_data < 0] = 0
    chm_data[chm_data > 60] = 0

    # Save CHM to disk as a .tif file
    chm_path = os.path.join(output_folder_chm, f"{file_basename}_worker_{worker_id}.tif")
    with rasterio.open(
        chm_path, 'w', driver='GTiff', height=chm_data.shape[0], width=chm_data.shape[1],
        count=1, dtype=np.float32, crs=dem_crs, transform=dem_transform
    ) as dst:
        dst.write(chm_data, 1)

    logging.info(f"CHM saved to: {chm_path}")
    return chm_path

def process_las_file(las_file, las_folder, dem_folder, output_folder_dsm, output_folder_chm, worker_id):
    """
    Process a single LAS file by creating the DSM and CHM.
    Skips if CHM already exists.
    """
    las_file_name = os.path.basename(las_file)
    grid_name = os.path.splitext(las_file_name)[0]

    las_file_path = os.path.join(las_folder, las_file_name)
    dem_file_path = os.path.join(dem_folder, f"{grid_name}.tif")
    chm_output_path = os.path.join(output_folder_chm, f"{grid_name}_worker_{worker_id}.tif")

    if not os.path.exists(dem_file_path):
        logging.warning(f"DEM file not found for {grid_name}. Skipping.")
        return None

    if os.path.exists(chm_output_path):
        logging.info(f"Worker {worker_id} CHM already exists for {grid_name}. Skipping.")
        return None

    logging.info(f"Worker {worker_id} processing {grid_name}.")
    try:
        create_dsm_chm(las_file_path, dem_file_path, output_folder_dsm, output_folder_chm, worker_id)
        logging.info(f"Worker {worker_id} completed {grid_name}.")
        return f"Worker {worker_id} completed {grid_name}"
    except Exception as e:
        logging.error(f"Worker {worker_id} failed to process {grid_name}: {e}")
        return None

def worker(worker_id, tasks, las_folder, dem_folder, output_folder_dsm, output_folder_chm):
    """
    Worker function for processing LAS files.
    """
    for las_file in tasks:
        process_las_file(las_file, las_folder, dem_folder, output_folder_dsm, output_folder_chm, worker_id)

def parallel_process_tiles(las_files, num_workers, las_folder, dem_folder, output_folder_dsm, output_folder_chm):
    """
    Parallel processing of LAS files using multiple workers.
    """
    chunk_size = max(1, len(las_files) // num_workers)
    file_chunks = [las_files[i:i + chunk_size] for i in range(0, len(las_files), chunk_size)]

    with multiprocessing.Pool(num_workers) as pool:
        pool.starmap(worker, [
            (worker_id, file_chunks[worker_id], las_folder, dem_folder, output_folder_dsm, output_folder_chm)
            for worker_id in range(num_workers)
        ])

if __name__ == '__main__':
    LAS_FOLDER = "path/to/your/las/folder"
    DEM_FOLDER = "path/to/your/dem/folder"
    OUTPUT_FOLDER_DSM = "path/to/your/output/dsm/folder"
    OUTPUT_FOLDER_CHM = "path/to/your/output/chm/folder"

    # Create output directories if they don't exist
    os.makedirs(OUTPUT_FOLDER_DSM, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER_CHM, exist_ok=True)

    # List all .laz files in the LAS folder
    las_files = [os.path.join(LAS_FOLDER, f) for f in os.listdir(LAS_FOLDER) if f.endswith(".laz")]

    # Number of workers
    num_workers = min(50, len(las_files))

    logging.info(f"Using {num_workers} workers for {len(las_files)} LAS files.")

    parallel_process_tiles(las_files, num_workers, LAS_FOLDER, DEM_FOLDER, OUTPUT_FOLDER_DSM, OUTPUT_FOLDER_CHM)
