# Microscale Carbon Emissions from Daily Multimodal Travel - Helsinki Region Public Transport Itinerary Calculation 

This repository contains a complete high-performance computing (HPC) workflow for modeling microscale CO₂ emissions from daily travel in the Helsinki Region. The process is divided into two main parts:

1.  **Part 1: Itinerary Calculation**: Uses R and `r5r` to compute ~72 million detailed, multimodal public transport (PT) itineraries between origin-destination (OD) pairs.
2.  **Part 2: CO₂ Emission Calculation**: Uses Python to process the generated itineraries, calculate CO₂ emissions based on Life Cycle Assessment (LCA) data, and save the results.

The scripts are optimized for HPC environments managed by the Slurm workload manager (e.g., CSC Puhti).

## Repository Structure
.
├── Batch_Run_r5rDetIti
│   ├── BatchRunCode_r5r_detiti_main_revised_0_300.txt
│   └── rcode_MobiTartu2024.R
│
├── PT_process_Co2data_into_Allas_using_BatchPY
│   ├── batchRun_process_detIti_withCo2_pyfile.txt
│   ├── ProcessData_and_SaveToAllas.py
│   └── DATA_CO2
│       └── LCA_gCO2_per_pkm_by_transport_mode.csv
│
└── README.md

## Methodological Context

The methodology and scientific context for this analysis are detailed in the following preprint:

> Dey, Subhrasankha; Marín-Flores, Cesar; Tenkanen, Henrikki. “A Methodological Framework for Microscale Mapping of Carbon Emissions from Daily Multimodal Travel: Application to the Helsinki Metropolitan Area.” SSRN: <https://ssrn.com/abstract=5348581>

---

## Part 1: Public Transport Itinerary Calculation

This part of the workflow focuses on large-scale public transport routing. The code for this section is located in the `Batch_Run_r5rDetIti` directory.

### Computational Workflow

#### R Routing Script (`rcode_MobiTartu2024.R`)

This is the core computational engine that calculates detailed itineraries for a subset of the OD data.

* **Functionality**: Receives all necessary parameters—such as data paths, departure times, and data slice indexes—via command-line arguments.
* **Routing Engine**: Uses the `r5r` package to build a transport network from OpenStreetMap (OSM) and GTFS data files. It then calculates the shortest-path itineraries for the given OD pairs considering walking and public transit (`"WALK"`, `"TRANSIT"`).
* **HPC Optimization**: Automatically detects the number of CPU cores allocated by Slurm (via `SLURM_CPUS_PER_TASK`) and passes this to `r5r` for efficient multi-threaded computation.
* **Output**: Produces a detailed CSV file for each assigned data chunk, named with a unique batch number to avoid conflicts.

#### Slurm Batch Job (`BatchRunCode_r5r_detiti_main_revised_0_300.txt`)

This Bash script orchestrates the parallel execution of the R script on the Slurm cluster.

* **Massive Parallelism**: Leverages a Slurm job array (`--array=0-300`) to divide the workload into hundreds of small, independent jobs that run in parallel.
* **Data Chunking**: For each job in the array, it calculates a unique slice of the master OD file to process based on its `SLURM_ARRAY_TASK_ID` and passes the chunk indexes to the R script.
* **Robust Job Management**:
    * **Skip Mechanism**: Checks if an output file for a specific task ID already exists. If so, the job is skipped, allowing for easy resumption of partially completed runs.
    * **Fail-Safe Retry Mechanism**: Wraps the `Rscript` command in a `while` loop that attempts to run the job up to 5 times. If the R script fails, it waits 15 seconds and tries again, making the process resilient to transient errors.

### How to Use (Part 1)

#### Prerequisites

* Access to an HPC cluster using the Slurm workload manager.
* An R environment with the required packages (`r5r`, `tidyverse`, `sf`, etc.).
* **Input Data**:
    * A folder containing the Helsinki region's OSM (`.pbf`) and GTFS (`.zip`) files.
    * A master CSV file containing all origin-destination pairs.

#### Important GTFS Data Consideration

