# DSM and CHM Generator

This repository contains a Python script (`create_dsm_chm.py`) designed to generate Digital Surface Models (DSM) and Canopy Height Models (CHM) from LAS files and Digital Elevation Models (DEM) using **PDAL** and **Rasterio**. The script processes LAS files to create a DSM, resamples the DEM to a 1-meter resolution, and computes the CHM by subtracting the DEM from the DSM, all while leveraging in-memory operations for efficiency.

## Features
- **DSM Generation**: Creates a DSM from LAS files using PDAL with ground and vegetation classes (Classification 4-5).
- **DEM Resampling**: Resamples the input DEM to a 1-meter resolution using bilinear interpolation.
- **CHM Calculation**: Computes the CHM by subtracting the resampled DEM from the DSM, with height thresholding (6.5 to 115 meters).
- **In-Memory Processing**: Uses `/vsimem/` for DSM creation to avoid intermediate file storage, improving performance.
- **File Matching**: Matches LAS and DEM files by basename for automated processing.
- **Output**: Saves resampled DEM and CHM as GeoTIFF files with proper CRS and transform.

## Assumptions
- **Existing DEM**: This script assumes that you already have a Digital Elevation Model (DEM) available in GeoTIFF format, matching the spatial extent of your LAS files. The DEM should be named such that its basename matches the corresponding LAS file for automatic pairing.
- **Coordinate Reference System (CRS)**: The LAS and DEM files should be in compatible CRS, or the script will reproject the LAS to match the DEM’s CRS.

## Requirements
- **Python 3.x**
- **PDAL**: Install via `pip install pdal` (may require GDAL/GEOS on HPC systems).
- **Rasterio**: Install via `pip install rasterio`.
- **Dependencies**: `numpy`, `os`, `json`.
- **Conda Environment**: Recommended for managing dependencies, especially on HPC systems like UConn HPC.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/dsm-chm-generator.git
   cd dsm-chm-generator

- **CHM output**:
  ![image](https://github.com/user-attachments/assets/d34965a8-fc13-4566-a587-a47665305fae)
