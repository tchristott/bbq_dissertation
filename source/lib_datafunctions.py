# Library of functions to process transfer data from liquid handlers and raw data from plate readers.
# Functions to readout data from raw data files from devices are in separate library.

import os

# Import libraries
import numpy as np
import pandas as pd
from multiprocessing import Pool
import peakutils as pu
import scipy.signal as scsi
import copy as copy

# Import my own libraries
import lib_platefunctions as pf
import lib_resultreadouts as ro
import lib_fittingfunctions as ff
import lib_messageboxes as msg
import lib_excelfunctions as ef

########################################################################################################
##                                                                                                    ##
##    ######  #####    ####   ##  ##   #####  ######  ######  #####     ######  ##  ##      ######    ##
##      ##    ##  ##  ##  ##  ### ##  ##      ##      ##      ##  ##    ##      ##  ##      ##        ##
##      ##    #####   ######  ######   ####   ####    ####    #####     ####    ##  ##      ####      ##
##      ##    ##  ##  ##  ##  ## ###      ##  ##      ##      ##  ##    ##      ##  ##      ##        ##
##      ##    ##  ##  ##  ##  ##  ##  #####   ##      ######  ##  ##    ##      ##  ######  ######    ##
##                                                                                                    ##
########################################################################################################

def parse_transfer(transfer_rules, transfer_file):
    """
    Takes transfer file parsing rules (as pandas dataframe) and
    file path of transfer file to parse (as string) and builds a
    data frame that captures the layout of each plate in the
    transfer file.
    
    Returns pandas dataframe "dfr_Layout" and boolean value for success of parsing.
    """

    extension = transfer_rules["Extension"]
    engine = transfer_rules["Engine"]
    worksheet = transfer_rules["Worksheet"]

    parsed_transfer = read_transfer(transfer_file,
                                    extension = extension,
                                    engine = engine,
                                    header = None,
                                    worksheet = worksheet)
    if parsed_transfer is None:
        return pd.DataFrame(), pd.DataFrame(), False

    # Verify whether we're dealing with a valid transfer file:
    if transfer_rules["UseVerificationKeyword"] == True:
        bool_Verified = False
        for idx in parsed_transfer.index:
            if parsed_transfer.loc[idx, transfer_rules["VerificationKeywordColumn"]] == transfer_rules["VerificationKeyword"]:
                bool_Verified = True
                break
        if bool_Verified == False:
            msg.warn_not_transferfile()
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), pd.DataFrame(), False
    
    # Default stop row as shape[0] in case the end of dataframe is end of entries
    int_StopRow = parsed_transfer.shape[0]

    # Find start and stop of transfer entries
    if not parsed_transfer.shape[0] == 0:
        # 1. Find start:
        if transfer_rules["UseStartKeyword"] == True:
            for row in range(parsed_transfer.shape[0]):
                int_StartCol = int(transfer_rules["StartKeywordColumn"])
                if parsed_transfer.iloc[row,int_StartCol] == transfer_rules["StartKeyword"]:
                    int_StartRow = row
                    break
        elif transfer_rules["UseStartCoordinates"] == True:
            int_StartRow = transfer_rules["StartCoordinates"][0]
            int_StartCol = transfer_rules["StartCoordinates"][1]
        else:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), pd.DataFrame(), False
        
        # 2. Now that we know wheret to start, read file again. Some files might be a bit borked,
        # so the correct number of columns might not be caught the first time.
        parsed_transfer = read_transfer(transfer_file,
                                        extension = extension,
                                        engine = engine,
                                        header = int_StartRow,
                                        worksheet = worksheet)
        if parsed_transfer is None:
            return pd.DataFrame(), pd.DataFrame(), False
        
        # 3. Find stop:
        if transfer_rules["UseStopKeyword"] == True:
            for row in range(int_StartRow+1, parsed_transfer.shape[0]):
                int_StopCol = int(transfer_rules["StopKeywordColumn"])
                if parsed_transfer.iloc[row,int_StopCol] == transfer_rules["StopKeyword"]:
                    int_StopRow = row-1
                    break
        elif transfer_rules["UseStopCoordinates"] == True:
            int_StopRow = transfer_rules["StopCoordinates"][0] - int_StartRow
            int_StopCol = transfer_rules["StopCoordinates"][1] - int_StartCol
        elif transfer_rules["UseStopEmptyLine"] == True:
            int_StopCol = parsed_transfer.shape[1]
            for row in range(int_StartRow+1, parsed_transfer.shape[0]):
                if pd.isna(parsed_transfer.iloc[row,0]) == True:
                    int_StopRow = row-1
                    break
        else:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), pd.DataFrame(), False
        
        # Ensure we don't end up with a one-column dataframe -> Default stop column to last column of dataframe
        if int_StopCol == int_StartCol:
            int_StopCol = parsed_transfer.shape[1]

        #parsed_transfer = parsed_transfer.iloc[int_StartRow+1:int_StopRow,int_StartCol:int_StopCol].rename(columns=col_rename).reset_index()
        parsed_transfer = parsed_transfer.iloc[int_StartRow+1:int_StopRow,int_StartCol:int_StopCol].reset_index(drop=True)
        
        # Reduce columns
        reduced_parsed = []
        reduced_layout = []
        for col in transfer_rules["TransferFileColumns"].keys():
            if not transfer_rules["TransferFileColumns"][col]["Mapped"] == "":
                reduced_parsed.append(transfer_rules["TransferFileColumns"][col]["Mapped"])
                reduced_layout.append(transfer_rules["TransferFileColumns"][col]["Name"])
        # Make column names compliant with standard naming scheme and remove spaces
        parsed_transfer = parsed_transfer[reduced_parsed].rename(columns=dict(zip(reduced_parsed,reduced_layout)))
        parsed_transfer.columns = parsed_transfer.columns.str.replace(" ", "")
        # Check whether "Sample Name" or "Sample ID" or both are used. If both are used, "Sample ID" will be given prefernce
        # for simplicity. This is used to differentiate between sample and solvent transfers
        if "Sample ID" in reduced_layout:
            sample_column = "SampleID"
        elif "Sample Name" in reduced_layout:
            sample_column = "SampleName"
        else:
            # In this case, there is no point in using this transfer file!
            msg.warn_missing_column("Sample Name or Sample ID")
            return pd.DataFrame(), pd.DataFrame(), False
        # If we do want to catch solvent-only transfers, make sure that column is in the layout dataframe, even if it
        # was not assigned (might not be explicitly labelled in transfer files):
        if transfer_rules["CatchSolventOnlyTransfers"] == True:
            if not "SolventTransferVolume" in reduced_layout:
                reduced_layout.append("SolventTransferVolume")
                solvent_column = "SampleTransferVolume"
            else:
                solvent_column = "SolventTransferVolume"
    
        # Create the actual layout dataframe to return
        # Get the list of destination plates:
        lst_DestinationPlates = parsed_transfer["DestinationPlateName"].dropna().unique()
        reduced_layout = [col.replace(" ","") for col in reduced_layout]
        dfr_Layout = pd.DataFrame(index=lst_DestinationPlates,columns=reduced_layout)
        # Get columns and rows based on plate format
        int_PlateRows = pf.plate_rows(transfer_rules["DestinationPlateFormat"])
        int_PlateColumns = pf.plate_columns(transfer_rules["DestinationPlateFormat"])

        lst_PlateRows = []
        for row in range(int_PlateRows):
            lst_PlateRows.append(chr(row+65))
        lst_PlateColumns = [*range(1,int_PlateColumns+1)] # asterisk is unpacking operator -> turns range into list!
        # Add sub-dataframes:
        for plate in dfr_Layout.index:
            for column in dfr_Layout.columns:
                dfr_Layout.at[plate,column] = pd.DataFrame(index=lst_PlateRows,columns=lst_PlateColumns)

        # Populate layot dataframe:
        # Go through each row in parsed transfer file:
        for row in parsed_transfer.index:
            # Get coordinates of destination well
            well = pf.split_coordinates(parsed_transfer.loc[row,"DestinationWell"])
            # Find destination plate
            plate = parsed_transfer.loc[row,"DestinationPlateName"]
            # Only use all columns if there is a sample ID associated:
            sample_id = parsed_transfer.loc[row, sample_column]
            if pd.isna(sample_id) == False:
                for col in parsed_transfer.columns:
                    dfr_Layout.loc[plate,col].loc[well[0],well[1]] = parsed_transfer.loc[row, col]
            # If there is no sample associated, it could either be solvent only or backfill:
            elif "SolventTransferVolume" in reduced_layout:
                dfr_Layout.loc[plate,"SolventTransferVolume"].loc[well[0],well[1]] = parsed_transfer.loc[row, solvent_column]

        return parsed_transfer, dfr_Layout, True
    
    else:

        return pd.DataFrame(), pd.DataFrame(), False
    
def read_transfer(transfer_file, extension, engine, header = None, worksheet = None):

    """
    Reads the transfer file into a dataframe.

    Arguments:

    transfer_file -> str. File path
    extension -> str. File extensions
    engine -> str. Engine to use when parsing
    header -> int or None. header row for dataframe.

    Returns pandas dataframe
    """
    if extension == "csv" or extension == "txt":
        try:
            return pd.read_csv(transfer_file,
                               sep=None,
                               header=header,
                               index_col=False,
                               engine=engine,
                               skip_blank_lines=False)
        except:
            # Couldn't parse, return empty dataframe and no success
            return None
    elif "xls" in extension:
        try:
            return pd.read_excel(transfer_file,
                                 sheet_name=worksheet,
                                 header=header,
                                 index_col=None,
                                 engine=engine)
        except:
            # Couldn't parse, return empty dataframe and no success
            return None

def create_transfer_frame(str_TransferFile, transfer_rules):
    """
    Reads transfer file into data frame and trims it down to neccessary lines
    
    !NOTE!: If the transfer file comes straight from the Echo, the delimiting will end after each line is over. What would be empty cells
    is not delimited. Example:
    First line is: Run ID,3360
    To capture all columns, the first line should be: Run ID,3360,,,,,,,,,,,,,,,,,,,
    This will trip up pd.read_csv, so we have to find the header row first byt loading only the first column and searching for the keyword.
    """
    # Open transfer file and find header row and exceptions (if any)
    engine = transfer_rules["Engine"]


    # Find header row/start of entries
    if transfer_rules["UseStartKeyword"] == True:
        dfr_Temp = ef.direct_read
        dfr_Temp = pd.read_csv(str_TransferFile, sep=",", usecols=[0], header=None, index_col=False, engine=engine)
        kw_start = transfer_rules["StartKeyword"]
        int_HeaderRow = dfr_Temp.index[dfr_Temp[0] == kw_start].tolist()
        # Check whether the start keyword has been found:
        if not int_HeaderRow:
            return None
        # We get a list, so we have to use the first instance:
        int_HeaderRow = int_HeaderRow[0]
        # Adjust header row for offset:
        # int_HeaderRow += 1
        # Used to be that the key word was "Details" and the header row started below.
    elif transfer_rules["UseStartCoordinates"] == True:
        int_HeaderRow = transfer_rules["UseStartCoordinates"][0]
    
    # Create exceptions dataframe
    if transfer_rules["CatchExceptions"] == True:
        kw_except = transfer_rules["ExceptionsKeyword"]
        int_Exceptions = dfr_Temp.index[dfr_Temp[0] == kw_except].tolist()
        if int_Exceptions:
            int_Exceptions = int_Exceptions[0] + 1
            int_Length = int_HeaderRow[0] - int_Exceptions - 2
            dfr_Exceptions = pd.read_csv(str_TransferFile, sep=",", header=int_Exceptions, index_col=False, engine="python")
            dfr_Exceptions = dfr_Exceptions.iloc[0:int_Length]
            dfr_Exceptions.columns = dfr_Exceptions.columns.str.replace(" ", "")
            dfr_Exceptions = dfr_Exceptions[["DestinationPlateName","DestinationWell"]]
        else:
            dfr_Exceptions = pd.DataFrame(columns=["DestinationPlateName","DestinationWell"])
    else:
        dfr_Exceptions = pd.DataFrame(columns=["DestinationPlateName","DestinationWell"])
    # Now open transfer file properly:
    dfr_TransferFile = pd.read_csv(str_TransferFile, sep=",", header=int_HeaderRow, index_col=False, engine="python")
    # Clean up headers
    
    headers = []
    mapped = []    
    transfer_columns = transfer_rules["TransferFileColumns"]
    for key in transfer_columns.keys():
        if not transfer_columns[key]["Mapped"] == "":
            headers.append(transfer_columns[key]["Name"])
            mapped.append(transfer_columns[key]["Mapped"])
    # Create list for sorting -> check which optional column header is present,
    # only use the first one if both
    sort_by = []
    if "Destination Plate Name" in headers:
        sort_by.append("Destination Plate Name")
    elif "Destination Plate Barcode" in headers:
        sort_by.append("Destination Plate Barcode")
    if "Sample ID"  in headers:
        sort_by.append("Sample ID")
    elif "Sample Name"  in headers:
        sort_by.append("Sample Name")
    sort_by.append("Destination Concentration")
    dic_renaming = dict(zip(headers, mapped))
    # Keep only relevant columns -> This will drop the first two columns that hold the appendix
    # data (Instrument name, serial number, etc)
    # Sort by DestinationConcentration -> Ensures that all points will be in the correct order
    # and there are no weird gaps when drawing the fit
    dfr_TransferFile = dfr_TransferFile[mapped].rename(columns=dic_renaming).sort_values(sort_by,
        ascending=[True,True,False])
    # Rename Destination Plate Name/Barcode column simply to "Destination". Use first element of 
    # sort_by list, since this has already undergone the check to see whether one or both is present:
    dfr_TransferFile = dfr_TransferFile.rename(columns={sort_by[0]:"Destination"})
    # Remove spaces from all column title (this allows us to referring to columns by using the
    # syntax dataframename.columnname)
    dfr_TransferFile.columns = dfr_TransferFile.columns.str.replace(" ", "")
    # Drop rows that are empty -> This will be where TransferVolume is "NaN"
    if "Sample Transfer Volume" in headers:
        dfr_TransferFile = dfr_TransferFile.dropna(subset=["TransferVolume"])
    # Make wells sortable -> Relegated to a later point
    return dfr_TransferFile, dfr_Exceptions

def get_destination_plates(transfer):
    # Creates and returns an array or dataframe with the Destination, DestinationPlateBarcode and number of wells
    destinations = transfer[["Destination", "DestinationPlateBarcode",
        "DestinationPlateType"]].sort_values(by=["Destination"]).drop_duplicates(subset=["Destination"],
        keep="first", ignore_index=True)
    # Get plate type
    destinations.DestinationPlateType = destinations.DestinationPlateType.apply(pf.plate_type_string)
    # Return result
    return destinations

def get_samples(processed,plate_name,wells):
    """
    Get sample locations and concentrations from processed transfer file and write into data frame/
    first column (after index) sample ID
    second column: list lists of locations
    third column: list of concentrations
    """
    # Get list of samples, drop duplicates, drop emtpies, reset index
    processed = processed[processed["Destination"]==plate_name]
    dfr_Samples = processed[["Destination","SampleID","SourceConcentration"]].drop_duplicates(subset=["SampleID"], keep="first",
        ignore_index=True).dropna().reset_index(drop=True)
    dfr_Samples = dfr_Samples.drop(dfr_Samples.index[dfr_Samples["SampleID"]=="Control"]).reset_index(drop=True)
    dfr_Samples.insert(2,"Locations","")
    dfr_Samples.insert(3,"Concentrations","")
    dfr_Samples.insert(4,"TransferVolumes","")
    dfr_Samples.insert(5,"Wells","")
    # Convert wells
    indices = processed.DestinationWell.apply(lambda x: pf.sortable_well(x, wells)).apply(lambda x: pf.well_to_index(x, wells)).tolist()
    lst_Wells = processed.DestinationWell.apply(lambda x: pf.sortable_well(x, wells)).tolist()
    processed.insert(3,"WellsIndex",indices) # Column position three is chosen randomly.
    processed.insert(5,"Wells",lst_Wells)
    # Create columns for Locations and Concentration, write placeholders, change data type to enable holding lists
    for smpl in dfr_Samples.index:
        current = processed[processed.SampleID == dfr_Samples.loc[smpl, "SampleID"]]

        # Pull list of concentrations for current sample
        lst_cnc = current.DestinationConcentration.reset_index(drop=True)
        lst_loc = current.WellsIndex.reset_index(drop=True)
        lst_vol = current.TransferVolume.reset_index(drop=True)
        #lstRaw = dfr_Processed.loc[i, "RawData"]
        # Create list of lists:
        lstlst_cnc = [] # list of lists for concentrations
        lstlst_loc = [] # list of lists for locations
        lstlst_vol = []
        # Go through list of concentrations
        for conc in range(len(lst_cnc)):
            lst_cnc_temp = []
            lst_loc_temp = []
            lst_vol_temp = []
            # Check to only use unique concentrations
            if lst_cnc[conc] != "found":
                # assign current conc/loc to temporary lists
                lst_cnc_temp = lst_cnc[conc] # simple list
                lst_loc_temp = [lst_loc[conc]] # list of lists, one concentration can be in many locations
                lst_vol_temp = [lst_vol[conc]]
                for k in range(conc+1,len(lst_cnc)):
                    if lst_cnc[conc] == lst_cnc[k]:
                        lst_cnc[k] = "found" # flag concentrations that are not unique
                        lst_loc_temp.append(lst_loc[k])
                        lst_vol_temp.append(lst_vol[k])
                # append temporary list to list of lists
                lstlst_cnc.append(lst_cnc_temp)
                lstlst_loc.append(lst_loc_temp)
                lstlst_vol.append(lst_vol_temp)

        dfr_Samples.at[smpl,"Concentrations"] = lstlst_cnc
        dfr_Samples.at[smpl,"Locations"] = lstlst_loc
        dfr_Samples.at[smpl,"TransferVolumes"] = lstlst_vol
        dfr_Samples.at[smpl,"Wells"] = current.Wells.reset_index(drop=True)

    return dfr_Samples