⚠️ **Problem**: During this project, an issue was identified where the `detailed_itineraries()` function failed for some OD pairs due to an inconsistency in the official GTFS data (`stop_times.txt` entries were not in chronological order). Full discussion: [r5r Issue #510](https://github.com/ipeaGIT/r5r/issues/510).

✅ **Solution**: The GTFS file used in this repository has been pre-processed to correct these errors. Users who intend to use different GTFS files **must** validate their `stop_times.txt` data to ensure all events are chronological.

#### Configuration & Execution

1.  Open `Batch_Run_r5rDetIti/BatchRunCode_r5r_detiti_main_revised_0_300.txt`.
2.  Modify the `#SBATCH` directives (project account, runtime, memory) and the `--array` range as needed.
3.  Update the paths for your OD data, Map data (OSM/GTFS), and results directory.
4.  Set the routing parameters: departure date (`D_DT`), time (`D_TM`), max walk time (`m_WT`), and max trip duration (`m_TD`).
5.  Submit the job:
    ```bash
    sbatch Batch_Run_r5rDetIti/BatchRunCode_r5r_detiti_main_revised_0_300.txt
    ```

#### Output (Part 1)

This script will generate hundreds of individual CSV files in the specified results directory. Each file contains detailed itineraries for one chunk of the OD data and serves as the input for Part 2.

---

## Part 2: CO₂ Emission Calculation

This second part of the workflow processes the itinerary files generated in Part 1 to calculate CO₂ emissions. The code is located in the `PT_process_Co2data_into_Allas_using_BatchPY` directory.

### Computational Workflow

#### Python Processing Script (`ProcessData_and_SaveToAllas.py`)

This script reads the detailed itinerary files, calculates carbon emissions for each trip segment, and aggregates the results.

* **Functionality**: Processes a single itinerary CSV file. It calculates CO₂ emissions by mapping travel modes (e.g., `WALK`, `BUS`, `RAIL`) to emission factors from the `LCA_gCO2_per_pkm_by_transport_mode.csv` file.
* **Data Aggregation**: Groups results by origin and destination ID, aggregating distances and calculating unique public transport modes.
* **Output**: Saves the processed data, including CO₂ emissions and geometry, into a `.parquet` file. It is also configured to upload the final file to the Allas object storage service.

#### Slurm Batch Job (`batchRun_process_detIti_withCo2_pyfile.txt`)

This Bash script manages the execution of the Python processing script on the Slurm cluster. Unlike the R script job, this script is designed to run as a single, powerful job that processes all itinerary files.

* **Environment Setup**: Loads necessary modules (`geoconda`) and sets the `PATH` to ensure the correct Python environment is used.
* **Execution**: Invokes the `ProcessData_and_SaveToAllas.py` script to begin the data processing and CO₂ calculation workflow.

### How to Use (Part 2)

#### Prerequisites

* An HPC environment with Python and the `geoconda` module available.
* Required Python packages: `pandas`, `h3`, `geopandas`, `shapely`, `boto3`.
* **Input Data**:
    * The folder of detailed itinerary CSV files generated in **Part 1**.
    * The `DATA_CO2/LCA_gCO2_per_pkm_by_transport_mode.csv` file containing emission factors.

#### Configuration & Execution

1.  Open `PT_process_Co2data_into_Allas_using_BatchPY/ProcessData_and_SaveToAllas.py` and modify the input/output directories and any Allas S3 connection details (e.g., bucket name, credentials).
2.  Open `PT_process_Co2data_into_Allas_using_BatchPY/batchRun_process_detIti_withCo2_pyfile.txt`.
3.  Modify the `#SBATCH` directives to match your project account, desired runtime, and memory requirements.
4.  Ensure the path to the Python script in the `python` command is correct.
5.  Submit the job:
    ```bash
    sbatch PT_process_Co2data_into_Allas_using_BatchPY/batchRun_process_detIti_withCo2_pyfile.txt
    ```

### Output (Part 2)

The script will generate processed `.parquet` files containing the itineraries enriched with CO₂ emission data. If configured, these files will also be uploaded to the specified Allas bucket.

## Citation

If you use this code or the resulting data in your research, please cite the following preprint:

> Dey, S., Marín-Flores, C., & Tenkanen, H. (2024). *A Methodological Framework for Microscale Mapping of Carbon Emissions from Daily Multimodal Travel: Application to the Helsinki Metropolitan Area*. Available at SSRN: <https://ssrn.com/abstract=5348581>
