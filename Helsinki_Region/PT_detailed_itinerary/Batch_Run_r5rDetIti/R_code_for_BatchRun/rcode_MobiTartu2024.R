#!/usr/bin/env 
# Rscript
# accept command line arguments and save them in a list called args
options(echo=TRUE) # if you want see commands in output file
args <- commandArgs(trailingOnly = TRUE) ## 0: ID, 1:MAPDATA, 2:OD, 3: Results Folder
print(args)

Datestr <- args[4] 
Timestr <- args[5]

from_index <- args[6]
to_index <- args[7]

Batch_num <- args[8] ## args[9]

# print task number
##print(paste0('Printing inputs from command line: ', args)

##vignette(package="parallel", topic = "parallel")

library(tidyverse)
library(sf)
library(data.table)
library(ggplot2)
library(conflicted)
library(dplyr)
library(zeallot)

# allocate RAM memory to Java
#options(java.parameters = "-Xmx8G")
options(java.parameters = c("-Xmx8G", "-XX:ParallelGCThreads=4"))

.libPaths(c("/projappl/project_2010418/R_PACKAGES", .libPaths()))

# my r5r R code here

# 1) build transport network, pointing to the path where OSM and GTFS data are stored

library(r5r)

rJava::.jinit()
rJava::.jcall("java.lang.System", "S", "getProperty", "java.version")

#path <- "/Data_helsinki/Helsinki/"
#path <- "/projappl/project_2010418/Batch_run_test/R_code_for_BatchRun/Data/Helsinki_map_data"

path <- args[1] ## 
list.files(path)
#path


##slurm_array_id = as.numeric(args[6])
##slurm_array_id
##print(paste0(as.numeric(args[6])))
#slurm_array_id <- as.data.frame(args[0])


### start recording start time to calculate network building time
#start.time <- Sys.time()
r5r_core <- setup_r5(data_path = path)
#end.time <- Sys.time()
#time.taken <- round(end.time - start.time,2)
#print(time.taken)


# 2) load origin/destination points and set arguments
#pois <- read.csv("/projappl/project_2010418/Batch_run_test/R_code_for_BatchRun/Data/h3_OD_Hexagons_Helsinki_latlon.csv")
#pois_O <- read.csv("/projappl/project_2010418/Batch_run_test/Data_helsinki/Helsinki/loco_Origin_Hex_LatLon_9Res.csv")
#pois_D <- read.csv("/projappl/project_2010418/Batch_run_test/Data_helsinki/Helsinki/loco_Destination_Hex_LatLon_9Res.csv")

pois <- read.csv(args[2])
mode <- c("WALK", "TRANSIT")
max_walk_time <- as.integer(args[9])##as.integer(x)  30   # minutes
max_trip_duration <- as.integer(args[10]) ##120 # minutes
departure_datetime_string <- paste(Datestr,Timestr,sep =" ")
departure_datetime <- as.POSIXct(departure_datetime_string,format = "%d-%m-%Y %H:%M:%S")

outFolder <- args[3]
outFile <- paste(outFolder, "/Helsinki_H3_r5rDI_",Sys.Date(),"_B_",Batch_num,".csv",sep ="")
#outFile 
##############
origin_df =  pois[from_index:to_index,]
dest_df = pois[-c(from_index:to_index),]


# --- OPTIMIZATION: Set threads based on Slurm allocation ---
# Read the number of cores Slurm has given this job
n_threads <- as.integer(Sys.getenv("SLURM_CPUS_PER_TASK"))

# Provide a fallback in case the script is run outside of a Slurm job
if (is.na(n_threads)) {
  n_threads <- 10 # Default to 2 threads if not on Slurm
}

print(paste("ROUTING: Using", n_threads, "threads for calculation."))
# -------------------------------------------------------------


#  get detailed info on multiple alternative routes
### start recording start time
start.time <- Sys.time()
print("Starting Detailed Itineraries calculation using r5r, Now !")
det <- detailed_itineraries(r5r_core = r5r_core,
                            origins = origin_df,#[37, ],
                            destinations = dest_df,#[20, ],
                            mode = mode,
                            departure_datetime = departure_datetime,
                            max_walk_time = max_walk_time,
                            max_trip_duration = max_trip_duration,
                            shortest_path = TRUE,
                            drop_geometry = TRUE,
                            time_window = 60,
                            all_to_all = TRUE,
                            n_threads = n_threads  # <-- Pass the number of threads to r5r)
                            )

end.time <- Sys.time()
time.taken <- round(end.time - start.time,2)
print(time.taken)
#write.csv(det, "/projappl/project_2010418/Batch_run_test/R_code_for_BatchRun/Batch_output/Helsinki_Hex_DetIte_r5r_Batch.csv", row.names=FALSE)
write.csv(det, outFile, row.names=FALSE)
print("Job complete.")