def get_samples_lightcycler(current_plate,raw_data,wells):
    plate_name = []
    sample_id = []
    source_conc = []
    locations = []
    conc = []
    transfer = []
    for well in raw_data.index:
        plate_name.append(current_plate)
        sample_id.append(raw_data.loc[well,"Name"])
        source_conc.append(["NA"]) # List with one element!
        locations.append([pf.well_to_index(raw_data.loc[well,"Well"],wells)]) # List with one element!
        conc.append(["NA"]) # List with one element!
        transfer.append(["NA"])
    return pd.DataFrame(data={"Destination":plate_name,
                              "SampleID":sample_id,
                              "SourceConcentration":source_conc,
                              "Locations":locations,
                              "Concentrations":conc,
                              "TransferVolumes":transfer})

def get_samples_wellonly(current_plate,raw_data,wells):
    plate_name = []
    sample_id = []
    source_conc = []
    locations = []
    conc = []
    transfer = []
    for well in raw_data.index:
        plate_name.append(current_plate)
        sample_id.append(raw_data.loc[well,"Well"])
        source_conc.append(["NA"]) # List with one element!
        locations.append([pf.well_to_index(raw_data.loc[well,"Well"],wells)]) # List with one element!
        conc.append(["NA"]) # List with one element!
        transfer.append(["NA"])
    return pd.DataFrame(data={"Destination":plate_name,
                              "SampleID":sample_id,
                              "SourceConcentration":source_conc,
                              "Locations":locations,
                              "Concentrations":conc,
                              "TransferVolumes":transfer})

def get_references(layout,datafile,raw_data):
    """
    Extracts locations of reference wells (control compound, no-addition and solvent-only wells) and calculates mean, standard error,
    standard deviation, median and median absolute deviation for each.
    """

    # Create a dataframe that will eventually hold Five columns: Well, Reading, Control, Transfer, Buffer, Solvent.
    raw_data = raw_data.rename(columns={datafile:"Reading"})

    # Calculate parameters
    ref_wells = layout[(layout["WellType"] == "r")].index.to_list()
    if len(ref_wells) > 0:
        ref_values = raw_data.loc[ref_wells,"Reading"].to_list()
        ref_mean = np.nanmean(ref_values)
        ref_STDEV = np.std(ref_values)
        ref_SEM = ref_STDEV / np.sqrt(np.size(ref_values))
        ref_median = np.nanmedian(ref_values)
        ref_MAD = mad(ref_values)
    else:
        ref_mean = np.nan
        ref_STDEV = np.nan
        ref_SEM = np.nan
        ref_median = np.nan
        ref_MAD = np.nan

    buf_wells = layout[(layout["WellType"] == "b")].index.to_list()
    if len(buf_wells) > 0:
        buf_values = raw_data.loc[buf_wells,"Reading"].to_list()
        buf_mean = np.nanmean(buf_values)
        buf_STDEV = np.std(buf_values)
        buf_SEM = buf_STDEV / np.sqrt(np.size(buf_values))
        buf_median = np.nanmedian(buf_values)
        buf_MAD = mad(buf_values)
    else:
        buf_mean = np.nan
        buf_STDEV = np.nan
        buf_SEM = np.nan
        buf_median = np.nan
        buf_MAD = np.nan

    ctr_wells = layout[(layout["WellType"] == "c")].index.to_list()
    if len(ctr_wells) > 0:
        ctr_values = raw_data.loc[ctr_wells,"Reading"].to_list()
        ctr_mean = np.nanmean(ctr_values)
        ctr_STDEV = np.std(ctr_values)
        ctr_SEM = ctr_STDEV / np.sqrt(np.size(ctr_values))
        ctr_median = np.nanmedian(ctr_values)
        ctr_MAD = mad(ctr_values)
    else:
        ctr_mean = np.nan
        ctr_STDEV = np.nan
        ctr_SEM = np.nan
        ctr_median = np.nan
        ctr_MAD = np.nan

    # If there is a control compound, give out a ZPrime. Choose Solvent or Buffer
    if not pd.isna(ctr_mean):
        if not pd.isna(ref_mean):
            flt_ZPrime_Mean = 1 - (3 * (ref_STDEV + ctr_STDEV) / abs(ref_mean - ctr_mean))
            flt_ZPrime_Median = 1 - (3 * (ref_MAD + ctr_MAD) / abs(ref_median - ctr_median))
        else:
            flt_ZPrime_Mean = 1 - (3 * (buf_STDEV + ctr_STDEV) / abs(buf_mean - ctr_mean))
            flt_ZPrime_Median = 1 - (3 * (buf_MAD + ctr_MAD) / abs(buf_median - ctr_median))
    else:
        flt_ZPrime_Mean = np.nan
        flt_ZPrime_Median = np.nan
    
    references = pd.DataFrame(columns=[0],index=["SolventMean","SolventMedian","SolventSEM","SolventSTDEV","SolventMAD",
        "BufferMean","BufferMedian","BufferSEM","BufferSTDEV","BufferMAD",
        "ControlMean","ControlMedian","ControlSEM","ControlSTDEV","ControlMAD",
        "ZPrimeMean","ZPrimeMedian"])
    references.at["SolventMean",0] = ref_mean
    references.at["SolventMedian",0] = ref_median
    references.at["SolventSEM",0] = ref_SEM
    references.at["SolventSTDEV",0] = ref_STDEV
    references.at["SolventMAD",0] = ref_MAD

    references.at["ControlMean",0] = ctr_mean
    references.at["ControlMedian",0] = ctr_median
    references.at["ControlSEM",0] = ctr_SEM
    references.at["ControlSTDEV",0] = ctr_STDEV
    references.at["ControlMAD",0] = ctr_MAD

    references.at["BufferMean",0] = buf_mean
    references.at["BufferMedian",0] = buf_median
    references.at["BufferSEM",0] = buf_SEM
    references.at["BufferSTDEV",0] = buf_STDEV
    references.at["BufferMAD",0] = buf_MAD

    references.at["ZPrimeMean",0] = flt_ZPrime_Mean
    references.at["ZPrimeMedian",0] = flt_ZPrime_Median

    return references

def get_references_flex(processed,exceptions,destination,str_RawDataFile,raw_data):
    """
    Extracts locations of reference wells (control compound, no-addition and solvent-only wells) and calculates mean, standard error,
    standard deviation, median and median absolute deviation for each.
    """
    wells = raw_data.shape[0]
    # Extracts location of controls and references from processed transfer file
    # Rename some columns to make things easier, get only columns and rows we need
    processed = processed[(processed["Destination"]==destination)]
    processed = processed[["Destination","SampleID","SampleName","DestinationWell"]].rename(columns={"DestinationWell":"Well"})
    exceptions = exceptions[(exceptions["Destination"]==destination)]
    # Adjust wells to sortable wells
    processed["Well"].apply(lambda x: pf.sortable_well(x, wells))
    raw_data["Well"].apply(lambda x: pf.sortable_well(x, wells))
    exceptions["DestinationWell"].apply(lambda x: pf.sortable_well(x, wells))
    # Create a dataframe that will eventually hold Five columns: Well, Reading, Control, Transfer, Buffer, Solvent.
    dfr_References = raw_data.rename(columns={str_RawDataFile:"Reading"})
    # Get list of exceptions and transfers -> make them sortable later for efficiency!
    lst_Exceptions = exceptions["DestinationWell"].tolist()
    lst_TransferWells = processed["Well"].unique()
    # Get control values (e.g. 100% inhibition)
    controls = processed[(processed["SampleName"] == "Control")]
    controls = controls[["Well","SampleName"]].rename(columns={"SampleName":"Control"})
    # Merge controls into reference dataframe
    dfr_References = pd.merge(dfr_References, controls, on=["Well"], how="left")
    # get all "buffer" wells, e.g. w/o any addition into them from transfer file
    dfr_Transfers = pd.DataFrame(list(zip(lst_TransferWells,lst_TransferWells)),columns=["Well","Transfer"])
    # Merge all transfers into reference dataframe
    dfr_References = pd.merge(dfr_References, dfr_Transfers, on=["Well"], how="left")
    # no transfer at all means buffer
    for i in dfr_References.index:
        if pd.isna(dfr_References.loc[i,"Transfer"]) == True and pd.isna(dfr_References.loc[i,"Reading"]) == False:
            dfr_References.loc[i,"Buffer"] = "YES"
        else:
            dfr_References.loc[i,"Buffer"] = np.nan
    # Solvent wells have a transfer but no sample
    #dfr_Solvent = processed[["SampleID","Well"]]
    dfr_Samples = processed[(processed["SampleID"].isnull() == False)]
    # Get entries in transfer file with no sample -> Solvent transfer. Could be backfills!
    dfr_Solvent = processed[(processed["SampleID"].isnull() == True)].reset_index(drop=True)
    # Figure out which Solvent transfers are not backfills and drop these from the dataframe
    lst_Backfills = []
    for well in dfr_Solvent.index:
        if dfr_Solvent.loc[well,"Well"] in dfr_Samples.values:
            lst_Backfills.append(well)
    dfr_Solvent = dfr_Solvent[["Well"]].drop(lst_Backfills).reset_index(drop=True)
    if dfr_Solvent.shape[0] > 0:
        dfr_Solvent.loc[dfr_Solvent["Well"].isnull() == False,"Solvent"] = "YES"
        # Merge to dfr_References
        dfr_References = pd.merge(dfr_References, dfr_Solvent, on=["Well"], how="left")
    else:
        dfr_References["Solvent"] = [np.nan] * dfr_References.shape[0]
    # Write readings into appropriate columns
    lst_Buffer = []
    for ref in dfr_References.index:
        if not dfr_References.loc[ref,"Well"] in lst_Exceptions:
            # Write control value, delete Solvent value if there is a control
            if dfr_References.loc[ref,"Control"] == "Control":
                dfr_References.loc[ref,"Control"] = dfr_References.loc[ref,"Reading"]
                dfr_References.loc[ref,"Solvent"] = np.nan
                dfr_References.loc[ref,"Buffer"] = np.nan
            # Write Solvent value. Must not be a control, must have transfer. SampleID = Nan has already been tested
            elif dfr_References.loc[ref,"Control"] != "Control" and dfr_References.loc[ref,"Solvent"] == "YES":
                dfr_References.loc[ref,"Solvent"] = dfr_References.loc[ref,"Reading"]
                dfr_References.loc[ref,"Control"] = np.nan
                dfr_References.loc[ref,"Buffer"] = np.nan
                        # Write buffer value
            elif dfr_References.loc[ref,"Buffer"] == "YES":
                    lst_Buffer.append(dfr_References.loc[ref,"Well"])
                    dfr_References.loc[ref,"Buffer"] = dfr_References.loc[ref,"Reading"]
        else:
            dfr_References.loc[ref,"Control"] = np.nan
            dfr_References.loc[ref,"Solvent"] = np.nan
            dfr_References.loc[ref,"Buffer"] = np.nan
    # Calculate parameters:
    flt_Solvent_Mean, flt_Solvent_SEM, flt_Solvent_STDEV = dfr_References["Solvent"].mean(), dfr_References["Solvent"].sem(), dfr_References["Solvent"].std()
    flt_Solvent_Median, flt_Solvent_MAD = dfr_References["Solvent"].median(), mad(dfr_References["Solvent"].to_list())
    flt_Control_Mean, flt_Control_SEM, flt_Control_STDEV = dfr_References["Control"].mean(), dfr_References["Control"].sem(), dfr_References["Control"].std()
    flt_Control_Median, flt_Control_MAD = dfr_References["Control"].median(), mad(dfr_References["Control"].to_list())
    flt_Buffer_Mean, flt_Buffer_SEM, flt_Buffer_STDEV = dfr_References["Buffer"].mean(), dfr_References["Buffer"].sem(), dfr_References["Buffer"].std()
    flt_Buffer_Median, flt_Buffer_MAD = dfr_References["Buffer"].median(), mad(dfr_References["Buffer"].to_list())
    # If there is a control compound, give out a ZPrime. Choose Solvent or Buffer
    if pd.isna(flt_Control_Mean) == False:
        if pd.isna(flt_Solvent_Mean) == False:
            flt_ZPrime_Mean = 1 - (3 * (flt_Solvent_STDEV + flt_Control_STDEV) / abs(flt_Solvent_Mean - flt_Control_Mean))
            flt_ZPrime_Median = 1 - (3 * (flt_Solvent_MAD + flt_Control_MAD) / abs(flt_Solvent_Median - flt_Control_Median))
        else:
            flt_ZPrime_Mean = 1 - (3 * (flt_Buffer_STDEV + flt_Control_STDEV) / abs(flt_Buffer_Mean - flt_Control_Mean))
            flt_ZPrime_Median = 1 - (3 * (flt_Buffer_MAD + flt_Control_MAD) / abs(flt_Buffer_Median - flt_Control_Median))
    else:
        flt_ZPrime_Mean = np.nan
        flt_ZPrime_Median = np.nan
    
    # Create dfr_Layout
    # Create empty lists
    lst_Welltype = ["s"] * wells
    lst_ProteinNumerical = [""] * wells
    lst_ProteinID = [""] * wells
    lst_ProteinConcentration = [""] * wells
    lst_ControlNumerical = [""] * wells
    lst_ControlID = [""] * wells
    lst_ControlConcentration = [""] * wells
    lst_ZPrime = [""] * wells
    lst_ReferenceNumerical = [""] * wells
    lst_ReferenceID = [""] * wells
    lst_ReferenceConcentration = [""] * wells
    lst_SampleNumerical = [""] * wells
    lst_SampleID = [""] * wells
    lst_SampleConcentration = [""] * wells

    # write relevant things into lists
    for i in range(wells):
        if pd.isna(dfr_References.loc[i,"Control"]) == False:
            lst_ControlID[i] = "Control 1"
            lst_ControlNumerical[i] = "1"
            lst_Welltype[i] = "c"
        elif pd.isna(dfr_References.loc[i,"Solvent"]) == False:
            lst_ReferenceID[i] = "Solvent"
            lst_ReferenceNumerical[i] = "1"
            lst_Welltype[i] = "r"
        elif pd.isna(dfr_References.loc[i,"Buffer"]) == False:
            lst_ReferenceID[i] = "Buffer"
            lst_ReferenceNumerical[i] = "2"
            lst_Welltype[i] = "r"

    # Write it all to dataframe
    dfr_Layout = pd.DataFrame(index=range(wells),
                                          data = {"WellType":lst_Welltype,
                                                  "ProteinNumerical":lst_ProteinNumerical,
                                                  "ProteinID":lst_ProteinID,
                                                  "ProteinConcentration":lst_ProteinConcentration,
                                                  "ControlNumerical":lst_ControlNumerical,
                                                  "ControlID":lst_ControlID,
                                                  "ControlConcentration":lst_ControlConcentration,
                                                  "ZPrime":lst_ZPrime,
                                                  "ReferenceNumerical":lst_ReferenceNumerical,
                                                  "ReferenceID":lst_ReferenceID,
                                                  "ReferenceConcentration":lst_ReferenceConcentration,
                                                  "SampleNumerical":lst_SampleNumerical,
                                                  "SampleID":lst_SampleID,
                                                  "SampleConcentration":lst_SampleConcentration})

    dfr_References_Return = pd.DataFrame(columns=[0],index=["SolventMean","SolventMedian","SolventSEM","SolventSTDEV","SolventMAD",
        "BufferMean","BufferMedian","BufferSEM","BufferSTDEV","BufferMAD",
        "ControlMean","ControlMedian","ControlSEM","ControlSTDEV","ControlMAD",
        "ZPrimeMean","ZPrimeMedian"])
    dfr_References_Return.at["SolventMean",0] = flt_Solvent_Mean
    dfr_References_Return.at["SolventMedian",0] = flt_Solvent_Median
    dfr_References_Return.at["SolventSEM",0] = flt_Solvent_SEM
    dfr_References_Return.at["SolventSTDEV",0] = flt_Solvent_STDEV
    dfr_References_Return.at["SolventMAD",0] = flt_Solvent_MAD

    dfr_References_Return.at["ControlMean",0] = flt_Control_Mean
    dfr_References_Return.at["ControlMedian",0] = flt_Control_Median
    dfr_References_Return.at["ControlSEM",0] = flt_Control_SEM
    dfr_References_Return.at["ControlSTDEV",0] = flt_Control_STDEV
    dfr_References_Return.at["ControlMAD",0] = flt_Control_MAD

    dfr_References_Return.at["BufferMean",0] = flt_Buffer_Mean
    dfr_References_Return.at["BufferMedian",0] = flt_Buffer_Median
    dfr_References_Return.at["BufferSEM",0] = flt_Buffer_SEM
    dfr_References_Return.at["BufferSTDEV",0] = flt_Buffer_STDEV
    dfr_References_Return.at["BufferMAD",0] = flt_Buffer_MAD

    dfr_References_Return.at["ZPrimeMean",0] = flt_ZPrime_Mean
    dfr_References_Return.at["ZPrimeMedian",0] = flt_ZPrime_Median

    return dfr_References_Return, dfr_Layout

