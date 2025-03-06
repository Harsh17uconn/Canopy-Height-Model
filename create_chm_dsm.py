""""Original code by Harshana Wedegedara"""
import os
import json
import pdal
import rasterio
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling

def resample_dem_to_1m(dem_path):
    """
    Resample a DEM to 1 meter resolution (in-memory operation).

    Args:
        dem_path (str): Path to the input DEM file.

    Returns:
        tuple: Resampled DEM array, transform, and CRS.
    """
    with rasterio.open(dem_path) as dem:
        transform, width, height = calculate_default_transform(
            dem.crs, dem.crs, dem.width, dem.height, *dem.bounds, resolution=3.28084
        )  # Set resolution to 1 meter
        resampled_dem = np.empty((height, width), dtype=np.float32)
        reproject(
            source=rasterio.band(dem, 1),
            destination=resampled_dem,
            src_transform=dem.transform,
            src_crs=dem.crs,
            dst_transform=transform,
            dst_crs=dem.crs,
            resampling=Resampling.bilinear  # Bilinear resampling for elevation data
        )

    return resampled_dem, transform, dem.crs

def create_dsm_chm(las_file, dem_path, output_folder):
    """
    Create DSM and CHM from a LAS file and DEM (in-memory DSM via /vsimem/).

    Args:
        las_file (str): Path to the input LAS file.
        dem_path (str): Path to the input DEM file.
        output_folder (str): Path to the output folder for saving results.

    Returns:
        tuple: CHM data, transform, and CRS.
    """
    file_basename = os.path.splitext(os.path.basename(las_file))[0]

    # Resample DEM to 1 meter resolution (in-memory)
    dem_array, dem_transform, dem_crs = resample_dem_to_1m(dem_path)

    # Save resampled DEM with "_DEM.tif" suffix
    dem_resampled_path = os.path.join(output_folder, f"{file_basename}_DEM.tif")
    with rasterio.open(
        dem_resampled_path, 'w', driver='GTiff', height=dem_array.shape[0], width=dem_array.shape[1],
        count=1, dtype=np.float32, crs=dem_crs, transform=dem_transform
    ) as dst:
        dst.write(dem_array, 1)

    print(f"Resampled DEM saved to: {dem_resampled_path}")

    # Define PDAL pipeline for DSM with the same resolution as DEM (1 meter)
    dsm_vsimem_path = f"/vsimem/{file_basename}_DSM.tif"
    dsm_pipeline = [
        {"type": "readers.las", "filename": las_file},
        {"type": "filters.reprojection", "out_srs": str(dem_crs)},
        {"type": "filters.range", "limits": "Classification[4:5]"},
        {
            "type": "writers.gdal",
            "filename": dsm_vsimem_path,
            "output_type": "max",
            "radius": 3.28084,
            "resolution": 3.28084,
            "nodata": -9999,
            "gdaldriver": "GTiff"
        }
    ]

    # Run DSM pipeline
    dsm_pipeline_obj = pdal.Pipeline(json.dumps(dsm_pipeline))
    dsm_pipeline_obj.execute()

    # Read the DSM from virtual memory
    with rasterio.open(dsm_vsimem_path) as dsm:
        dsm_data = dsm.read(1)

        # Check if DSM shape matches DEM shape
        if dsm_data.shape != dem_array.shape:
            print(f"Resampling DSM to match DEM dimensions for {file_basename}...")
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

    # Calculate CHM by subtracting DEM from DSM (in-memory operation)
    chm_data = dsm_data - dem_array
    chm_data[(dsm_data == -9999) | (dem_array == -9999)] = -9999
    chm_data[chm_data < 6.5] = 0  # Threshold for minimum height
    chm_data[chm_data > 115] = 0  # Threshold for maximum height

    return chm_data, dem_transform, dem_crs

def process_las_and_dem_files(las_folder, dem_folder, output_folder):
    """
    Process LAS and DEM files to create CHMs (in-memory operation).

    Args:
        las_folder (str): Path to the folder containing LAS files.
        dem_folder (str): Path to the folder containing DEM files.
        output_folder (str): Path to the folder for saving CHM and DEM files.
    """
    las_files = [f for f in os.listdir(las_folder) if f.endswith(".las")]
    dem_files = [f for f in os.listdir(dem_folder) if f.endswith(".tif")]

    for las_file in las_files:
        las_basename = os.path.splitext(las_file)[0]
        matching_dems = [dem_file for dem_file in dem_files if las_basename in dem_file]

        if matching_dems:
            dem_file = matching_dems[0]
            las_path = os.path.join(las_folder, las_file)
            dem_path = os.path.join(dem_folder, dem_file)

            print(f"Processing LAS: {las_file} with DEM: {dem_file}")

            # Create CHM
            chm_data, dem_transform, dem_crs = create_dsm_chm(las_path, dem_path, output_folder)

            # Save CHM
            chm_path = os.path.join(output_folder, f"{las_basename}_CHM.tif")
            with rasterio.open(
                chm_path, 'w', driver='GTiff', height=chm_data.shape[0], width=chm_data.shape[1],
                count=1, dtype=np.float32, crs=dem_crs, transform=dem_transform
            ) as dst:
                dst.write(chm_data, 1)

            print(f"CHM saved to: {chm_path}")
        else:
            print(f"No matching DEM found for LAS: {las_file}")

# Example usage
if __name__ == "__main__":
    las_folder = "path/to/your/las/folder"  # Folder with .las files
    dem_folder = "path/to/your/dem/folder"  # Folder with DEM files
    output_folder = "path/to/your/output/folder"  # Folder to save CHM and DEM files

    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    process_las_and_dem_files(las_folder, dem_folder, output_folder)