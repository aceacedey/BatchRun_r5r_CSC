# Helsinki Region Public Transport Itinerary Calculation

This repository contains R scripts and Slurm job submission files for large-scale public transport (PT) routing in the Helsinki Region. It computes detailed, multimodal itineraries for ~72 million origin–destination (OD) pairs and is optimized for high-performance computing (HPC) environments managed by Slurm (e.g., CSC).

## Methodological Context

The methodology and scientific context for this routing analysis are detailed in the following preprint:

> Dey, Subhrasankha; Marín-Flores, Cesar; Tenkanen, Henrikki. “A Methodological Framework for Microscale Mapping of Carbon Emissions from Daily Multimodal Travel: Application to the Helsinki Metropolitan Area.” SSRN: <https://ssrn.com/abstract=5348581>

The detailed travel itineraries produced by these scripts are a crucial input for the subsequent modeling of microscale $CO₂$ emissions from daily travel.

## Computational Workflow

The massive computation is managed through a combination of a core R script that performs the routing and a Slurm batch script that orchestrates the parallel execution of thousands of tasks.

### R Routing Script (`rcode_MobiTartu2024.R`)

This is the core computational engine that calculates detailed itineraries for a subset of the OD data.

* **Functionality**: The script receives all necessary parameters—such as data paths, departure times, and data slice indexes—via command-line arguments.
* **Routing Engine**: It uses the `r5r` package to build a transport network from OpenStreetMap (OSM) and GTFS data files. It then calculates the shortest-path itineraries for the given OD pairs considering walking and public transit (`"WALK"`, `"TRANSIT"`).
* **HPC Optimization**: The script is optimized for performance in an HPC environment. It automatically detects the number of CPU cores allocated to the job by Slurm (via the `SLURM_CPUS_PER_TASK` environment variable) and passes this value to `r5r` to enable efficient multi-threaded computation.
* **Output**: The result is a detailed CSV file containing the calculated itineraries for the assigned data chunk, named with a unique batch number to avoid conflicts.

### Slurm Batch Job (`BatchRunCode_r5r_detiti_main_revised_0_300.txt`)

This Bash script is the orchestrator that manages the parallel execution of the R script on the Slurm cluster.

* **Massive Parallelism**: The script leverages a Slurm job array (e.g., `--array=0-300`) to divide the total workload into hundreds of small, independent jobs that can run in parallel.
* **Data Chunking**: For each job in the array, the script calculates a unique slice or "chunk" of the master OD file to process based on its `SLURM_ARRAY_TASK_ID`. It then passes the start and end indexes of this chunk to the R script.
* **Robust Job Management**: The script includes two key features for robust execution:
    * **Skip Mechanism**: Before starting a job, it checks if an output file for that specific task ID already exists. If it does, the job is skipped, saving computational resources and allowing for easy resumption of partially completed runs.
    * **Fail-Safe Retry Mechanism**: The script wraps the `Rscript` command in a `while` loop that attempts to run the job up to 5 times (`MAX_RETRIES=5`). If the R script fails, it waits 15 seconds and tries again, making the process resilient to transient node or system errors.

## How to Use

### Prerequisites

* Access to an HPC cluster using the Slurm workload manager.
* An R environment with the required packages (`r5r`, `tidyverse`, `sf`, etc.) installed.
* **Input Data**:
    * A folder containing the Helsinki region's OSM (`.pbf`) and GTFS (`.zip`) files.
    * A CSV file containing all origin-destination pairs with `id`, `lon`, and `lat` columns.

### Important GTFS Data Consideration

⚠️ During this project, a data-related issue was identified that caused the `detailed_itineraries()` function to fail for certain OD pairs. The issue was investigated and resolved with the help of the `r5r` developers, and the full discussion can be found here: <https://github.com/ipeaGIT/r5r/issues/510>.

* **Problem**: The root cause was an inconsistency in the official GTFS data, where some trips in the `stop_times.txt` file had arrival/departure times that were not in chronological order.
* **Solution**: The GTFS file used in this repository has been pre-processed to correct these chronological errors.
* **Recommendation**: Users who intend to replicate this analysis with newer or different GTFS files **must** perform a validation check on their `stop_times.txt` data. Any trips with non-chronological events should be corrected or removed to ensure the routing analysis runs without errors.

### Configuration

1.  Open the `BatchRunCode_r5r_detiti_main_revised_0_300.txt` script.
2.  Modify the `#SBATCH` directives to match your project account, desired runtime, and memory requirements. Adjust the `--array` range as needed.
3.  Update the paths for `OD`, `MapData`, and `RESULTS` to point to your data and output directories.
4.  Set the routing parameters: departure date (`D_DT`), time (`D_TM`), max walk time (`m_WT`), and max trip duration (`m_TD`).

### Execution

Submit the job to the Slurm scheduler using the `sbatch` command:

```bash
sbatch BatchRunCode_r5r_detiti_main_revised_0_300.txt
```

## Output
The script will generate hundreds of individual CSV files in the specified RESULTS directory. Each file will be named with a unique batch ID and will contain the detailed itineraries for one chunk of the OD data. These files can then be concatenated for full-scale analysis.

## Citation
If you use this code or the resulting data in your research, please cite the following preprint:

Dey, S., Marín-Flores, C., & Tenkanen, H. (2024). A Methodological Framework for Microscale Mapping of Carbon Emissions from Daily Multimodal Travel: Application to the Helsinki Metropolitan Area. Available at SSRN: https://ssrn.com/abstract=5348581