def get_layout(processed_transfer,str_TransferEntry,raw_data):

    wells = raw_data.shape[0]
    raw_data["Well"] = raw_data["Well"].apply(lambda x: pf.sortable_well(x, wells))
    # Extracts location of controls and references from processed transfer file
    # Rename some columns to make things easier, get only columns and rows we need
    processed_transfer = processed_transfer[(processed_transfer["Destination"]==str_TransferEntry)]
    processed_transfer = processed_transfer[["Destination","SampleID","SampleName","DestinationWell"]].rename(columns={"DestinationWell":"Well"})
    # Get control values (e.g. 100% inhibition)
    controls = processed_transfer[["Well","SampleName"]].rename(columns={"SampleName":"Control"})
    controls = controls[(controls["Control"] == "Control")]
    controls.loc[controls["Control"].notnull(),"Control"] = True
    controls["Well"] = controls["Well"].apply(lambda x: pf.sortable_well(x, wells))
    # Create a dataframe that will eventually hold Five columns: Well, Reading, Control, Transfer, Buffer, Solvent.
    layout = raw_data.merge(controls, on=["Well"], how="left")
    # Get all wells with a transfer associated with it -> those without will be buffer wells
    transfers = processed_transfer["Well"].apply(lambda x: pf.sortable_well(x, wells)).unique()
    trues = [True] * len(transfers)
    transfers = pd.DataFrame(list(zip(transfers,trues)),columns=["Well","Transfer"])
    # Merge all transfers into reference dataframe
    layout = layout.merge(transfers, on=["Well"], how="left")
    samples = processed_transfer[["Well","SampleID"]]
    samples = samples[samples["SampleID"].notnull() & (samples["SampleID"] != "Control")]
    samples["Well"] = samples["Well"].apply(lambda x: pf.sortable_well(x, wells))
    layout = layout.merge(samples, on=["Well"], how="left")
    # Get entries in transfer file with no sample -> Solvent transfer. Could be backfills!
    solvent = processed_transfer[["Well","SampleName"]].rename(columns={"SampleName":"Solvent"})
    solvent = solvent[solvent["Solvent"].isnull()]
    solvent.loc[solvent["Solvent"].isnull() == True, "Solvent"] = True
    solvent["Well"] = solvent["Well"].apply(lambda x: pf.sortable_well(x, wells))
    layout = layout.merge(solvent, on=["Well"], how="left")

    # Create empty lists
    lst_Welltype = [""] * wells
    lst_ProteinNumerical = [""] * wells
    lst_ProteinID = [""] * wells
    lst_ProteinConcentration = [""] * wells
    lst_ControlNumerical = [""] * wells
    lst_ControlID = [""] * wells
    lst_ControlConcentration = [""] * wells
    lst_ZPrime = [""] * wells
    lst_ReferenceNumerical = [""] * wells
    lst_ReferenceID = [""] * wells
    lst_ReferenceConcentration = [""] * wells
    lst_SampleNumerical = [""] * wells
    lst_SampleID = [""] * wells
    lst_SampleConcentration = [""] * wells

    # write relevant things into lists
    for i in range(layout.shape[0]):
        if any_nonnan(layout.loc[i,"Reading"]):
            if layout.loc[i,"Control"] == True:
                lst_ControlID[i] = "Control 1"
                lst_ControlNumerical[i] = "1"
                lst_Welltype[i] = "c"
            elif layout.loc[i,"Solvent"] == True:
                if pd.isna(layout.loc[i,"SampleID"]):
                    lst_ReferenceID[i] = "Solvent"
                    lst_ReferenceNumerical[i] = "1"
                    lst_Welltype[i] = "r"
                else:
                    layout.loc[i,"Solvent"] == False
                    lst_SampleID[i] = layout.loc[i,"SampleID"]
                    lst_Welltype[i] = "s"
            elif not pd.isna(layout.loc[i,"SampleID"]):
                lst_SampleID[i] = layout.loc[i,"SampleID"]
                lst_Welltype[i] = "s"
            else:
                lst_ReferenceID[i] = "Buffer"
                lst_ReferenceNumerical[i] = "2"
                lst_Welltype[i] = "b"

    # Write it all to dataframe
    layout_return = pd.DataFrame(index=range(wells),
                                          data = {"WellType":lst_Welltype,
                                                  "ProteinNumerical":lst_ProteinNumerical,
                                                  "ProteinID":lst_ProteinID,
                                                  "ProteinConcentration":lst_ProteinConcentration,
                                                  "ControlNumerical":lst_ControlNumerical,
                                                  "ControlID":lst_ControlID,
                                                  "ControlConcentration":lst_ControlConcentration,
                                                  "ZPrime":lst_ZPrime,
                                                  "ReferenceNumerical":lst_ReferenceNumerical,
                                                  "ReferenceID":lst_ReferenceID,
                                                  "ReferenceConcentration":lst_ReferenceConcentration,
                                                  "SampleNumerical":lst_SampleNumerical,
                                                  "SampleID":lst_SampleID,
                                                  "SampleConcentration":lst_SampleConcentration})

    return layout_return

##########################################################
##                                                      ##
##     #####  ##  ##   ####   #####   ######  #####     ##
##    ##      ##  ##  ##  ##  ##  ##  ##      ##  ##    ##
##     ####   ######  ######  #####   ####    ##  ##    ##
##        ##  ##  ##  ##  ##  ##  ##  ##      ##  ##    ##
##    #####   ##  ##  ##  ##  ##  ##  ######  #####     ##
##                                                      ##
##########################################################

