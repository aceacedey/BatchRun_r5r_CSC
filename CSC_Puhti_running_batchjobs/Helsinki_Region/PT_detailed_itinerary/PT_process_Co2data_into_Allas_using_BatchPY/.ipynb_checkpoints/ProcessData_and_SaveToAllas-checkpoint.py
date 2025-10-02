import pandas as pd

Car_share_Hsl = 0.35 ## Car
PT_share_Hsl = 0.23 ## Public transport
Bike_share_Hsl = 0.08  ## Bicycle
Walk_share_Hsl = 0.33  ## Walking
Other_share_Hsl = 0.01 ## Other

ghg_factors = pd.read_csv("Data_CO2/LCA_gCO2_per_pkm_by_transport_mode.csv",index_col=0)
ghg_factors.loc['Total_gCO2'] = ghg_factors.sum(axis=0)
ghg_factors.head()

# Create a function that returns travel mode specific co2 emission factors
def CO2_emission_factors(mode, ghg_factors):
    """
    Convenience function that returns mode specific GHG emission factors (average)
    based on International Transport Forum's LCA Emission estimates.

    Parameters
    ----------

    mode : str
       Name of the travel mode.

    ghg_factors : pd.DataFrame
       A DataFrame containing information about the emissions of different types of vehicles.
      
    """
    # Here, we don't assume walking produces emissions (although it does..due to eating)
    if mode == "WALK":
        co2_value = 0
    elif mode in ["TRAM", "SUBWAY", "RAIL"]:
        co2_value =  ghg_factors.loc['Total_gCO2',['Metro/urban train']].mean()
    elif mode == "BUS":
        co2_value =  ghg_factors.loc['Total_gCO2',['Bus - ICE', 'Bus - HEV', 'Bus - BEV','Bus - BEV (two packs)', 'Bus - FCEV']].mean()
    elif mode == "FERRY":
        co2_value = 36 ## to be change here
    else:
        print(str(mode))
        raise ValueError("Unknown Transit mode found!")
    return co2_value
    
    

import boto3

# create connection s3
s3_client = boto3.client("s3", endpoint_url='https://a3s.fi')

# define bucket name and object name
bucket_name = "Helsinki_PT_detailed_itinerary_csvfiles_r5r"

#object_name = "Helsinki_GTFS_April_2023_Transit/Batch_output_0_300/Helsinki_H3_r5rDI_2024-08-21_B_0.csv"

# Read data to memory before opening with Pandas
#response = s3_client.get_object(Bucket=bucket_name, Key=object_name)

# read
#df = pd.read_csv(response.get("Body"), sep=",")

#df.head()


# create connection s3
s3_resource = boto3.resource('s3', endpoint_url='https://a3s.fi')
# list uploaded files in Bucket
my_bucket = s3_resource.Bucket(bucket_name)

output_bucket_name = "Helsinki_PT_detailed_itinerary_parquet_r5r_wCO2data"
# create a new bucket
s3_resource.create_bucket(Bucket=output_bucket_name)

##s3_resource.Object(output_bucket_name, object_name).upload_file(source_path)


for my_bucket_object in my_bucket.objects.all():
    temp_object_name = my_bucket_object.key
    #print(temp_object_name)
    f = temp_object_name.split("/")[-1]
    
    response = s3_client.get_object(Bucket=bucket_name, Key=temp_object_name)
    
    temp_travel_details= pd.read_csv(response.get("Body"), sep=",")
    temp_travel_details['ghg_emission_factor'] = temp_travel_details.apply(lambda x: CO2_emission_factors(x['mode'], ghg_factors), axis=1)
    temp_travel_details["GHG_emissions_in_grams"] = temp_travel_details["distance"]/1000 * temp_travel_details["ghg_emission_factor"]
    temp_df = pd.DataFrame()
    temp_df["pt_departure_time"] = temp_travel_details.groupby(["from_id", "to_id"])["departure_time"].unique().apply(lambda x:x[0])
    temp_df["pt_dist"] = temp_travel_details.groupby(["from_id", "to_id"])["total_distance"].unique().apply(lambda x:x[0])
    temp_df["pt_time"] = temp_travel_details.groupby(["from_id", "to_id"])["total_duration"].unique().apply(lambda x:x[0])
    temp_df["pt_co2"] = temp_travel_details.groupby(["from_id", "to_id"]).GHG_emissions_in_grams.sum()
    temp_df["pt__trip_seq"] = temp_travel_details.groupby(["from_id", "to_id"]).agg({"mode":pd.Series.to_list})
    temp_df["pt_time_seq"]= temp_travel_details.groupby(["from_id", "to_id"]).agg({"segment_duration":pd.Series.to_list})  #,])#.to_list()
    temp_df["pt_dist_seq"]= temp_travel_details.groupby(["from_id", "to_id"]).agg({"distance":pd.Series.to_list}) 
    temp_df["pt_unique_modes"] = temp_travel_details.groupby(["from_id", "to_id"])["mode"].nunique()
    del_date_str = "_".join(f[0:-4].split("_")[:3]+f[0:-4].split("_")[4:])
    ### put container name and 
    new_fname =  "/Helsinki_PT_detailed_itinerary_parquet_r5r/Helsinki_GTFS_April_2023_Transit_wCO2/"+ del_date_str + "_wCO2.parquet.gzip" #output_bucket_name + "/" +
    temp_df.round(2).reset_index().to_parquet(new_fname,compression='gzip')
    #s3_resource.Object(output_bucket_name, new_fname).upload_file(temp_df.round(2))
    print(f)
   # break