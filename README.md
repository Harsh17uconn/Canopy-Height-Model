# CHM Generation Script

This repository contains a Python script (`create_chm_dsm.py`) designed to generate Digital Surface Models (DSM) and Canopy Height Models (CHM) from LAS (LiDAR) files and corresponding Digital Elevation Models (DEM). The script leverages **PDAL (Point Data Abstraction Library)** and **rasterio** for efficient point cloud and raster processing, with support for parallel execution on multi-core systems.

## Features
- **DSM Generation**: Creates a DSM from LAS files, including only first returns and classifications 3, 4, and 5 (vegetation-related points).
- **CHM Calculation**: Computes the CHM by subtracting the resampled DEM from the DSM, with height constraints (0 to 60 meters).
- **Parallel Processing**: Utilizes Python's `multiprocessing` to process multiple LAS files concurrently, optimized for high-performance computing (HPC) environments.
- **Resolution Standardization**: Resamples DEM and DSM to 1-meter resolution for consistency.
- **Skip Existing Files**: Skips processing if the CHM output file already exists, avoiding redundant computations.
- **Logging**: Records processing details, warnings, and errors to `chm_processing.log`.

## Requirements
- **Python 3.x**
- **PDAL**: Install via `pip install pdal` (may require additional dependencies like GDAL/GEOS on HPC systems).
- **rasterio**: Install via `pip install rasterio`.
- **numpy**: Install via `pip install numpy`.
- **multiprocessing**, **os**, **json**: Included in Python standard library.
- **Conda Environment**: Recommended to use a Conda environment (e.g., `randla_pytorch`) on HPC systems.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/chm-generation.git
   cd chm-generation

2. Set up a Conda environment (optional but recommended):
   ```bash
   conda create -n chm_gen python=3.9 -y
   conda activate chm_gen
   pip install pdal rasterio numpy

3. Update the following variables in chm_processing.py with your paths:
   ```bash
   LAS_FOLDER: Path to your LAS files.
   DEM_FOLDER: Path to your DEM files.
   OUTPUT_FOLDER_DSM: Path to save DSM output files.
   OUTPUT_FOLDER_CHM: Path to save CHM output files.

5. Run the script:
   ```bash
   python create_chm_dsm.py

  ![image](https://github.com/user-attachments/assets/d34965a8-fc13-4566-a587-a47665305fae)

- **Figure**: Canopy Height Model