def complete_container(ProjectTab, dlg_progress):

    plate_assignment = ProjectTab.dfr_PlateAssignment
    data_path = ProjectTab.paths["Data"]
    transfer_file = ProjectTab.dfr_TransferFile
    layout = ProjectTab.dfr_Layout
    details = ProjectTab.details
    data_rules = ProjectTab.rawdata_rules
    exceptions = ProjectTab.dfr_Exceptions

    assay_name = details["AssayType"]
    assay_category = details["AssayCategory"]
    assay_volume = details["AssayVolume"]
    sample_source = details["SampleSource"]
    device = details["Device"]
    plate_assignment = plate_assignment[plate_assignment["DataFile"] != ""]

    # Assay category is broad: single_dose, IC50 (or dose response), DSF_384...
    # Count how many rows we need:
    dlg_progress.lbx_Log.InsertItems([f"Assay category: {assay_category}"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
    container = pd.DataFrame(columns=["Destination","Samples","Wells","DataFile",
        "RawData","Processed","PlateID","Layout","References"], index=range(plate_assignment.shape[0]))
    # Iterate through the plate_assignment frame
    for plate in plate_assignment.index:
        container.loc[plate,"Destination"] = plate_assignment.loc[plate,"TransferEntry"]
        dest = container.loc[plate,"Destination"]
        dlg_progress.lbx_Log.InsertItems([f"Processing plate {plate+1}: {dest}"], dlg_progress.lbx_Log.Count)
        dlg_progress.lbx_Log.InsertItems(["==============================================================="], dlg_progress.lbx_Log.Count)
        container.loc[plate,"Wells"] = int(plate_assignment.loc[plate,"Wells"])
        container.loc[plate,"DataFile"] = plate_assignment.loc[plate,"DataFile"]
        # Get raw data
        datafile = container.loc[plate,"DataFile"]
        dlg_progress.lbx_Log.InsertItems([F"Read raw data file: {datafile}"], dlg_progress.lbx_Log.Count)
        if assay_category.find("dose_response") != -1:
            container.at[plate,"RawData"] = ro.get_bmg_plate_readout(data_path,
                                                                          container.loc[plate,"DataFile"],
                                                                          container.loc[plate,"Wells"],
                                                                          assay_name)
            #container.at[plate,"RawData"], rawdataread = ro.get_readout(data_path,
            #                                                            container.loc[plate,"DataFile"],
            #                                                            data_rules)
        elif assay_category.find("single_dose") != -1:
            # All plates will be the same plate type!
            raw_data = ro.get_bmg_list_readout(data_path, int(plate_assignment.loc[0,"Wells"]))
            container.at[plate,"RawData"] = raw_data[["Well",container.loc[plate,"DataFile"]]]
            #container.at[plate,"RawData"], rawdataread = ro.get_readout(data_path,
            #                                                            container["DataFile"].to_list(),
            #                                                            data_rules)
        elif assay_category == "thermal_shift":
            if "Agilent" in assay_name and "96" in assay_name:
                container.at[plate,"RawData"] = ro.get_mxp_readout(data_path + chr(92) + container.loc[plate,"DataFile"], 24) # last argument is NOT number of wells but starting temperature!
            elif "LightCycler" in assay_name and "96" in assay_name:
                container.at[plate,"RawData"] = ro.get_lightcycler_readout(data_path + chr(92) + container.loc[plate,"DataFile"], 96)
            elif "LightCycler" in assay_name and "384" in assay_name:
                container.at[plate,"RawData"] = ro.get_lightcycler_readout(data_path + chr(92) + container.loc[plate,"DataFile"], 384)
            elif "QuantStudio" in assay_name and "384" in assay_name:
                container.at[plate,"RawData"] = ro.get_quantstudio_readout(data_path + chr(92) + container.loc[plate,"DataFile"], 384)
        elif assay_category == "rate":
            container.at[plate,"RawData"] = ro.get_bmg_timecourse_readout(data_path + container.loc[plate,"DataFile"])
        # Test whether a correct file was loaded:
        if container.loc[plate,"RawData"] is None: # == False:
            msg.warn_not_datafile("self")
            return None
        # Get samples
        if sample_source == "echo":
            dlg_progress.lbx_Log.InsertItems(["Extract sample IDs from transfer file"], dlg_progress.lbx_Log.Count)
            container.at[plate,"Samples"] = get_samples(transfer_file,
                                                        container.loc[plate,"Destination"],
                                                        container.loc[plate,"Wells"])
        elif sample_source == "lightcycler":
            dlg_progress.lbx_Log.InsertItems(["Extract sample IDs from raw data file"], dlg_progress.lbx_Log.Count)
            container.at[plate,"Samples"] = get_samples_lightcycler(container.loc[plate,"Destination"],
                                                                    container.at[plate,"RawData"],
                                                                    len(layout.loc[plate,"ProteinNumerical"]))
        elif sample_source == "well":
            container.at[plate,"Samples"] = get_samples_wellonly(container.loc[plate,"Destination"],
                                                                 container.at[plate,"RawData"],
                                                                 len(layout.loc[plate,"ProteinNumerical"]))
        if assay_category == "thermal_shift":
            # References get handled differently here
            if layout.shape[0] > 1:
                idx_Layout = plate
            else:
                idx_Layout = 0
            container.at[plate,"PlateID"] = layout.loc[idx_Layout,"PlateID"]
            container.at[plate,"Layout"] = layout.loc[idx_Layout,"Layout"]
            # Create dataframe for data processing
            container.at[plate,"Processed"], container.at[plate,"References"] = create_dataframe_DSF(container.at[plate,"RawData"],
                                                                                                              container.loc[plate,"Samples"],
                                                                                                              layout.loc[idx_Layout,"Layout"],
                                                                                                              dlg_progress)
        elif assay_category.find("rate") != -1:
            # References get handled differently here
            container.at[plate,"Layout"] = get_layout(transfer_file,
                                                      container.loc[plate,"Destination"],
                                                      container.loc[plate,"RawData"].rename(columns={"Signal":"Reading"}))
            # Create dataframe for data processing
            container.at[plate,"Processed"], container.at[plate,"References"] = create_dataframe_rate(container.at[plate,"RawData"],
                container.loc[plate,"Samples"],container.loc[plate,"Layout"],dlg_progress)
        else:
            # Endpoint assays
            # Get controls and references
            container.at[plate,"Layout"] = get_layout(transfer_file,
                                                      container.loc[plate,"Destination"],
                                                      container.loc[plate,"RawData"].rename(columns={datafile:"Reading"}))
            container.at[plate,"References"] = get_references(container.at[plate,"Layout"],
                                                              datafile,
                                                              container.loc[plate,"RawData"])
            if pd.isna(container.loc[plate,"References"].loc["SolventMean",0]) == True:
                dlg_progress.lbx_Log.InsertItems(["Note: No Solvent wells"], dlg_progress.lbx_Log.Count)
            if pd.isna(container.loc[plate,"References"].loc["ControlMean",0]) == True:
                dlg_progress.lbx_Log.InsertItems(["Note: No control wells"], dlg_progress.lbx_Log.Count)
            if pd.isna(container.loc[plate,"References"].loc["BufferMean",0]) == True:
                dlg_progress.lbx_Log.InsertItems(["Note: No buffer wells"], dlg_progress.lbx_Log.Count)
            # Create dataframe for data processing
            if assay_category.find("dose_response") != -1:
                container.at[plate,"Processed"] = create_dataframe_EPDR(container.at[plate,"RawData"],
                    container.loc[plate,"Samples"],container.loc[plate,"References"],assay_name,assay_volume,dlg_progress)
            elif assay_category.find("single_dose") != -1:
                container.at[plate,"Processed"] = create_dataframe_EPSD(container.at[plate,"RawData"],
                    container.loc[plate,"Samples"],container.loc[plate,"References"],assay_name,assay_volume,dlg_progress)
        dlg_progress.lbx_Log.InsertItems(["Plate "+ str(plate+1) + " completed"], dlg_progress.lbx_Log.Count)
        dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)

    return container

def ProgressGauge(current,total):
    int_Length = 20
    int_Full = int(round(current/total * int_Length,0))
    int_Blank = int_Length - int_Full
    str_Full = chr(9646)
    str_Blank = chr(9647)
    str_Gauge = "[" + int_Full*str_Full + int_Blank*str_Blank + "]"
    return str_Gauge

def blankfornan(fnord):
    """
    Turns argument into empty string if argument is nan
    """
    if pd.isna(fnord) == True:
        return ""
    else:
        return fnord

def nanint(number):
    """
    Use for turning numbers in a dataframe into integers when
    there might be "nan"s or other data types in the data.
    These will be untouched.
    """
    try:
        return int(number)
    except:
        return number

def Mean_SEM_STDEV(lst_Values):
    """
    Calculates Mean, Standard Error of Mean and STandard DEViation for a list of values.
    Previously used my own function and doing it manually. But why do that if numpy can do it faster?
    """
    if any_nonnan(lst_Values) == True:
        flt_Mean = round(np.nanmean(lst_Values),2)
        flt_STDEV= np.std(lst_Values, ddof=1)
        flt_SEM = flt_STDEV / np.sqrt(np.size(lst_Values))
        return flt_Mean, flt_SEM, flt_STDEV
    else:
        return np.nan, np.nan, np.nan

def Mean_SEM_STDEV_ListList(lstlstRawData):
    """
    Helper function to calculate Mean, SEM and STDEV in a list of lists (e.g. for a series of concentrations with replicate values at each point)
    """
    lst_Mean = []
    lst_STDEV = []
    lst_SEM = []
    
    for lst_Elem in lstlstRawData:
        Mean, SEM, STDEV = Mean_SEM_STDEV(lst_Elem)
        lst_Mean.append(Mean)
        lst_SEM.append(SEM)
        lst_STDEV.append(STDEV)

    return lst_Mean, lst_SEM, lst_STDEV

def mad(dataset):
    """
    Calculates mean absolute deviation for a list of values.
    Returns np.nan if there are no numeric values in the list.
    """
    if any_nonnan(dataset) == True:
        median = np.nanmedian(dataset)
        dataset = abs(dataset-median)
        return np.nanmedian(dataset)
    else:
        return np.nan

def moles_to_micromoles(lst_Conc):
    """
    Turns moles/molar into micromoles/micromolar
    """
    # initialise list
    lst_ConcMicro = []
    for conc in lst_Conc:
        # Convert to micromoles/ar
        concentration = float(conc)*1000000
        # cut off beyond 5th decimal
        concentration = int(concentration*100000)/100000
        # add to list
        lst_ConcMicro.append(concentration)
    # remove dummy element from list
    return lst_ConcMicro

def any_nonnan(values):
    """
    Tests a list to see if there are _any_ elements that are NOT nan.
    Previous version actually went through the whole list and counted the non-nan values. Returned True when the count was > 0.
    For the purposes of this function, we can just return True as soon as we encounter a value that is not nan.
    """
    if hasattr(values, "__iter__"):
        if not pd.Series(values).isnull().values.all():
            return True
        #for val in values:
        #    # Return True as soon as a non-nan value is encountered
        #    if not pd.isna(val):
        #        return True
    else:
        if not pd.isna(values):
            return True
    # If there are only nan values, we get to this point and return False
    return False

def import_string_to_list(str_Input):
    """
    Convert strings of this format "['1.1','2.2','3.3']" into actual lists.
    Also takes into accound possibility of lists of lists.
    """
    if (type(str_Input) == str and str_Input.find("[") != -1 and
        str_Input.find("]") != -1 and str_Input.find("Destination") == -1):
        # Determine the list separator
        if str_Input.find(",") != -1:
            str_Separator = ", "
        else:
            str_Separator = " "
        lst_Converted = []
        # Make sure we can handle lists of lists
        # If we are dealing with a simple list, there will only be one
        # pair of square brackets
        if str_Input.count("[") == 1:
            # Truncate string by first and last (i.e. [ and ]) and split by str_Separator
            lst_Parsed = list(str_Input[1:int(len(str_Input)-1)].split(str_Separator))
            for element in lst_Parsed:
                # This is included because in IC50 curves I use "found"as keyword for concentrations with replicates
                if element.find("found") != -1:
                    lst_Converted.append(element)
                elif len(element) > 0:
                    # Take care of single quotes surrounding strings: If single quotes, we are working with actual lists of strings, not numbers stored as strings.
                    if element.find("'") == -1:
                        if element == "True":
                            lst_Converted.append(True)
                        elif element == "False":
                            lst_Converted.append(False)
                        else:
                            lst_Converted.append(float(element))
                    else:
                        lst_Converted.append(element[1:(len(element)-1)])
        else:
            # Nowe we deal with lists of lists
            # Remove square brackets at outside of string
            str_ListOfLists = str_Input[1:int(len(str_Input)-1)]
            # Variable to keep track of which level we are on:
            lst_Toplevel = []
            str_Temp = ""
            open = False
            for element in str_ListOfLists:
                if open == True:
                    str_Temp = str_Temp + element
                if element == "[":
                    open = True
                elif element == "]":
                    open = False
                if open == False and str_Temp != "":
                    if str_Temp.find(",") != -1:
                        str_Separator = ", "
                    else:
                        str_Separator = " "
                    lst_Append = list(str_Temp[0:int(len(str_Temp)-1)].split(str_Separator))
                    lst_Converted.append([])
                    for j in range(len(lst_Append)):
                        if lst_Append[j] != "''":
                            lst_Converted[len(lst_Converted)-1].append(lst_Append[j])
                    str_Temp = ""
            # Convert to numbers, of possible
            for element in lst_Converted:
                for jelement in element:
                    try:
                        jelement = int(jelement)
                    except:
                        try: jelement = float(jelement)
                        except: None
    else:
        return str_Input
    return lst_Converted

def get_csv_columns(str_TransferFile):
    # This works, but is super slow. Leave here for posterity
    file = open(str_TransferFile)
    int_MaxColumns = 0
    int_MaxRows = 0

    bol_FoundStart = False
    lst_Test = []
    # Iterate through the csv file
    for row in file.readlines():
        # First check: See if we have found the start:
        if bol_FoundStart == True:
            pd.read_csv(file, sep=",", header=0, index_col=False, engine="python")
            # Second check: Stop if we are in the last line!
            if row.find("Instrument Name") != -1:
                # If this is found, it means that we have reached the end of the transfer data
                break
            else:
                lst_Test.append(row.split(","))
                int_Columns = len(lst_Test[-1]) #length of last item in list
                if int_Columns > int_MaxColumns:
                    int_MaxColumns = int_Columns
                int_MaxRows += 1
        else:
            if row.find("[DETAILS]") != -1:
                bol_FoundStart = True

    # create the dataframe
    transfer_file = pd.DataFrame(columns=range(int_MaxColumns),index=range(int_MaxRows))
    for i in range(int_MaxRows):
        for j in range(len(lst_Test[i])):
            transfer_file.iloc[i,j] = lst_Test[i][j]

    return int_MaxColumns

def string_or_na(value):
    if pd.isna(value) == True or value == "":
        return "NA"
    elif type(value) != str:
        return str(value)
    else:
        return value

def change_concentrations(flt_OldStock,flt_NewStock,lst_Concentrations,assay_volume):
    # Changes concentrations based on new stock concentration and transfer volumes
    flt_AssayVolume = float(assay_volume)
    # AssayConc = (TransferVolume*StockConc)/AssayVolume
    #for i in range(len(lstConcentrations)):
        #TransferVolume = (float(lstConcentrations[i])/fltOldStock) * fltAssayVolume
        # There were issues when writing the new list concentrations into the dataframe due to rounding errors (sometimes there were many zeros followed by a nonzero,
        # for example after changing a source concentration and then chaning it back to the original value  2.24E-5 would turn into 0.00022400000000000002, with
        # pandas unable to write the new list over the old). Solution was rounding off the offending digits.
        #flt_NewConc = round(((TransferVolume*fltNewStock)/fltAssayVolume)*100000000000,0)/100000000000
        #lstNewConc.append(flt_NewConc)
    TransferVolume = (float(lst_Concentrations)/flt_OldStock) * flt_AssayVolume
    flt_NewConc = round(((TransferVolume*flt_NewStock)/flt_AssayVolume)*100000000000,0)/100000000000
    return flt_NewConc

def nearest(list, item, index=False):
    # https://www.geeksforgeeks.org/python-find-closest-number-to-k-in-given-list/
    if any_nonnan(list) == True:
        list = np.asarray(list)
        list_nonan = list[np.logical_not(np.isnan(list))]
        idx = (np.abs(list_nonan - item)).argmin()
        if index == False:
            return list_nonan[idx]
        else:
            return idx
    else:
        return np.nan

def Normalise(lst_Readings,str_AssayType,dfr_References):
    flt_Solvent = dfr_References.loc["SolventMean",0]
    flt_Control = dfr_References.loc["ControlMean",0]
    flt_Buffer = dfr_References.loc["BufferMean",0]
    lstNorm = []
    # Check if there are controls:
    if pd.isna(flt_Control) == True:
        flt_Control = 0
    # Check which reference to use
    if pd.isna(flt_Solvent) == True:
        flt_Reference = flt_Buffer - flt_Control
    else:
        flt_Reference = flt_Solvent - flt_Control
    # run check for assay type str_AssayType was saved in lst_Details[0]
    if str_AssayType == "HTRF":
        # for HTRF
        for val in lst_Readings:
            lstNorm.append(round(100 * (1-((val - flt_Control)/flt_Reference)),2))
    elif str_AssayType == "TAMRA FP":
        flt_Control = flt_Control - flt_Reference
        for val in lst_Readings:
            lstNorm.append(round(100 * ((val - flt_Reference) / flt_Control),2))
    elif str_AssayType == "AlphaScreen" or str_AssayType.find("Glo") != -1:
        for val in lst_Readings:
            lstNorm.append(round(100 * (1 - ((val - flt_Control) / flt_Reference)),2))
    return lstNorm

def middle_of_list(lst):
    """
    Gives the approximate middle item of a list by rounding up
    to an int in case of a list of an even numbered length.

    Arguments:
    lst -> list
    """

    if not isinstance(lst, list):
        lst = list(lst)

    idx = int(len(lst)/2)

    return lst[idx]

##########################################
##                                      ##
##    ######  #####   #####   #####     ##
##    ##      ##  ##  ##  ##  ##  ##    ##
##    ####    #####   ##  ##  #####     ##
##    ##      ##      ##  ##  ##  ##    ##
##    ######  ##      #####   ##  ##    ##
##                                      ##
##########################################

def create_dataframe_EPDR(dfr_RawData, dfr_Samples, dfr_References, str_AssayType, assay_volume, dlg_progress):
    """
    This function is for endpoint protein-peptide interaction/displacement assays such as HTRF, AlphaScreen or endpoint assays of enzymatic
    reactions such as the "Glo" family of assays.
    Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
    and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
    to calculate values based on the assay type.
    """
    # Get number of samples:
    int_Samples = dfr_Samples.shape[0]
    # Create new dataframe
    lst_Columns = ["Destination","SampleID","Locations","Concentrations","SourceConcentration","AssayVolume","RawData",
        "Raw","RawSEM","RawExcluded","RawFit","RawFitPars","RawFitCI","RawFitR2","RawFitErrors","DoFitRaw",
        "Norm","NormSEM","NormExcluded","NormFitFree","NormFitFreePars","NormFitFreeCI","NormFitFreeR2","NormFitFreeErrors","DoFitFree",
        "NormFitConst","NormFitConstPars","NormFitConstCI","NormFitConstR2","NormFitConstErrors","DoFitConst",
        "Show","DoFit"]
    dfr_Processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))
    fltAssayVolume = float(assay_volume)
    # Check each concentration if it occurs more than once, then write it into a new list and add the corresponding locations
    # to a list and add that list to a list. Once finished, overwrite columns Locations and Concentration with the new list.
    # dfr_Samples must have been sorted for Concentration for this to work properly.
    dlg_progress.lbx_Log.InsertItems([f"Number of samples to process: {int_Samples}"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([f"Processed 0 out of {int_Samples} samples"], dlg_progress.lbx_Log.Count)
    for smpl in range(int_Samples):
        # Assign list of lists to dataframe
        dfr_Processed.loc[smpl,"Destination"] = dfr_Samples.loc[smpl,"Destination"]
        dfr_Processed.loc[smpl,"SampleID"] = dfr_Samples.loc[smpl,"SampleID"]
        dfr_Processed.loc[smpl,"SourceConcentration"] = dfr_Samples.loc[smpl,"SourceConcentration"]
        dfr_Processed.loc[smpl,"Concentrations"] = dfr_Samples.loc[smpl,"Concentrations"]
        dfr_Processed.loc[smpl,"AssayVolume"] = fltAssayVolume
        dfr_Processed.loc[smpl,"Locations"] = dfr_Samples.loc[smpl,"Locations"]
        lstlstRaw = []
        for conc in range(len(dfr_Processed.loc[smpl,"Concentrations"])):
            lstlstRaw.append([dfr_RawData.iloc[rep,1] for rep in dfr_Processed.loc[smpl,"Locations"][conc]])
        dfr_Processed.loc[smpl,"RawData"] = lstlstRaw
        dfr_Processed.loc[smpl,"Raw"], dfr_Processed.loc[smpl,"RawSEM"], fnord = Mean_SEM_STDEV_ListList(lstlstRaw)
        dfr_Processed.loc[smpl,"RawExcluded"] = [np.nan] * len(dfr_Processed.loc[smpl,"Concentrations"])

        # Normalisation needs to happen before datafitting is attempted
        lstlstNorm = [Normalise(raw, str_AssayType, dfr_References) for raw in lstlstRaw]
        dfr_Processed.loc[smpl,"Norm"], dfr_Processed.loc[smpl,"NormSEM"], fnord = Mean_SEM_STDEV_ListList(lstlstNorm)
        dfr_Processed.loc[smpl,"NormExcluded"] = [np.nan] * len(dfr_Processed.loc[smpl,"Concentrations"])

        # Fitting criteria
        # Exclude points where the NormSEM is > 20%
        for j in range(len(dfr_Processed.loc[smpl,"Raw"])):
            if dfr_Processed.loc[smpl,"NormSEM"][j] > 20:
                dfr_Processed.loc[smpl,"RawExcluded"][j] = dfr_Processed.loc[smpl,"Raw"][j]
                dfr_Processed.loc[smpl,"Raw"][j] = np.nan
                dfr_Processed.loc[smpl,"NormExcluded"][j] = dfr_Processed.loc[smpl,"Norm"][j]
                dfr_Processed.loc[smpl,"Norm"][j] = np.nan
            else:
                dfr_Processed.loc[smpl,"RawExcluded"][j] = np.nan
                dfr_Processed.loc[smpl,"NormExcluded"][j] = np.nan
        # Criteria for fit:
        dfr_Processed.loc[smpl,"DoFit"] = get_DoFit(dfr_Processed.loc[smpl,"Norm"],dfr_Processed.loc[smpl,"NormSEM"])
        # Perform fit -> Check if fitting criteria are met in the first instance
        if dfr_Processed.loc[smpl,"DoFit"] == True:
            dfr_Processed.loc[smpl,"RawFit"], dfr_Processed.loc[smpl,"RawFitPars"], dfr_Processed.loc[smpl,"RawFitCI"], dfr_Processed.loc[smpl,"RawFitErrors"], dfr_Processed.loc[smpl,"RawFitR2"], dfr_Processed.loc[smpl,"DoFitRaw"] = ff.fit_sigmoidal_free(dfr_Processed.loc[smpl,"Concentrations"], dfr_Processed.loc[smpl,"Raw"])
            dfr_Processed.loc[smpl,"NormFitFree"], dfr_Processed.loc[smpl,"NormFitFreePars"], dfr_Processed.loc[smpl,"NormFitFreeCI"], dfr_Processed.loc[smpl,"NormFitFreeErrors"], dfr_Processed.loc[smpl,"NormFitFreeR2"], dfr_Processed.loc[smpl,"DoFitFree"] = ff.fit_sigmoidal_free(dfr_Processed.loc[smpl,"Concentrations"], dfr_Processed.loc[smpl,"Norm"])
            # Constrained fit needs SEM for fit
            dfr_Processed.loc[smpl,"NormFitConst"], dfr_Processed.loc[smpl,"NormFitConstPars"], dfr_Processed.loc[smpl,"NormFitConstCI"], dfr_Processed.loc[smpl,"NormFitConstErrors"], dfr_Processed.loc[smpl,"NormFitConstR2"], dfr_Processed.loc[smpl,"DoFitConst"] = ff.fit_sigmoidal_const(dfr_Processed.loc[smpl,"Concentrations"], dfr_Processed.loc[smpl,"Norm"], dfr_Processed.loc[smpl,"NormSEM"])
            # If both the free and constrained fit fail, set check variable to False
            if dfr_Processed.loc[smpl,"DoFitFree"] == False and dfr_Processed.loc[smpl,"DoFitConst"] == False:
                dfr_Processed.loc[smpl,"DoFit"] = False
        else:
            many = len(dfr_Processed.loc[smpl,"Raw"])
            dfr_Processed.loc[smpl,"RawFit"], dfr_Processed.loc[smpl,"RawFitPars"] = [np.nan] * many, [np.nan]*4
            dfr_Processed.loc[smpl,"RawFitCI"], dfr_Processed.loc[smpl,"RawFitErrors"] = [np.nan]*4, [np.nan]*4
            dfr_Processed.loc[smpl,"RawFitR2"] = np.nan
            dfr_Processed.loc[smpl,"DoFitRaw"] = False
            dfr_Processed.loc[smpl,"NormFitFree"],dfr_Processed.loc[smpl,"NormFitFreePars"] = [np.nan] * many, [np.nan]*4
            dfr_Processed.loc[smpl,"NormFitFreeCI"], dfr_Processed.loc[smpl,"NormFitFreeErrors"] = [np.nan]*4, [np.nan]*4
            dfr_Processed.loc[smpl,"NormFitFreeR2"] = np.nan
            dfr_Processed.loc[smpl,"DoFitFree"] = False
            dfr_Processed.loc[smpl,"NormFitConst"],dfr_Processed.loc[smpl,"NormFitConstPars"] = [np.nan] * many, [np.nan]*4
            dfr_Processed.loc[smpl,"NormFitConstCI"], dfr_Processed.loc[smpl,"NormFitConstErrors"] = [np.nan]*4, [np.nan]*4
            dfr_Processed.loc[smpl,"NormFitConstR2"] = np.nan
            dfr_Processed.loc[smpl,"DoFitConst"] = False

        dfr_Processed.loc[smpl,"Show"] = 1
        dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, f"{ProgressGauge(smpl+1,int_Samples)} {smpl+1} out of {int_Samples} samples.")

    # Return
    return dfr_Processed

def get_DoFit(lst_Data,lst_Error):
    '''
    Tests a set of normalised datapoints on whether to perform a sigmoidal fit.
    Criteria for fit:
    - More than five datapoints with standard error of mean < 20%
    - Maximum datapoint >= 60% \_ensure the IC50 is actually within the range)
    - Minimum datapoint <= 40% /
    '''
    count = 0
    for error in lst_Error:
        if error < 20:
            count += 1
            # As soon as we have enough datapoints, check whether the other conditions apply:
            if count > 5:
                if np.nanmax(lst_Data) >= 60 and np.nanmin(lst_Data) <= 40:
                    return True
                else:
                    return False

def recalculate_fit_sigmoidal(owner, plate, smpl, dp = None, do_return = False):

    """
    Recalculates the fit for datapoints after some datapoints may have been changed (i.e.
    outliers or error too high) or after user decided to fit a dataset that was previously
    not fit.

    Arguments:
        owner -> object that owns the assay_data dataframe
        plate -> int. Index of the plate in assay_data dataframe
        smpl -> int. Index of sample in processed dataframe
        dp -> int. Optional datapoint if coming from a plot's pick event
        do_return -> boolean. Whether to return the dataset or not
                     use in conjunction with a plot.
    """

    dataset = owner.assay_data.loc[plate,"Processed"].loc[smpl].to_dict()

    if not dp is None:
        # test whether there is enough data to fit
        if not np.isnan(dataset["Raw"][dp]):
            # First check if there are enough datapoints left to perform a fit
            if enough_points(dataset["Raw"], 5):
                # Selected datapoint IS NOT excluded -> copy it into excluded series and set value in data series to nan
                dataset["RawExcluded"][dp] = dataset["Raw"][dp]
                dataset["Raw"][dp] = np.nan
                dataset["NormExcluded"][dp] = dataset["Norm"][dp]
                dataset["Norm"][dp] = np.nan
            else:
                return None
        else:
            # Selected datapoint IS excluded -> copy it back into data series and set value in excluded series to nan
            dataset["Raw"][dp] = dataset["RawExcluded"][dp]
            dataset["RawExcluded"][dp] = np.nan
            dataset["Norm"][dp] = dataset["NormExcluded"][dp]
            dataset["NormExcluded"][dp] = np.nan
        
    # Check whether a re-fit is required:
    dataset["DoFit"] = get_DoFit(dataset["Norm"],dataset["NormSEM"])
            
    if dataset["DoFit"] == True:
        # 3. Re-fit
        dataset["RawFit"], dataset["RawFitPars"], dataset["RawFitCI"], dataset["RawFitErrors"], dataset["RawFitR2"], dataset["DoRawFit"] = ff.fit_sigmoidal_free(dataset["Concentrations"], dataset["Raw"])  # only function for constrained needs SEM
        dataset["NormFitFree"], dataset["NormFitFreePars"], dataset["NormFitFreeCI"], dataset["NormFitFreeErrors"], dataset["NormFitFreeR2"], dataset["DoRawFree"] = ff.fit_sigmoidal_free(dataset["Concentrations"], dataset["Norm"])
        dataset["NormFitConst"], dataset["NormFitConstPars"], dataset["NormFitConstCI"], dataset["NormFitConstErrors"], dataset["NormFitConstR2"], dataset["DoRawConst"] = ff.fit_sigmoidal_const(dataset["Concentrations"], dataset["Norm"], dataset["NormSEM"])
        if dataset["DoFitFree"] == False and dataset["DoFitConst"] == False:
            dataset["DoFit"] = False
    else:
        dataset["RawFit"] = [np.nan] * len(dataset["RawFit"])
        dataset["RawFitPars"] = [np.nan] * 4
        dataset["RawFitR2"] = np.nan

        dataset["NormFitFree"] = [np.nan] * len(dataset["NormFitFree"])
        dataset["NormFitFreePars"] = [np.nan] * 4
        dataset["NormFitFreeR2"] = np.nan

        dataset["NormFitConst"] = [np.nan] * len(dataset["NormFitConst"])
        dataset["NormFitConstPars"] = [np.nan] * 4
        dataset["NormFitConstR2"] = np.nan

        dataset["NormFitFreeCI"], dataset["NormFitConstCI"], dataset["RawFitCI"] = [np.nan] * 4, [np.nan] * 4, [np.nan] * 4
        dataset["NormFitFreeErrors"], dataset["NormFitConstErrors"], dataset["RawFitErrors"] = [np.nan] * 4, [np.nan] * 4, [np.nan] * 4
    
    dataset = pd.Series(dataset)

    # return dataset back to assay_data
    owner.assay_data.at[plate,"Processed"].loc[smpl] = dataset

    return dataset

def enough_points(lst, min):
    """
    Test if a list of values has more than a minimum of not NaN values
    
    Arguments:
        lst -> 1D collection of values that pandas can convert to
               a series
        min -> int. Number of values that must not be NaN
    """
    lst = pd.Series(lst)
    pts = lst.shape[0] - lst.isnull().sum()
    return pts > min

def write_IC50(flt_IC50,bol_DoFit,flt_Confidence):
    
    # Cannot do a direct type check as the curve fit returns numpy.float64.
    # When I read it in after saving the file it comes back as python native float and I have not figured out a sensible way to convert, yet.
    if bol_DoFit == False or str(type(flt_IC50)).find("float") == -1: # actually calculated values seem to be numpy.float64?
        return "N.D."
    else:
        flt_IC50 = flt_IC50 / 1000000 # IC50 gets handed to this function in micromolar -> turn back to molar
        flt_PlusMinus = flt_Confidence  / 1000000 
        if (flt_IC50) * 1000 <= 500 and flt_IC50 * 1000000 > 500:
            return str(round(flt_IC50 * 1000, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus * 1000, 1)) + " mM"
        elif flt_IC50 * 1000000 <= 500 and flt_IC50 * 1000000000 > 500:
            return str(round(flt_IC50 * 1000000, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus * 1000000, 1)) + " " + chr(181) + "M"
        elif flt_IC50 * 1000000000 <= 500 and flt_IC50 * 1000000000000 > 500:
            return str(round(flt_IC50 * 1000000000, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus * 1000000000, 1)) + " nM"
        else:
            return str(flt_IC50) + " M"

##########################################
##                                      ##
##    ######  #####    #####  #####     ##
##    ##      ##  ##  ##      ##  ##    ##
##    ####    #####    ####   ##  ##    ##
##    ##      ##          ##  ##  ##    ##
##    ######  ##      #####   #####     ##
##                                      ##
##########################################

def create_dataframe_EPSD(dfr_RawData, dfr_Samples, dfr_References, str_AssayType, assay_volume, dlg_progress):
    """
    This function is for endpoint protein-peptide interaction/displacement assays such as HTRF, AlphaScreen or endpoint assays of enzymatic
    reactions such as the "Glo" family of assays.
    Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
    and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
    to calculate values based on the assay type.
    """
    # Get number of samples:
    int_Samples = dfr_Samples.shape[0]
    # Create new dataframe
    lst_Columns = ["Destination","SampleID","Locations","Concentrations","SourceConcentration","AssayVolume","RawData",
        "Raw","RawSEM","RawExcluded","RawFit","RawFitPars","RawFitCI","RawFitR2","RawFitErrors","DoFitRaw",
        "Norm","NormSEM","NormExcluded","NormFitFree","NormFitFreePars","NormFitFreeCI","NormFitFreeR2","NormFitFreeErrors","DoFitFree",
        "NormFitConst","NormFitConstPars","NormFitConstCI","NormFitConstR2","NormFitConstErrors","DoFitConst",
        "Show","DoFit"]
    dfr_Processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))
    fltAssayVolume = float(assay_volume)
    # Check each concentration if it occurs more than once, then write it into a new list and add the corresponding locations
    # to a list and add that list to a list. Once finished, overwrite columns Locations and Concentration with the new list.
    # dfr_Samples must have been sorted for Concentration for this to work properly.
    dlg_progress.lbx_Log.InsertItems([f"Number of samples to process: {int_Samples}"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([f"Processed 0 out of {int_Samples} samples"], dlg_progress.lbx_Log.Count)
    for smpl in range(int_Samples):
        # Assign list of lists to dataframe
        dfr_Processed.loc[smpl,"Destination"] = dfr_Samples.loc[smpl,"Destination"]
        dfr_Processed.loc[smpl,"SampleID"] = dfr_Samples.loc[smpl,"SampleID"]
        dfr_Processed.loc[smpl,"SourceConcentration"] = dfr_Samples.loc[smpl,"SourceConcentration"]
        dfr_Processed.loc[smpl,"Concentrations"] = dfr_Samples.loc[smpl,"Concentrations"]
        dfr_Processed.loc[smpl,"AssayVolume"] = fltAssayVolume
        dfr_Processed.loc[smpl,"Locations"] = dfr_Samples.loc[smpl,"Locations"]
        lstlstRaw = []
        for conc in range(len(dfr_Processed.loc[smpl,"Concentrations"])):
            lstlstRaw.append([dfr_RawData.iloc[rep,1] for rep in dfr_Processed.loc[smpl,"Locations"][conc]])
        dfr_Processed.loc[smpl,"RawData"] = lstlstRaw
        dfr_Processed.loc[smpl,"Raw"], dfr_Processed.loc[smpl,"RawSEM"], fnord = Mean_SEM_STDEV_ListList(lstlstRaw)
        dfr_Processed.loc[smpl,"RawExcluded"] = [np.nan] * len(dfr_Processed.loc[smpl,"Concentrations"])

        lstlstNorm = [Normalise(raw, str_AssayType, dfr_References) for raw in lstlstRaw]
        dfr_Processed.loc[smpl,"Norm"], dfr_Processed.loc[smpl,"NormSEM"], fnord = Mean_SEM_STDEV_ListList(lstlstNorm)
        dfr_Processed.loc[smpl,"NormExcluded"] = [np.nan] * len(dfr_Processed.loc[smpl,"Concentrations"])

        dfr_Processed.loc[smpl,"Show"] = 1
        dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, f"{ProgressGauge(smpl+1,int_Samples)} {smpl+1} out of {int_Samples} samples.")
    # Return
    return dfr_Processed

##################################
##                              ##
##    #####    #####  ######    ##
##    ##  ##  ##      ##        ##
##    ##  ##   ####   ####      ##
##    ##  ##      ##  ##        ##
##    #####   #####   ##        ##
##                              ##
##################################

def create_dataframe_DSF(dfr_RawData, dfr_Samples, dfr_Layout, dlg_progress):
    """
    Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
    and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
    to calculate values based on the assay type.
    """
    wells = dfr_RawData.shape[0]
    # This function is called per plate, so there will only be one plate name
    str_PlateName = dfr_Samples.loc[0,"Destination"]

    lst_SampleIDs = [np.nan] * 384
    int_Samples = 0
    for smpl in dfr_Samples.index:
        for loc in dfr_Samples.loc[smpl,"Locations"]:
            if hasattr(loc, "__iter__"):
                for rep in loc:
                    lst_SampleIDs[rep] = dfr_Samples.loc[smpl,"SampleID"]
                    if pd.isna(lst_SampleIDs[rep]) == False:
                        int_Samples += 1
            else:
                lst_SampleIDs[loc] = dfr_Samples.loc[smpl,"SampleID"]
                if pd.isna(lst_SampleIDs[loc]) == False:
                    int_Samples += 1
    # Create new dataframe
    lst_Columns = ["Destination","SampleID","Protein","ProteinConcentration","Well",
                   "Temp","Initial",
                   "Raw","RawDeriv","RawDerivBaseline",
                   "RawInflections","RawPeakStarts","RawSlopes","RawInfMax","RawSlopeMax",
                   "RawTm","RawDTm","RawFit","RawFitPars",
                   "Norm","NormDeriv","NormDerivBaseline",
                   "NormInflections","NormPeakStarts","NormSlopes","NormInfMax","NormSlopeMax",
                   "NormTm","NormDTm","NormFit","NormFitPars",
                   "UseForDTm","UseNorm","DoFit","Method"]#,
                   #"RawSavgol","NormSavgol"]
    processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))
    #flt_AssayVolume = float(assay_volume)
    k = -1
    dlg_progress.lbx_Log.InsertItems([f"Number of samples to process: {int_Samples}"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems(["Processed 0 out of {int_Samples} samples"], dlg_progress.lbx_Log.Count)
    
    for sample in lst_SampleIDs:
        if type(sample) == str:
            k += 1 #k is set to -1 above, so this will set k = 0 in the first instance.
            # Assign list of lists to dataframe
            processed.loc[k,"Destination"] = str_PlateName
            processed.loc[k,"SampleID"] = sample
            processed.loc[k,"Well"] = dfr_RawData.loc[k,"Well"]
            processed.at[k,"Temp"] = dfr_RawData.loc[k,"Temp"]
            processed.at[k,"Raw"] = dfr_RawData.loc[k,"Fluo"]
            processed.at[k,"Protein"] = dfr_Layout.loc[k,"ProteinID"]
            processed.at[k,"ProteinConcentration"] = dfr_Layout.loc[k,"ProteinConcentration"]
            processed.loc[k,"Method"] = "Derivative"
            processed.loc[k,"UseNorm"] = False

            # Normalisation needs to happen before datafitting is attempted
            flt_FluoMin = np.nanmin(processed.loc[k,"Raw"])
            flt_FluoMax = np.nanmax(processed.loc[k,"Raw"]) - flt_FluoMin
            lst_Norm = []
            for val in processed.loc[k,"Raw"]:
                lst_Norm.append((val-flt_FluoMin)/flt_FluoMax)
            processed.at[k,"Norm"] = lst_Norm
            # Get initial fluorescence (average of normalised over first 10 degrees)
            flt_Initial = 0
            for j in range(10):
                flt_Initial = flt_Initial + processed.loc[k,"Norm"][j]
            flt_Initial = flt_Initial / 10
            if flt_Initial < 0.3:
                processed.loc[k,"Initial"] = 0
            if flt_Initial >= 0.3 and flt_Initial < 0.5:
                processed.loc[k,"Initial"] = 1
            elif flt_Initial > 0.5:
                processed.loc[k,"Initial"] = 2
            
            # Fitting criteria
            # Criteria for fit:
            processed.loc[k,"DoFit"] = True

            if processed.loc[k,"DoFit"] == True:
                # Always determine derivatives:
                for fit in ["Raw","Norm"]:
                    #processed.at[k,fit+"Savgol"]= scsi.savgol_filter(processed.loc[k,fit],20,2)
                    processed.at[k,fit+"Deriv"] = np.gradient(scsi.savgol_filter(processed.loc[k,fit],20,2))
                    processed.at[k,fit+"DerivBaseline"] = pu.baseline(np.asarray(processed.at[k,fit+"Deriv"]),
                                                                      deg = 3)
                    max = np.nanmax(processed.loc[k,fit+"Deriv"])
                    peaks, props = scsi.find_peaks(processed.loc[k,fit+"Deriv"], width = 5, height = max*0.05)
                    processed.at[k,fit+"Inflections"] = [int(p) for p in peaks]
                    processed.at[k,fit+"Slopes"] = [processed.loc[k,fit+"Deriv"][x] for x in peaks]
                    processed.at[k,fit+"PeakStarts"] = [processed.loc[k,"Temp"][int(x)] for x in props["left_ips"]]            
                    # find inflection point at which derivative is greatest:
                    inflections = processed.loc[k,fit+"Inflections"]
                    if len(inflections) > 1:
                        deriv_arr = np.asarray(processed.loc[k,fit+"Deriv"])
                        inf_deriv = deriv_arr[inflections]
                        dic_inf = dict(zip(inf_deriv,inflections))
                        slopes = processed.loc[k,fit+"Slopes"]
                        inf_max = dic_inf[np.nanmax(list(dic_inf.keys()))]
                        dic_slopes = dict(zip(inflections,slopes))
                        slope = dic_slopes[inf_max]
                    elif len(inflections) > 0:
                        inf_max = processed.loc[k,fit+"Inflections"][0]
                        slope = processed.loc[k,fit+"Slopes"][0]
                    else:
                        inf_max = np.nan
                        slope = np.nan
                    processed.at[k,fit+"InfMax"] = inf_max
                    processed.at[k,fit+"SlopeMax"] = slope
                    # Set default Tm to inflection point with maximum height
                    processed.at[k,fit+"Tm"] = inf_max

                    transition = None
                    if not pd.isna(inf_max):
                        for dp in range(inf_max,0,-1):
                            if processed.loc[k,fit + "Deriv"][dp] < processed.loc[k,fit+"DerivBaseline"][dp]:
                                transition = processed.loc[k,fit][dp]
                                break
                        tmguess = processed.loc[k,"Temp"][inf_max]
                    else:
                        tmguess = middle_of_list(processed.loc[k,"Temp"])
                    pars, confidence, stderr, success = ff.fit_tm_boltzmann(processed.loc[k,"Temp"],
                                                                           processed.loc[k,fit],
                                                                           tmguess,
                                                                           transition)
                    if pars[0] > np.nanmax(processed.loc[k,"Temp"]):
                        pars = [np.nan] * 4
                        drawn = [np.nan] * len(processed.loc[k,"Temp"])
                    else:
                        drawn = ff.draw_tm_boltzmann(processed.loc[k,"Temp"],pars)
                    processed.at[k,fit+"FitPars"] = pars
                    processed.at[k,fit+"Fit"] = drawn

                # If there is no fit at all, set DoFit to False (default was True)
                if (np.isnan(processed.loc[k,"NormFitPars"]).any() and
                    np.isnan(processed.loc[k,"RawFitPars"]).any() and
                    np.isnan(processed.at[k,"NormInfMax"]) and 
                    np.isnan(processed.at[k,"RawInfMax"])):
                    processed.loc[k,"DoFit"] = False


                #if processed.loc[k,"Method"] == "Thompson":
                #    pars, confidence, stderr, success = ff.fit_tm_thompson(processed.loc[k,"Temp"],processed.loc[k,"Raw"])
                #    processed.at[k,"FitPars"] = pars
                #    processed.at[k,"Fit"] = ff.draw_tm_thompson(processed.loc[k,"Temp"],pars)

            processed.loc[k,"Show"] = 0
            dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, f"{ProgressGauge(k+1,int_Samples)} {k+1} out of {int_Samples} samples.")
    # Calculate DTms:
    # Make dataframe to calculate average Tm of references
    lst_Proteins = list(set(dfr_Layout["ProteinID"]))
    n = len(lst_Proteins)
    references = pd.DataFrame(data={"n":[0]*n,
                                    "TmRawSum":[0]*n,
                                    "AverageTmRaw":[0]*n,
                                    "TmNormSum":[0]*n,
                                    "AverageTmNorm":[0]*n})
    # Need to initialise these with 0 to make the += work later.
    for i in range(len(lst_Proteins)):
        references.at[i,"TmSum"] = 0
        references.at[i,"n"] = 0
        references.at[i,"AverageTm"] = 0
    # Sum up Tms of references
    for idx in processed.index:
        if not pd.isna(processed.loc[idx,"Well"]):
            well = pf.well_to_index(processed.loc[idx,"Well"], wells)
            if dfr_Layout.loc[well,"WellType"] == "r":
                if processed.loc[well,"Method"] == "Derivative":
                    tm_Raw = processed.loc[well,"RawInfMax"]
                    tm_Raw = processed.loc[well,"Temp"][tm_Raw]
                    tm_Norm = processed.loc[well,"NormInfMax"]
                    tm_Norm = processed.loc[well,"Temp"][tm_Norm]
                else:
                    tm_Raw = processed.loc[well,"RawFitPars"][0]
                    tm_Norm = processed.loc[well,"NormFitPars"][0]
                references.at[int(dfr_Layout.loc[well,"ProteinNumerical"]),"TmRawSum"] += tm_Raw
                references.at[int(dfr_Layout.loc[well,"ProteinNumerical"]),"TmNormSum"] += tm_Norm
                references.at[int(dfr_Layout.loc[well,"ProteinNumerical"]),"n"] += 1
    # Average Tms of references
    for ref in references.index:
        if references.loc[ref,"n"] > 0:
            references.at[ref,"AverageTmRaw"] = round(references.loc[ref,"TmRawSum"]/references.loc[ref,"n"],2)
            references.at[ref,"AverageTmNorm"] = round(references.loc[ref,"TmNormSum"]/references.loc[ref,"n"],2)
            # get DTms of samples
            for proc in processed.index:
                well = pf.well_to_index(processed.loc[proc,"Well"], wells)
                if processed.loc[well,"Method"] == "Derivative":
                    tm_Raw = processed.loc[well,"RawInfMax"]
                    if not pd.isna(tm_Raw):
                        tm_Raw = processed.loc[proc,"Temp"][tm_Raw]
                    tm_Norm = processed.loc[well,"NormInfMax"]
                    if not pd.isna(tm_Norm):
                        tm_Norm = processed.loc[proc,"Temp"][tm_Norm]
                else:
                    tm_Raw = processed.loc[well,"RawFitPars"][0]
                    tm_Norm = processed.loc[well,"NormFitPars"][0]
                if not pd.isna(tm_Raw):
                    processed.at[proc,"RawDTm"] = round(tm_Raw - references.loc[int(dfr_Layout.loc[well,"ProteinNumerical"]),"AverageTmRaw"],2)
                if not pd.isna(tm_Norm):
                    processed.at[proc,"NormDTm"] = round(tm_Norm - references.loc[int(dfr_Layout.loc[well,"ProteinNumerical"]),"AverageTmNorm"],2)
        else:
            dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, "No reference wells have been defined for protein " + lst_Proteins[i] + ". Only melting temperatures, not Tm shifts, were calculated.")

    return processed, references

def create_Database_frame_DSF_Platemap(details, lstHeaders, dfr_PlateData, dfr_Layout):
        # Filter out controls:
    dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
    # Create partial Database frame
    dfr_PlateMap = pd.DataFrame(columns=lstHeaders,index=range(dfr_PlateData.shape[0]))
    # Go through dfr_PlateData and write into dfPatial
    for i in range(len(dfr_PlateData)):

        dfr_PlateMap.iloc[i,0] = dfr_Layout.loc["PlateID"] #"PlateID"
        if details["AssayType"] == "nanoDSF":
            dfr_PlateMap.iloc[i,1] = dfr_Layout.loc["PlateID"] + pf.index_to_well(dfr_PlateData.loc[i,"CapIndex"]+1,96) #"PlateWell ID"
        else:
            dfr_PlateMap.iloc[i,1] = str(dfr_Layout.loc["PlateID"]) + dfr_PlateData.loc[i,"Well"] #"PlateWell ID"
        dfr_PlateMap.iloc[i,2] = "Plate Parent"
        dfr_PlateMap.iloc[i,3] = dfr_PlateData.loc[i,"SampleID"] # "SGC Global Compound ID"
        dfr_PlateMap.iloc[i,4] = "Well concentration(mM)"
        dfr_PlateMap.iloc[i,5] = "Neccesary additive"
        dfr_PlateMap.iloc[i,6] = "Plate well: plate active"
        dfr_PlateMap.iloc[i,7] = "Plate well purpose"
        dfr_PlateMap.iloc[i,8] = "Plate well comments"
    
    return dfr_PlateMap

def recalculate_fit_DSF(sample):

    sample = sample.to_dict()

    if sample["Method"] == "Boltzmann":
        # Find boundaries for fit!
        # find intersection of derivative and its calculated baseline left of maximum
        for fit in ["Raw","Norm"]:
            tm = sample[fit+"InfMax"]
            transition = None
            for dp in range(sample["RawInflections"][0],0,-1):
                if sample["RawDeriv"][dp] < sample["RawDerivBaseline"][dp]:
                    transition = sample[fit][dp]
                    break
            pars, confidence, stderr, sucess = ff.fit_tm_boltzmann(sample["Temp"],
                                                                   sample[fit],
                                                                   sample["Temp"][tm],
                                                                   transition)
            sample[fit+"FitPars"] = pars
            sample[fit+"Fit"] = ff.draw_tm_boltzmann(sample["Temp"],pars)
    elif sample["Method"] == "Thompson":
        for fit in ["Raw","Norm"]:
            tm = sample[fit+"InfMax"]
            pars, confidence, stderr, sucess = ff.fit_tm_thompson(sample["Temp"],
                                                                  sample[fit],
                                                                  sample["Temp"][tm])
            sample[fit + "FitPars"] = pars
            sample[fit + "Fit"] = ff.draw_tm_thompson(sample["Temp"],pars)

    # 2. Push dfr_Sample back to CompleteContainer
    return pd.Series(sample)

def write_Tm(flt_Tm, bol_DoFit, flt_PlusMinus):
    # Cannot do a direct type check as the curve fit returns numpy.float64.
    # When I read it in after saving the file it comes back as python native float and I have not figured out a sensible way to convert, yet.
    if bol_DoFit == False or str(type(flt_Tm)).find("float") == -1: # actually calculated values seem to be numpy.float64?
        return "N.D."
    else:
        # Convert Tm from K to C
        return str(round(flt_Tm-273.15, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus, 1)) + " " + chr(176) + "C"

def write_Enthalpy(flt_H, bol_DoFit, flt_PlusMinus):
    # Cannot do a direct type check as the curve fit returns numpy.float64.
    # When I read it in after saving the file it comes back as python native float and I have not figured out a sensible way to convert, yet.
    if bol_DoFit == False or str(type(flt_H)).find("float") == -1: # actually calculated values seem to be numpy.float64?
        return "N.D."
    else:
        # Convert from J to kJ
        return str(round(flt_H/1000, 2)) + " " + chr(177) + " " + str(round(flt_PlusMinus/1000, 2)) + " kJ/mol"

##########################################################################
##                                                                      ##
##    ##  ##   ####   ##  ##   ####           #####    #####  ######    ##
##    ### ##  ##  ##  ### ##  ##  ##          ##  ##  ##      ##        ##
##    ######  ######  ######  ##  ##  ######  ##  ##   ####   ####      ##
##    ## ###  ##  ##  ## ###  ##  ##          ##  ##      ##  ##        ##
##    ##  ##  ##  ##  ##  ##   ####           #####   #####   ##        ##
##                                                                      ##
##########################################################################

def complete_container_nanoDSF(data_path,assay_category,bol_PlateID,dfr_Capillaries,dfr_Layout,dlg_progress):
    dlg_progress.lbx_Log.InsertItems(["Assay category: " + assay_category], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)

    dfr_Container = pd.DataFrame(columns=["Destination","Samples","Capillaries","DataFile",
        "RawData","Processed","Layout","References"], index=range(1))

    for idx_Set in dfr_Container.index:
        dlg_progress.lbx_Log.InsertItems([f"Processing capillary set {idx_Set + 1}"], dlg_progress.lbx_Log.Count)
        dfr_Container.loc[idx_Set,"Destination"] = f"CapillarySet_{idx_Set+1}"
        dfr_Container.loc[idx_Set,"DataFile"] = data_path
        dfr_Container.at[idx_Set,"RawData"] = ro.get_prometheus_readout(data_path)
        if dfr_Container.loc[idx_Set,"RawData"] is None: # == False:
            msg.warn_not_datafile(None)
            return None
        dfr_Container.at[idx_Set,"Samples"] = pd.DataFrame({"CapillaryIndex":dfr_Container.loc[idx_Set,"RawData"]["CapIndex"].to_list(),
            "CapillaryName":dfr_Container.loc[idx_Set,"RawData"]["CapillaryName"].to_list()})
        dfr_Container.at[idx_Set,"Layout"] = dfr_Layout
        dfr_Container.at[idx_Set,"Processed"], dfr_Container.at[idx_Set,"References"] = create_dataframe_nanoDSF(dfr_Container.loc[idx_Set,"RawData"],dfr_Capillaries,dfr_Layout.loc[idx_Set],dlg_progress)

    return dfr_Container

def create_dataframe_nanoDSF(raw_data, capillaries, layout, dlg_progress):
    # raw_data is dfr_Prometheus
    raw_data = raw_data[raw_data["CapillaryName"] != "no capillary"]
    int_Samples = raw_data.shape[0]
    lst_Columns = ["CapillarySet","CapillaryName","SampleID","SampleConc","PurificationID","ProteinConc","Buffer","CapIndex","Temp",
        "Ratio","RatioDeriv","RatioInflections","RatioSlopes",
        "330nm","330nmDeriv","330nmInflections","330nmSlopes",
        "350nm","350nmDeriv","350nmInflections","350nmSlopes",
        "Scattering","ScatteringDeriv","ScatteringInflections","ScatteringSlopes",
        "NormDTm","Show","DoFit"]
    processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))

    processed["CapillaryName"] = raw_data["CapillaryName"]
    processed["SampleID"] = capillaries["SampleID"].apply(string_or_na)
    processed["SampleConc"] = capillaries["SampleConc"].apply(string_or_na)
    processed["PurificationID"] = capillaries["PurificationID"].apply(string_or_na)
    processed["ProteinConc"] = capillaries["ProteinConc"].apply(string_or_na)
    processed["Buffer"] = capillaries["Buffer"].apply(string_or_na)
    processed["CapIndex"] = raw_data["CapIndex"]
    processed["Temp"] = raw_data["Temp"]
    processed["Ratio"] = raw_data["Ratio"]
    processed["330nm"] = raw_data["330nm"]
    processed["350nm"] = raw_data["350nm"]
    processed["Scattering"] = raw_data["Scattering"]

    dlg_progress.lbx_Log.InsertItems([f"Number of samples to process: {int_Samples}"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([f"Processed 0 out of {int_Samples} samples"], dlg_progress.lbx_Log.Count)

    k = -1
    for cap in range(int_Samples):
        k += 1
        processed.at[cap,"RatioDeriv"],processed.at[cap,"RatioInflections"],processed.at[cap,"RatioSlopes"] = ff.derivative(raw_data.loc[cap,"Temp"], raw_data.loc[cap,"Ratio"],2,2,"both")
        processed.at[cap,"330nmDeriv"],processed.at[cap,"330nmInflections"],processed.at[cap,"330nmSlopes"] = ff.derivative(raw_data.loc[cap,"Temp"], raw_data.loc[cap,"330nm"],2,2,"both")
        processed.at[cap,"350nmDeriv"],processed.at[cap,"350nmInflections"],processed.at[cap,"350nmSlopes"] = ff.derivative(raw_data.loc[cap,"Temp"], raw_data.loc[cap,"350nm"],2,2,"both")
        processed.at[cap,"ScatteringDeriv"],processed.at[cap,"ScatteringInflections"],processed.at[cap,"ScatteringSlopes"] = ff.derivative(raw_data.loc[cap,"Temp"], raw_data.loc[cap,"Scattering"],2,2,"both")
        dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, f"{ProgressGauge(k+1,int_Samples)} {k+1} out of {int_Samples} samples.")

    # Calculate DTms:
    # Make dataframe to calculate average Tm of references
    lst_Proteins = list(set(layout.loc["ProteinID"]))
    references = pd.DataFrame(columns=["TmSum","n","AverageTm"], index=(range(len(lst_Proteins))))
    # Since the protein assignment works differently here (at least at the moment), we will have to iterate through to assign the numerical:
    for cap in processed.index:
        for prot in range(len(lst_Proteins)):
            if layout.loc["ProteinID"][cap] == lst_Proteins[prot]:
                layout.loc["ProteinNumerical"][cap] = prot+1
    # Need to initialise these with 0 to make the += work later.
    for i in range(len(lst_Proteins)):
        references.at[i,"TmSum"] = 0
        references.at[i,"n"] = 0
        references.at[i,"AverageTm"] = 0
    # Sum up Tms of references
    for cap in processed.index:
        if layout["WellType"][cap] == "r":
            references.at[int(layout["ProteinNumerical"][cap])-1,"TmSum"] += processed.loc[cap,"RatioInflections"][0]
            references.at[int(layout["ProteinNumerical"][cap])-1,"n"] += 1
    # Average Tms of references
    for ref in references.index:
        if references.loc[ref,"n"] > 0:
            references.at[ref,"AverageTm"] = round(references.loc[ref,"TmSum"]/references.loc[ref,"n"],2)
            # get DTms of samples
            for cap in processed.index:
                processed.at[cap,"NormDTm"] = round(processed.loc[cap,"RatioInflections"][0] - references.loc[int(layout["ProteinNumerical"][cap])-1,"AverageTm"],2)
        else:
            dlg_progress.lbx_Log.InsertItems(["No reference capillaries have been defined for protein " + lst_Proteins[i] + ". Only melting temperatures, not Tm shifts, were calculated."],
                dlg_progress.lbx_Log.Count)

    return processed, references

##########################################
##                                      ##
##    #####    ####   ######  ######    ##
##    ##  ##  ##  ##    ##    ##        ##
##    #####   ######    ##    ####      ##
##    ##  ##  ##  ##    ##    ##        ##
##    ##  ##  ##  ##    ##    ######    ##
##                                      ##
##########################################

def create_dataframe_rate(raw_data, dfr_Samples, dfr_Layout, dlg_progress):
    """
        Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
        and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
        to calculate values based on the assay type.
    """
    # This function is called per plate, so there will only be one plate name
    str_PlateName = dfr_Samples.loc[0,"Destination"]
    #fltAssayVolume = float(assay_volume)
    k = 0
    dlg_progress.lbx_Log.InsertItems([f"Number of samples to process: {dfr_Samples.shape[0]}"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([f"Processed 0 out of {dfr_Samples.shape[0]} samples"], dlg_progress.lbx_Log.Count)

    dfr_Processed = pd.DataFrame(columns = ["Destination",
                                            "Concentrations",
                                            "Locations",
                                            "SampleID",
                                            "Time",
                                            "Signal",
                                            "DoFit",
                                            "Window",
                                            "RawFit",
                                            "Show",
                                            "vi",
                                            "viError",
                                            "RateFit"],
                                  index = dfr_Samples.index)

    equation = ff.eq_logMM

    references = pd.DataFrame(columns=[0],index=["SolventMean","SolventMedian","SolventSEM","SolventSTDEV","SolventMAD",
        "BufferMean","BufferMedian","BufferSEM","BufferSTDEV","BufferMAD",
        "ControlMean","ControlMedian","ControlSEM","ControlSTDEV","ControlMAD",
        "ZPrimeMean","ZPrimeMedian"])

    ref_names = {"Solvent":"r","Buffer":"b","Control":"c"}
    for ref in ref_names.keys():
        wells = list(dfr_Layout[dfr_Layout["WellType"] == ref_names[ref]].index)
        if len(wells) > 0:
            refs = []
            for well in wells:
                fit, pars, ci, err, r2, success = ff.fit_any(equation,
                                                             xdata = raw_data.loc[well,"Time"],
                                                             ydata = raw_data.loc[well,"Signal"],
                                                             window = (0,150))
                vi = pars[1]/pars[2]
                if vi < 0:
                    vi = 0
                refs.append(vi)
            if any_nonnan(refs):
                references.loc[ref+"Mean",0] = np.nanmean(refs)
                references.loc[ref+"Median",0] = np.nanmedian(refs)
                references.loc[ref+"SEM",0] = np.std(refs)
                references.loc[ref+"MAD",0] = mad(refs)
                #if we get np.nan in one of the errors/deviations, set to 0:
                for meas in ["SEM","MAD"]:
                    if pd.isna(references.loc[ref+meas,0]):
                        references.loc[ref+meas,0] = 0
            else:
                references.loc[ref+"Mean",0] = np.nan
                references.loc[ref+"Median",0] = np.nan
                references.loc[ref+"SEM",0] = np.nan
                references.loc[ref+"MAD",0] = np.nan
        else:
            references.loc[ref+"Mean",0] = np.nan
            references.loc[ref+"Median",0] = np.nan
            references.loc[ref+"SEM",0] = np.nan
            references.loc[ref+"MAD",0] = np.nan

    references.loc["ZPrimeMean", 0] = 1 - (3 * (references.loc["SolventSEM",0] + references.loc["ControlSEM",0]) / abs(references.loc["SolventMean",0] - references.loc["ControlMean",0]))
    references.loc["ZPrimeMedian", 0] = 1 - (3 * (references.loc["SolventMAD",0] + references.loc["ControlMAD",0]) / abs(references.loc["SolventMedian",0] - references.loc["ControlMedian",0]))

    for smpl in dfr_Samples.index:
        dfr_Processed.at[smpl,"Concentrations"] = dfr_Samples.loc[smpl,"Concentrations"]
        dfr_Processed.at[smpl,"Locations"] = dfr_Samples.loc[smpl,"Locations"]
        dfr_Processed.at[smpl,"Destination"] = str_PlateName
        dfr_Processed.at[smpl,"SampleID"] = dfr_Samples.loc[smpl,"SampleID"]
        dfr_Processed.at[smpl,"Time"] = raw_data.loc[dfr_Samples.loc[smpl,"Locations"][0][0],"Time"] # time is the same for all
        dfr_Processed.at[smpl,"Show"] = 0
        dfr_Processed.at[smpl,"Window"] = (0,150)

        time = []
        signal = []
        mean = []
        stdev = []
        raw_vi = []
        raw_fit = []
        raw_fit_pars = []
        raw_vi_error = []
        raw_r_square = []

        c = 0
        for conc in range(len(dfr_Samples.loc[smpl,"Concentrations"])):
            # I here we also make lists for creating the dataframe
            # -> lists are lists of list, with outermost list having
            # the length of the number of concentrations
            wells = dfr_Samples.loc[smpl,"Locations"][conc]
            time.append(dfr_Processed.at[smpl,"Time"])
            c_signal = []
            for tp in range(len(dfr_Processed.at[smpl,"Time"])):
                c_signal.append([raw_data.loc[w,"Signal"][tp] for w in wells])
            signal.append(c_signal)
            mean.append([np.nanmean(sig) for sig in c_signal])
            stdev.append([np.nanstd(sig) for sig in c_signal])

            rfit, rfp, rfci, rfe, rfr2, rs = ff.fit_any(equation,
                    xdata = time[c],
                    ydata = mean[c],
                    window = dfr_Processed.loc[smpl,"Window"])

            c += 1

            if rs == True:
                raw_vi.append(rfp[1]/rfp[2])
                # Propagation of uncertainty -> https://en.wikipedia.org/wiki/Propagation_of_uncertainty
                f1 = 1/rfp[2]
                f2 = -1*rfp[1]*(rfp[2]**(-2))
                vi_sigma = abs((abs(f1)**2)*((rfe[1])**2) + (abs(f2)*(rfe[2])**2) + (2*f1*f2*rfe[1]/rfp[1]*rfe[2]))
                raw_vi_error.append(vi_sigma)
                raw_fit.append(rfit)
                raw_fit_pars.append(rfp)
                raw_r_square.append(rfr2)
            else:
                raw_vi.append(np.nan)
                raw_vi_error.append(np.nan)
                raw_fit.append([np.nan] * len(time))
                raw_fit_pars.append([np.nan]*3)
                raw_r_square.append(np.nan)
        
        dfr_Processed.at[smpl,"Signal"] = pd.DataFrame(data={"Time":time,
                                                          "Signal":signal,
                                                          "Mean":mean,
                                                          "STDEV":stdev,
                                                          "Fit":raw_fit})

        dfr_Processed.at[smpl,"Fit"] = pd.DataFrame(data={"Pars":raw_fit_pars,
                                                          "RSquare":raw_r_square,
                                                          "vi":raw_vi,
                                                          "vi_error":raw_vi_error})

        vi_min = np.nanmin(raw_vi)
        vi_max = np.nanmax(raw_vi)
        norm_vi = [100*(vi-vi_min)/(vi_max-vi_min) for vi in raw_vi]
        
        vi_fit, vi_pars, vi_ci, vi_err, vi_r_square, vi_success = ff.fit_sigmoidal_free(
                                                        doses = dfr_Samples.loc[smpl,"Concentrations"],
                                                        responses = norm_vi)
        vi_excluded = [False] * len(dfr_Processed.at[smpl,"Concentrations"])
        
        dfr_Processed.at[smpl,"RateFit"] = {"Concentrations":dfr_Samples.loc[smpl,"Concentrations"],
                                            "vi":raw_vi,
                                            "viNorm":norm_vi,
                                            "DoFit":True,
                                            "Fit":vi_fit,
                                            "Pars":vi_pars,
                                            "CI":vi_ci,
                                            "Error":raw_vi_error,
                                            "Excluded":vi_excluded,
                                            "RSquare":vi_r_square}

        
        dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, f"{ProgressGauge(k+1,dfr_Samples.shape[0])} {k+1} out of {dfr_Samples.shape[0]} samples.")
        k += 1

    # Return
    return dfr_Processed, references

def recalculate_primary_fit(owner, plate, smpl, window, do_return = False):

    dataset = owner.assay_data.loc[plate,"Processed"].loc[smpl].to_dict()
    references = owner.assay_data.loc[plate,"References"]

    if not window is None:
        dataset["Window"] = window

    #refit the vis for each concentration
    do_raw_fit = []
    raw_fit = []
    raw_fit_pars = []
    raw_fit_ci = []
    raw_fit_errors = []
    raw_r_square = []
    raw_vi = []
    raw_vi_error = []
    success_raw = []
    success_norm = []

    for conc in dataset["Signal"].index:
        rfit, rfp, rfci, rfe, rfr2, rs = ff.fit_any(ff.eq_logMM,
                xdata = dataset["Signal"].loc[conc,"Time"],
                ydata = dataset["Signal"].loc[conc,"Mean"],
                window = window)
        raw_fit_pars.append(rfp) # will all be nan if fit failed
        if rs == True:
            rfit = ff.draw_any(ff.eq_logMM, dataset["Signal"].loc[conc,"Time"], rfp)
            raw_fit.append(rfit)
            raw_r_square.append(ff.calculate_rsquare(dataset["Signal"].loc[conc,"Mean"], rfit))
            do_raw_fit.append(True)
            raw_vi.append(rfp[1]/rfp[2])
            # Propagation of uncertainty -> https://en.wikipedia.org/wiki/Propagation_of_uncertainty
            f1 = 1/rfp[2]
            f2 = -1*rfp[1]*(rfp[2]**(-2))
            vi_sigma = abs((abs(f1)**2)*((rfe[1])**2) + (abs(f2)*(rfe[2])**2) + (2*f1*f2*rfe[1]/rfp[1]*rfe[2]))
            raw_vi_error.append(abs(vi_sigma/rfp[1]/rfp[2]))
        else:
            raw_fit.append([np.nan] * len(dataset["Signal"].loc[conc,"Time"]))
            raw_r_square.append(np.nan)
            do_raw_fit.append(False)
            raw_vi.append(np.nan)
            raw_vi_error.append(np.nan)

    dataset["DoFit"] = do_raw_fit
    dataset["vi"] = raw_vi

    dataset["Signal"] = pd.DataFrame(data={"Time":dataset["Signal"]["Time"].to_list(),
                                           "Signal":dataset["Signal"]["Signal"].to_list(),
                                           "Mean":dataset["Signal"]["Mean"].to_list(),
                                           "STDEV":dataset["Signal"]["STDEV"].to_list(),
                                           "Fit":raw_fit})

    dataset["Fit"] = pd.DataFrame(data={"Pars":raw_fit_pars,
                                        "RSquare":raw_r_square,
                                        "vi":raw_vi,
                                        "vi_error":raw_vi_error})

    vi_min = references.loc["ControlMean",0]
    vi_max = references.loc["SolventMean",0] - vi_min
    norm_vi = [(vi-vi_min)/vi_max*100 for vi in raw_vi]

    vi_excluded = []
    for vi in range(len(norm_vi)):
        if dataset["RateFit"]["Excluded"][vi] == False:
            vi_excluded.append(norm_vi[vi])
        else:
            vi_excluded.append(np.nan)

    vi_fit, vi_pars, vi_ci, vi_err, vi_r_square, vi_success = ff.fit_sigmoidal_free(dataset["Concentrations"], vi_excluded)
        
    dataset["RateFit"] = {"Concentrations":dataset["Concentrations"],
                          "vi":raw_vi,
                          "viNorm":norm_vi,
                          "DoFit":True,
                          "Fit":vi_fit,
                          "Pars":vi_pars,
                          "CI":vi_ci,
                          "Error":raw_vi_error,
                          "Excluded":dataset["RateFit"]["Excluded"],
                          "RSquare":vi_r_square}
    
    dataset = pd.Series(dataset)

    # return dataset back to assay_data
    owner.assay_data.loc[plate,"Processed"].loc[smpl] = dataset

    if do_return == True:
        return dataset

def recalculate_secondary_fit(owner, plate, smpl, do_return = False):

    dataset = owner.assay_data.loc[plate,"Processed"].loc[smpl].to_dict()

    vi_excluded = []
    for vi in range(len(dataset["RateFit"]["viNorm"])):
        if dataset["RateFit"]["Excluded"][vi] == False:
            vi_excluded.append(dataset["RateFit"]["viNorm"][vi])
        else:
            vi_excluded.append(np.nan)

    vi_fit, vi_pars, vi_ci, vi_err, vi_r_square, vi_success = ff.fit_sigmoidal_free(dataset["Concentrations"], vi_excluded)
        
    dataset["RateFit"] = {"Concentrations":dataset["Concentrations"],
                          "vi":dataset["RateFit"]["vi"],
                          "viNorm":dataset["RateFit"]["viNorm"],
                          "DoFit":vi_success,
                          "Fit":vi_fit,
                          "Pars":vi_pars,
                          "CI":vi_ci,
                          "Error":dataset["RateFit"]["Error"],
                          "Excluded":dataset["RateFit"]["Excluded"],
                          "RSquare":vi_r_square}
    
    dataset = pd.Series(dataset)

    # return dataset back to assay_data
    owner.assay_data.at[plate,"Processed"].loc[smpl] = dataset

    if do_return == True:
        return dataset

def recalculate_fit_rate(sample_data):
    # Re-fit
    vi_fit, vi_pars, vi_ci, vi_err, vi_r_square, vi_success = ff.fit_sigmoidal_free(sample_data["Concentrations"], sample_data["vi"])

    return {"Concentrations":sample_data["Concentrations"].copy(),
            "vi":sample_data["vi"].copy(),
            "Fit":vi_fit,
            "Pars":vi_pars,
            "CI":vi_ci,
            "Error":vi_err,
            "Excluded":sample_data["Excluded"].copy(),
            "RSquare":vi_r_square}

def write_Rate(flt_Rate, bol_DoFit, flt_PlusMinus):
    # Cannot do a direct type check as the curve fit returns numpy.float64.
    # When I read it in after saving the file it comes back as python native float and I have not figured out a sensible way to convert, yet.
    if bol_DoFit == False or str(type(flt_Rate)).find("float") == -1: # actually calculated values seem to be numpy.float64?
        return "N.D."
    else:
        return str(round(flt_Rate, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus, 1)) + " 1/s"


##########################################
##                                      ##
##     #####  #####    #####   #####    ##
##    ##      ##  ##  ##      ##        ##
##    ##      #####   ##       ####     ##
##    ##      ##  ##  ##          ##    ##
##     #####  #####    #####  #####     ##
##                                      ##
##########################################

def complete_container_CBCS(dfr_DataStructure, dfr_Layout, dlg_progress, lst_Concentrations, lst_Conditions, str_ReferenceCondition, lst_Replicates, str_DataProcessor):

    #assay_data = pd.DataFrame(index=[0],columns=["Column"])

    #assay_data.at[0,"Column"] = create_dataframe_CBCS(dfr_DataStructure, dfr_Layout, dlg_progress, lst_Concentrations, lst_Conditions, lst_Replicates)
    # read raw data
    int_Plates = dfr_DataStructure.shape[0]
    dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems(["Reading raw data files:"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([f"0 out of {int_Plates} files read."], dlg_progress.lbx_Log.Count)
    k = 0
    dlg_progress.currentitems = int_Plates
    for idx in dfr_DataStructure.index:
        dfr_DataStructure.at[idx,"RawData"] = ro.get_operetta_readout(dfr_DataStructure.loc[idx,"FilePath"], str_DataProcessor)
        if dfr_DataStructure.at[idx,"RawData"] is None:
            msg.warn_files_not_loaded()
            dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
            dlg_progress.lbx_Log.InsertItems(["Processing aborted, could not load files."], dlg_progress.lbx_Log.Count)
            return None, None, None
        dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Plates) + " " + str(k+1) + " out of " + str(int_Plates) + " files read.")
        k += 1

    return create_dataframe_CBCS(dfr_DataStructure, dfr_Layout, dlg_progress, lst_Concentrations, lst_Conditions, str_ReferenceCondition, lst_Replicates)


def create_dataframe_CBCS(dfr_DataStructure, dfr_Layout, dlg_progress, lst_Concentrations, lst_Conditions, str_ReferenceCondition, lst_Replicates):

    dfr_ReferenceLocations = CBCS_get_references(dfr_Layout)
    str_ZPrimeControl = CBCS_find_ZPrime(dfr_Layout)

    wells = dfr_DataStructure.loc[dfr_DataStructure.index[0],"RawData"].shape[0]

    # Normalise data and determine control values:
    int_Plates = dfr_DataStructure.shape[0]
    dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems(["Normalising plates:"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([f"0 out of {int_Plates} plates normalised."], dlg_progress.lbx_Log.Count)

    k = 0
    for idx in dfr_DataStructure.index:
        dfr_DataStructure.at[idx,"Normalised"], dfr_DataStructure.at[idx,"Controls"] = CBCS_normalise_plate(dfr_DataStructure.loc[idx,"RawData"], dfr_ReferenceLocations)
        dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Plates) + " " + str(k+1) + " out of " + str(int_Plates) + " plates normalised.")
        k += 1

    lst_ConcIndices = []
    lst_CondIndices = []
    for conc in lst_Concentrations:
        for cond in lst_Conditions:
            lst_ConcIndices.append(conc)
            lst_CondIndices.append(cond)
    lst_Indices = [lst_ConcIndices, lst_CondIndices]
    dfr_Processed = pd.DataFrame(index=lst_Indices,columns=["Data","PerCent","Controls",
                                                            "m","c","RSquare","Pearson",
                                                            "ZPrimeMean","ZPrimeMedian"])

    # process normalised data
    int_Conditions = len(lst_CondIndices)
    k = 0
    dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems(["Processing conditions:"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([f"0 out of {int_Conditions} conditions processed."], dlg_progress.lbx_Log.Count)
    for conc in lst_Concentrations:
        for cond in lst_Conditions:
            # Prepare empty lists:
            lst_RawMean = [np.nan] * wells
            lst_NormMean = [np.nan] * wells
            lst_NormMedian = [np.nan] * wells
            lst_NormSTDEV = [np.nan] * wells
            lst_NormMAD = [np.nan] * wells
            lst_NormMeanPerCent = [np.nan] * wells
            lst_ZScore = [np.nan] * wells
            lst_DeltaZScore = [np.nan] * wells

            # process wells:
            for well in range(wells):
                lst_RawValues = []
                lst_NormValues = []
                lst_PerCentValues = []
                for rep in lst_Replicates:
                    idx = (conc,cond,rep)
                    lst_RawValues.append(dfr_DataStructure.loc[idx,"RawData"].loc[well,"Readout"])
                    lst_NormValues.append(dfr_DataStructure.loc[idx,"Normalised"].loc[well,"Normalised"])
                    lst_PerCentValues.append(dfr_DataStructure.loc[idx,"Normalised"].loc[well,"PerCent"])
                # if there are only nan values, we don't need to write in the list
                # Check separately for raw values and normalised values as 
                # ZPrime values are calculated from raw values
                if any_nonnan(lst_RawValues) == True:
                    lst_RawMean[well] = np.nanmean(lst_RawValues)
                    lst_NormMeanPerCent[well] = np.nanmean(lst_PerCentValues)
                if any_nonnan(lst_NormValues) == True:
                    lst_NormMean[well] = np.nanmean(lst_NormValues)
                    lst_NormMedian[well] = np.nanmedian(lst_NormValues)
                    lst_NormSTDEV[well] = np.nanstd(lst_NormValues)
                    lst_NormMAD[well] = mad(lst_NormValues)

            dfr_Processed.loc[(conc,cond),"m"], dfr_Processed.loc[(conc,cond),"c"], dfr_Processed.loc[(conc,cond),"RSquare"], dfr_Processed.loc[(conc,cond),"Pearson"] = ff.calculate_repcorr(dfr_DataStructure.loc[(conc,cond,"R1"),"Normalised"]["PerCent"],
                dfr_DataStructure.loc[(conc,cond,"R2"),"Normalised"]["PerCent"])

            dfr_Processed.at[(conc,cond),"Controls"] = CBCS_calculate_controls(lst_RawMean, dfr_ReferenceLocations)
            #dfr_Processed.at[(conc,cond),"Controls"] = CBCS_calculate_controls(lst_NormMean, dfr_ReferenceLocations)

            dfr_Processed.loc[(conc,cond),"ZPrimeMean"] = dfr_Processed.at[(conc,cond),"Controls"].loc[str_ZPrimeControl,"ZPrimeMean"]
            dfr_Processed.loc[(conc,cond),"ZPrimeMedian"] = dfr_Processed.at[(conc,cond),"Controls"].loc[str_ZPrimeControl,"ZPrimeMedian"]
            

            dfr_Temp = dfr_Processed.at[(conc,cond),"Controls"] = CBCS_calculate_controls(lst_NormMean, dfr_ReferenceLocations)
            # Calculate ZScores
            dfr_Processed.loc[(conc,cond),"Controls"].loc["SamplePopulation","NormMean"] = dfr_Temp.loc["SamplePopulation","NormMean"]
            dfr_Processed.loc[(conc,cond),"Controls"].loc["SamplePopulation","NormSTDEV"] = dfr_Temp.loc["SamplePopulation","NormSTDEV"]
            pop_mean = dfr_Processed.loc[(conc,cond),"Controls"].loc["SamplePopulation","NormMean"]
            pop_stdev = dfr_Processed.loc[(conc,cond),"Controls"].loc["SamplePopulation","NormSTDEV"]
            # ZScore = ((value of sample i)-(mean of all samples))/(STDEV of population)
            for well in range(wells):
                lst_ZScore[well] = (lst_NormMean[well]-pop_mean)/pop_stdev

            dfr_Processed.at[(conc,cond),"Data"] = pd.DataFrame(data={"RawMean":lst_RawMean,
                                                                      "NormMean":lst_NormMean,
                                                                      "NormMedian":lst_NormMedian,
                                                                      "NormSTDEV":lst_NormSTDEV,
                                                                      "NormMAD":lst_NormMAD,
                                                                      "ZScore":lst_ZScore,
                                                                      "DeltaZScore":lst_DeltaZScore,
                                                                      "NormMeanPerCent":lst_NormMeanPerCent})

            dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Conditions) + " " + str(k+1) + " out of " + str(int_Conditions) + " conditions processed.")
            k += 1

    # get Delta Z Score:
    if not str_ReferenceCondition == None:
        k = 0
        dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
        dlg_progress.lbx_Log.InsertItems(["Calculating DeltaZScores for each condition:"], dlg_progress.lbx_Log.Count)
        dlg_progress.lbx_Log.InsertItems([f"0 out of {int_Conditions} conditions processed."], dlg_progress.lbx_Log.Count)
        for conc in lst_Concentrations:
            for cond in lst_Conditions:
                for well in range(wells):
                    dfr_Processed.loc[(conc,cond),"Data"].loc[well,"DeltaZScore"] = dfr_Processed.loc[(conc,cond),"Data"].loc[well,"ZScore"] - dfr_Processed.loc[(conc,str_ReferenceCondition),"Data"].loc[well,"ZScore"]
                dlg_progress.lbx_Log.SetString(dlg_progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Conditions) + " " + str(k+1) + " out of " + str(int_Conditions) + " conditions processed.")
                k += 1

    dfr_SampleInfo = pd.DataFrame(columns=["MaxDeltaZScore"],index=range(wells))

    # get largest change from
    for well in range(wells):
        dzs = []
        for conc in lst_Concentrations:
            for cond in lst_Conditions:
                dzs.append(dfr_Processed.loc[(conc,cond),"Data"].loc[well,"DeltaZScore"])
        if not np.count_nonzero(np.isnan(dzs)) == len(dzs):
            min = np.nanmin(dzs)
            max = np.nanmax(dzs)
            if abs(max) > abs(min):
                dfr_SampleInfo.loc[well,"MaxDeltaZScore"] = max
            else:
                dfr_SampleInfo.loc[well,"MaxDeltaZScore"] = min
        else:
            dfr_SampleInfo.loc[well,"MaxDeltaZScore"] = np.nan

    return dfr_DataStructure, dfr_Processed, dfr_SampleInfo

def CBCS_normalise_plate(dfr_RawData, dfr_ReferenceLocations):

    # This function normalises the raw data and returns the normalised data for sample population and
    # the reference/control values (i.e. the mean, median, STDEV, MAD of each reference/control)

    wells = dfr_RawData.shape[0]
    #dfr_Normalised = pd.DataFrame(index=range(wells),columns=["Row","Column","Readout"])

    # list of controls to exclude them from normalisation
    lst_SampleLocations = []
    try:
        lst_SampleLocations.extend(dfr_ReferenceLocations.loc["SamplePopulation","Locations"])
    except:
        None
    try:
        lst_SampleLocations.extend(dfr_ReferenceLocations.loc["Solvent","Locations"])
    except:
        None

    # get controls and solvent reference values
    dfr_Controls = CBCS_calculate_controls(dfr_RawData["Readout"], dfr_ReferenceLocations)

    # normalise as per-cent of solvent reference
    percent = []
    for well in range (wells):
        percent.append(round(100 * dfr_RawData.loc[well,"Readout"]/dfr_Controls.loc["Solvent","NormMean"],2))

    # Prepare dataframe to return data
    dfr_Return = pd.DataFrame(index=range(wells),data={"PerCent":percent,
                                                       "Normalised":dfr_RawData["Readout"].tolist(),
                                                       "Row":dfr_RawData["Row"].tolist(),
                                                       "Column":dfr_RawData["Column"].tolist()})

    # make dataframe for raw data that excludes all control compound wells:
    dfr_RawDataNoControls = dfr_RawData.filter(items=lst_SampleLocations, axis=0)

    # Normalise each well in a column against column median
    # Get each uniwue column and row
    columns = dfr_RawData["Column"].dropna().unique()
    rows = dfr_RawData["Row"].dropna().unique()

    normalise = True
    if normalise == True:
        # First: get median of each column -> save in dictionary with column as key
        dic_ColumnMedian = {}
        for col in columns:
            dic_ColumnMedian[col] = dfr_RawDataNoControls[dfr_RawDataNoControls["Column"]==col]["Readout"].median()
        # Second: normalise each well against the corresponding column's median
        for well in range(wells):
            if pd.isna(dfr_RawData.loc[well,"Column"]) == False:
                dfr_Return.loc[well,"Normalised"] = dfr_RawData.loc[well,"Readout"]/dic_ColumnMedian[dfr_RawData.loc[well,"Column"]]
        # Third: get median of each row after column normalisation, re-use dfr_RawDataNoControls -> save in dictionary with row as key
        dic_RowMedian = {}
        dfr_NormalisedByColumn = dfr_Return.filter(items=lst_SampleLocations, axis=0)
        for row in rows:
            dic_RowMedian[row] = dfr_NormalisedByColumn[dfr_NormalisedByColumn["Row"]==row]["Normalised"].median()
        # Fourth: normalise each well against the corresponding row's median
        for well in range(wells):
            if pd.isna(dfr_RawData.loc[well,"Row"]) == False:
                dfr_Return.loc[well,"Normalised"] = dfr_Return.loc[well,"Normalised"]/dic_RowMedian[dfr_Return.loc[well,"Row"]]

    return dfr_Return, dfr_Controls

def CBCS_get_references(dfr_Layout):
    
    lst_ControlNumericals = []
    lst_ControlIDs = []

    dfr_ReferenceLocations = pd.DataFrame(index=["Solvent","SamplePopulation"],columns=["Locations"])
    dfr_ReferenceLocations.at["Solvent","Locations"] = []
    dfr_ReferenceLocations.loc["SamplePopulation","Locations"] = []

    for w in dfr_Layout.loc[0,"Layout"].index:
        if dfr_Layout.loc[0,"Layout"].loc[w,"WellType"] == "r": # r = reference
            dfr_ReferenceLocations.loc["Solvent","Locations"].append(w)
        elif dfr_Layout.loc[0,"Layout"].loc[w,"WellType"] == "s": # s = sample
            dfr_ReferenceLocations.loc["SamplePopulation","Locations"].append(w)

    for w in dfr_Layout.loc[0,"Layout"].index:
        if not dfr_Layout.loc[0,"Layout"].loc[w,"ControlNumerical"] == "":
            if not dfr_Layout.loc[0,"Layout"].loc[w,"ControlNumerical"] in lst_ControlNumericals:
                lst_ControlNumericals.append(dfr_Layout.loc[0,"Layout"].loc[w,"ControlNumerical"])
                lst_ControlIDs.append(dfr_Layout.loc[0,"Layout"].loc[w,"ControlID"])
                dfr_ReferenceLocations.at[dfr_Layout.loc[0,"Layout"].loc[w,"ControlID"],"Locations"] = []
                dfr_ReferenceLocations.loc[dfr_Layout.loc[0,"Layout"].loc[w,"ControlID"],"Locations"].append(w)
            else:
                dfr_ReferenceLocations.loc[dfr_Layout.loc[0,"Layout"].loc[w,"ControlID"],"Locations"].append(w)

    return dfr_ReferenceLocations

def CBCS_find_ZPrime(dfr_Layout):
    # find zprime, this should be very quick:
    str_ZPrimeCtrl = "Control 1"
    for w in dfr_Layout.loc[0,"Layout"].index:
        if dfr_Layout.loc[0,"Layout"].loc[w,"ZPrime"] == True:
            str_ZPrimeCtrl = dfr_Layout.loc[0,"Layout"].loc[w,"ControlID"]
            # There can only be one control used for ZPrimes
            break

    return str_ZPrimeCtrl

def CBCS_calculate_controls(lst_Data, dfr_RefLoc):

    # Add new columns to dfr_ReferenceLocations and return it as dfr_Controls

    # go through each reference/control type
    for ref in dfr_RefLoc.index:
        lst = []
        for idx_Well in dfr_RefLoc.loc[ref,"Locations"]:
            lst.append(lst_Data[idx_Well])
        if any_nonnan(lst) == True:
            dfr_RefLoc.loc[ref,"NormMean"] = np.nanmean(lst)
            dfr_RefLoc.loc[ref,"NormMedian"] = np.nanmedian(lst)
            dfr_RefLoc.loc[ref,"NormMAD"] = mad(lst)
            dfr_RefLoc.loc[ref,"NormSTDEV"] = np.nanstd(lst)
        else:
            dfr_RefLoc.loc[ref,"NormMean"] = np.nan
            dfr_RefLoc.loc[ref,"NormMedian"] = np.nan
            dfr_RefLoc.loc[ref,"NormMAD"] = np.nan
            dfr_RefLoc.loc[ref,"NormSTDEV"] = np.nan
        dfr_RefLoc.loc[ref,"ZPrimeMean"] = np.nan
        dfr_RefLoc.loc[ref,"ZPrimeMedian"] = np.nan
    
    # Calculate Zprime values:
    for ref in dfr_RefLoc.index:
        if not ref == "Solvent":
            dfr_RefLoc.loc[ref,"ZPrimeMean"] = 1 - (3 * (dfr_RefLoc.loc["Solvent","NormSTDEV"] + dfr_RefLoc.loc[ref,"NormSTDEV"]) / abs(dfr_RefLoc.loc["Solvent","NormMean"] - dfr_RefLoc.loc[ref,"NormMean"]))
            dfr_RefLoc.loc[ref,"ZPrimeMedian"] = 1 - (3 * (dfr_RefLoc.loc["Solvent","NormMAD"] + dfr_RefLoc.loc[ref,"NormMAD"]) / abs(dfr_RefLoc.loc["Solvent","NormMedian"] - dfr_RefLoc.loc[ref,"NormMedian"]))

    return dfr_RefLoc

def create_database_frame_CBCS(dfr_Processed, concs, lst_Conditions, int_Wells):
    
    dic_RawMean = {conc: [] for conc in concs}
    dic_Normalised = {conc: [] for conc in concs}
    dic_PerCent = {conc: [] for conc in concs}
    dic_ZScore = {conc: [] for conc in concs}
    dic_DeltaZScore = {conc: [] for conc in concs}
    lst_Wells = pf.write_well_list(int_Wells)

    lst_IndexWells = []
    lst_IndexConditions = []
    for well in range(int_Wells):
        for cond in lst_Conditions:
            lst_IndexWells.append(lst_Wells[well])
            lst_IndexConditions.append(cond)
            for conc in concs:
                dic_RawMean[conc].append(dfr_Processed.loc[(conc,cond),"Data"].loc[well,"RawMean"])
                dic_Normalised[conc].append(dfr_Processed.loc[(conc,cond),"Data"].loc[well,"NormMean"])
                dic_PerCent[conc].append(dfr_Processed.loc[(conc,cond),"Data"].loc[well,"NormMeanPerCent"])
                dic_ZScore[conc].append(dfr_Processed.loc[(conc,cond),"Data"].loc[well,"ZScore"])
                dic_DeltaZScore[conc].append(dfr_Processed.loc[(conc,cond),"Data"].loc[well,"DeltaZScore"])

    # Create dictionary to prepare dataframe:
    dic_Data = {"Well":lst_IndexWells,"Condition":lst_IndexConditions}
    for conc in concs:
        dic_Data["Mean Raw ("+conc+")"] = dic_RawMean[conc]
    for conc in concs:
        dic_Data["Normalised ("+conc+")"] = dic_Normalised[conc]
    for conc in concs:
        dic_Data["Per-cent control ("+conc+")"] = dic_PerCent[conc]
    for conc in concs:
        dic_Data["ZScore ("+conc+")"] = dic_ZScore[conc]
    for conc in concs:
        dic_Data["DeltaZScore ("+conc+")"] = dic_DeltaZScore[conc]

    # Create dataframe

    return pd.DataFrame(data=dic_Data).dropna()