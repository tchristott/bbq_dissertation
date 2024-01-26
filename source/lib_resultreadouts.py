"""
Library of functions to read out results from devices, e.g. plate readers

Functions:
    get_bmg_list_readout
    get_bmg_list_namesonly
    get_bmg_plate_readout
    get_lightcycler_readout
    get_mxp_readout
    get_bmg_timecourse_readout
    get_bmg_DRTC_readout
    get_FLIPR_DRTC_readout
    get_prometheus_readout
    get_prometheus_capillaries
    get_operetta_readout

"""
import pandas as pd
import numpy as np
import lib_platefunctions as pf
import os

def get_bmg_list_readout(datafile: str, wells: int):
    """
    Parses list format BMG Pherastar output and writes it into
    a dataframe.
    
    Arguments:
        datafile -> string. Path of datafile.
        wells -> integer. Plate format in number of wells.
                 Permitted: 96, 384, 1536
    
    Returns:
        Pandas dataframe. Index is well, columns are plates in file
    """
    # Read file. Cells in PheraStar output are tab stop separated (Symbol: \t)
    try:
        dfr_Direct = pd.read_csv(datafile, sep="\t", header=None,
                                 index_col=False, engine="python",
                                 names=["Plate", "Reading"])
    except:
        return None
    # Remove empty lines
    dfr_Direct = dfr_Direct.dropna(how = "all")
    # Separate first column into plate and well. Write well into new column
    lst_Plates = dfr_Direct.Plate.apply(pf.pherastar_plate)
    lst_Wells = dfr_Direct.Plate.apply(pf.pherastar_well)
    lst_Wells = [pf.sortable_well(w, wells) for w in lst_Wells]
    lst_Wells = [pf.well_to_index(w, wells) for w in lst_Wells]
    dfr_Direct["Plate"] = lst_Plates
    dfr_Direct = dfr_Direct.assign(Well = lst_Wells)
    # repurpose lstPlates to only contain the unique plate names
    lst_Plates = np.unique(np.array(lst_Plates))
    # repurpose lstWells to hold list of all wells possible on the current plate type
    lst_Wells = pf.write_well_list(wells)
    # Create new dataframe to hold the plate data
    dfr_Plates = pd.DataFrame(lst_Wells, columns=["Well"])
    # Get reading for each plate and write it in dfPlateArray as new column
    for p in range(len(lst_Plates)):
        dfr_Plates[lst_Plates[p]] = dfr_Direct[dfr_Direct.Plate == lst_Plates[p]].reset_index().Reading
    # Return
    return dfr_Plates

def get_bmg_list_namesonly(datafile: str):
    """
    Returns only the plate names in a BMG list output file.

    Arguments:
        datafile -> string. Path of datafile
    """
    # Read file. Cells in PheraStar output are tab stop separated (Symbol: \t)
    try:
        dfr_Direct = pd.read_csv(datafile, sep="\t", header=None, index_col=False,
                                 engine="python", names=["Plate", "Reading"])
    except:
        return None
    # Remove empty lines
    dfr_Direct = dfr_Direct.dropna()
    # Separate first column into plate and well. Write well into new column
    arr_Plates = dfr_Direct.Plate.apply(pf.pherastar_plate)
    arr_Plates = np.unique(np.array(arr_Plates))
    # numpy arrays are immutable, so we need an actual list
    # into which we write the entries that pass the criteria
    lst_Plates = []
    for i in range(len(arr_Plates)):
        if arr_Plates[i] != "":
            lst_Plates.append(arr_Plates[i])
    return lst_Plates

def get_bmg_plate_readout(datapath: str, datafile: str, wells: int, assaytype: str):
    """
    Parses HTRF output file from BMG Pherastar, going by keyword.
    
    
    Note: Output files from plate reader are text files (tab delimited)
    masquerading as xls files. Depending on the machine/software version/protocol,
    they sometimes seem purely tab delimited, sometimes there is leading
    whitespace, sometimes they"ve ben resaved by the user as actual excel files.
    If they are actual excel files, the read_csv throw an error and we will have to try
    read_excel.

    Arguments:
        datapath -> string. Path to directory of datafile
        datafile -> string. Name of datafile.
        wells -> integer. Plateformat in number of wells.
                 Permitted: 96, 384, 1536
        assaytype -> string. Assay type. Specific to our org, used to validate
                     data file. Permitted: "HTRF", "AlphaScreen", "TAMRA FP".
    """

    # In case there is no slash at the end of the data path, add one!
    if datapath[len(datapath)-1] != chr(92):
        datapath = datapath + chr(92)
    # Make 49 columns (48 columns max on plate, plus 1 column for well letters)
    lst_Columns = [""] * 49
    for i in range(len(lst_Columns)):
        lst_Columns[i] = i
    # Read file. Cells in PheraStar output are tab stop separated (Symbol: \t)
    # Get proper encoding by opening the file first with basic tools and
    # accessing the encoding
    dfpath = os.path.join(datapath, datafile)
    try:
        dfr_Direct = pd.read_csv(dfpath,
                                 sep="\t",
                                 header=None,
                                 index_col=False,
                                 engine="python", 
                                 names=lst_Columns,
                                 encoding = open(dfpath).encoding)
    except:
        try:
            dfr_Direct = pd.read_excel(dfpath,
                                       header=None,
                                       index_col=False,
                                       engine="openpyxl",
                                       names=lst_Columns)
        except:
            return None

    if dfr_Direct.iloc[0,0].find("Testname") == -1:
        return None
    # Find keyword and return the row number where data starts
    if assaytype == "HTRF":
        str_Keyword = "Chromatic / Channel: 1/Ratio channel A / B"
        int_DataStartRowOffset = 3
    elif assaytype == "TAMRA FP":
        str_Keyword = "Chromatic / Channel: 1/Polarization values [mP]"
        int_DataStartRowOffset = 4
    elif assaytype == "AlphaScreen":
        str_Keyword = "A"
        int_DataStartRowOffset = 0
    elif assaytype.find("Glo") != -1:
        str_Keyword = "A"
        int_DataStartRowOffset = 0
    # perhaps inefficient, but this returns a list, and we need the first/0 element of the list
    try:
        int_DataStartRow = dfr_Direct.index[dfr_Direct[0] == str_Keyword][0] + int_DataStartRowOffset
    except:
        return None
    # Check whether row labels are present:
    if dfr_Direct.loc[int_DataStartRow,0].find("A") == -1:
        return None
    # Extract all lines after keyword
    lst_Wells = []
    lst_Data = []
    # Write wells into list
    for row in range(int_DataStartRow,len(dfr_Direct),1):
        lst_Row = dfr_Direct.loc[row]
        #for j in range(len(lst_Row)-1):
        for col in range(pf.plate_columns(wells)):
            lst_Wells.append(pf.sortable_well(str(lst_Row[0]) + str(col+1),wells))
    # Write data into list
    for row in range(pf.plate_rows(wells)):
        for col in range(pf.plate_columns(wells)):
            if type(dfr_Direct.loc[int_DataStartRow+row,col+1]) != str:
                lst_Data.append(dfr_Direct.loc[int_DataStartRow+row,col+1])
            else:
                try:
                    lst_Data.append(int(dfr_Direct.loc[int_DataStartRow+row,col+1]))
                except:
                    lst_Data.append(np.nan)
    # Return
    return pd.DataFrame(data={"Well":lst_Wells,datafile:lst_Data})

def get_lightcycler_readout(datafile: str, wells: int):
    """
    Parses Roche LightCycler data files.
    
    Arguments:
        datafile -> string. Path of datafile
        wells -> integer. Plate format in number of wells.
                 Permitted values: 96, 384.

    Returns pandas dataframe with columns "Well","Name","Temp","Fluo"
    """
    # Open Datafile
    try:
        direct = pd.read_csv(datafile, sep="\t", header=1, index_col=False,
                             engine="c",
                             names=["Well","Name","Prog","Seg",
                                    "Cycle","Time","Temp","Fluo"])
    except Exception:
        return None
    # Define required lists
    all_wells = direct.Well.unique()
    sortable = [pf.sortable_well(well,wells) for well in direct.Well.unique()]
    samples = direct.Name.unique()
    temp = [direct[(direct.Well==well)]["Temp"].tolist() for well in all_wells]
    fluo = [direct[(direct.Well==well)]["Fluo"].tolist() for well in all_wells]
    # Return
    return pd.DataFrame(data = {"Well":sortable,
                                "Name":samples,
                                "Temp":temp,
                                "Fluo":fluo})

def get_quantstudio_readout(datafile: str, wells: int):
    """
    Parses Quantstudio7 data files.
    
    Arguments:
        datafile -> string. Path of datafile
        wells -> integer. Plate format in number of wells.
                 Permitted values: 96, 384.

    Returns pandas dataframe with columns "Well","Name","Temp","Fluo"
    """
    # Open Datafile
    try:
        direct = pd.read_excel(datafile, 
                               header=None,
                               engine="openpyxl",
                               sheet_name="Melt Curve Raw Data")
    except Exception:
        return None
    if direct.iloc[0,0] != "Block Type":
        return None
    start = 0
    for row in direct.index:
        if direct.iloc[row,0] == "Well Position":
            start = row
    if start == 0:
        # We couldn't find the start of the file
        return None
    direct = direct.loc[start+1:]
    direct.columns = ["Well","Temp","Fluo","Derivative"]
    # Define required lists
    all_wells = direct.Well.unique()
    sortable = [pf.sortable_well(well,wells) for well in direct.Well.unique()]
    samples = [np.nan] * len(all_wells)
    temp = [direct[(direct.Well==well)]["Temp"].tolist() for well in all_wells]
    fluo = [direct[(direct.Well==well)]["Fluo"].tolist() for well in all_wells]
    # Return
    return pd.DataFrame(data = {"Well":sortable,
                                "Name":samples,
                                "Temp":temp,
                                "Fluo":fluo})

def get_mxp_readout(datafile: str, start: int):
    """
    Parses Agilent Stratagene MX3005p output files. Format may be
    specific to our org.

    Arguments:
        datafile -> string. Path of datafile
        start -> integer. Start temperature of experiment.
    
    Returns pandas dataframe with columns "Well","Name","Temp","Fluo"
    """
    try:
        dfr_Direct = pd.read_excel(datafile, header=None, engine="openpyxl")
    except:
        return None
    # Test to see if we have the right file type:
    if dfr_Direct.iloc[0,0] != "Amplification Plots":
        return None
    # Drop all unrequired rows and columns
    # Drop first two rows first rows (they are empty) and
    # row three (only has unrequired headers, i.e. "Fluorescence (R)")
    dfr_Direct.drop([0,1,3], inplace=True)
    # Reset index:
    dfr_Direct = dfr_Direct.reset_index(drop=True)
    # delete first two columns. First is empty, second has cycles,
    # but we will not need them as we use indices
    dfr_Direct.drop([0,1], axis=1, inplace=True)
    # find empty row separating the two halves
    int_Separator = 0
    for row in range(dfr_Direct.shape[0]):
        if type(dfr_Direct.iloc[row,0]) == str:
            int_Separator = row-1
    # Split dataframe due to how the data is organised in the output file
    # (One block for top half of plate, one for bottom)
    dfr_Direct_Top = dfr_Direct.iloc[:int_Separator-3,:]
    dfr_Direct_Top = dfr_Direct_Top.reset_index(drop=True)
    dfr_Direct_Bot = dfr_Direct.iloc[int_Separator:,:].reset_index(drop=True)
    dfr_Direct_Bot.drop([1], inplace=True)
    dfr_Direct_Bot = dfr_Direct_Bot.reset_index(drop=True)
    drop_list = []
    for col in dfr_Direct_Bot.columns:
        if pd.isna(dfr_Direct_Bot.loc[0,col]):
            drop_list.append(col)
    dfr_Direct_Bot = dfr_Direct_Bot.drop(columns=drop_list)
    # Get list of wells
    lst_Wells = dfr_Direct_Top.loc[0].to_list() + dfr_Direct_Bot.loc[0].to_list()
    for well in range(len(lst_Wells)):
        int_Comma = lst_Wells[well].find(",")
        lst_Wells[well] = pf.sortable_well(lst_Wells[well][:int_Comma],96)
    # Lose top row before transposing
    dfr_Direct_Top.drop([0], inplace=True)
    dfr_Direct_Bot.drop([0], inplace=True)
    # Get list of temperatures based on start temp
    # Concatenate dataframes
    dfr_Direct = pd.concat([dfr_Direct_Top.T, dfr_Direct_Bot.T]).reset_index(drop=True)
    # Assumption is one reading per degree
    lst_Temp = list(range(start, start + dfr_Direct.shape[1]))
    # Create new dataframe
    dfr_Readout = pd.DataFrame(index=range(len(lst_Wells)),
                               columns=["Well","Name","Temp","Fluo"])
    for well in range(dfr_Readout.shape[0]):
        dfr_Readout.loc[well,"Well"] = lst_Wells[well]
        dfr_Readout.loc[well,"Name"] = lst_Wells[well]
        dfr_Readout.loc[well,"Temp"] = lst_Temp
        dfr_Readout.loc[well,"Fluo"] = dfr_Direct.loc[well].tolist()
    # Return the new dataframe
    return dfr_Readout

def get_bmg_timecourse_readout(datafile: str):
    """
    Get readout for timecourse on BMG plate reader.
    Assumption is data is in one plate-shaped table per timepoint, 384 wells.

    Arguments:
        datafile -> string. Path to datafile

    Returns pandas dataframe with columns "Well"(string),
    "Time"(list of times),"Signal"(list of readings)
    """
    int_PlateFormat = 384
    int_Columns = pf.plate_columns(int_PlateFormat)
    int_Rows = pf.plate_rows(int_PlateFormat)
    lst_ReadoutColumns = range(int_Columns+1)
    # Read file. Cells in PheraStar output are tab stop separated (Symbol: \t)
    # Get proper encoding by opening the file first with basic tools and
    # accessing the encoding

    try:
        dfr_Direct = pd.read_csv(datafile,
                                 sep="\t",
                                 header=None,
                                 index_col=False,
                                 engine="python", 
                                 names=lst_ReadoutColumns,
                                 encoding = open(datafile).encoding)
    except:
        try:
            dfr_Direct = pd.read_csv(datafile,
                                     sep="\s+",
                                     header=None,
                                     index_col=False,
                                     engine="python", 
                                     names=lst_ReadoutColumns,
                                     encoding = open(datafile).encoding)
        except:
            try:
                dfr_Direct = pd.read_excel(datafile,
                                           header=None,
                                           index_col=False,
                                           engine="openpyxl",
                                           names=lst_ReadoutColumns)
            except:
                return None

    int_CycleLength = 36
    int_Cycles = 0
    # Time of cycle is given in file
    dfr_Timecourse = pd.DataFrame(index=range(int_PlateFormat),
                                  columns=["Well","Time","Signal"])
    # Initialise timecourse
    for i in range(dfr_Timecourse.shape[0]):
        dfr_Timecourse.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
        dfr_Timecourse.loc[i,"Time"] = []
        dfr_Timecourse.loc[i,"Signal"] = []

    # Go through first column to find number of cycles and associated time
    for line in range(dfr_Direct.shape[0]):
        cell = dfr_Direct.iloc[line,0]
        if type(cell) == str:
            if "Cycle: " in cell:
                int_Cycles += 1
                # Any number of spaces is separator
                # -> String in csv is "Time [s]: 1234"
                # -> number of seconds ends up in third column (index 2)
                for row in range(int_Rows):
                    for col in range(int_Columns):
                        # find corresponding index
                        int_Index = row*int_Columns + col
                        value = dfr_Direct.iloc[line+3+row,1+col] # for GEF assay
                        #value = dfr_Direct.iloc[line+2+row,1+col] # For charline's assay
                        if not value is None:
                            try:
                                value = float(value)
                            except ValueError:
                                value = np.nan
                        dfr_Timecourse.loc[int_Index,"Signal"].append(value)
                        seconds = dfr_Direct.iloc[line+1,2]
                        if not pd.isna(seconds):
                            seconds = float(seconds)
                        else:
                            seconds = int_Cycles * int_CycleLength
                        dfr_Timecourse.loc[int_Index,"Time"].append(seconds)
                        #except ValueError:
                        #    pass
    # cleanup to remove any empty wells
    dfr_Timecourse = dfr_Timecourse[dfr_Timecourse["Signal"].map(lambda d: len(d)) > 0]
    dfr_Timecourse.reset_index(drop=True, inplace=True)

    return dfr_Timecourse

def get_bmg_DRTC_readout(datafile: str):
    '''
    Parses BMG files for dose response time course experiments.
    This output format is slightly different from the other time 
    course files and requires a separate parser.

    Arguments:
        datafile -> string. Path of datafile

    Returns pandas dataframe with wells as indices and timepoints
    as columns.
    '''
    int_PlateFormat = 384
    int_Columns = pf.plate_columns(int_PlateFormat)
    int_Rows = pf.plate_rows(int_PlateFormat)
    lst_ReadoutColumns = range(int_Columns+1)
    # Read file. Cells in PheraStar output are tab stop separated (Symbol: \t)
    try:
        dfr_Direct = pd.read_csv(datafile, sep="\s+", header=None,
                                 index_col=False, engine="python",
                                 names=lst_ReadoutColumns)
    except:
        try:
             dfr_Direct = pd.read_excel(datafile, header=None, index_col=False,
                                        engine="openpyxl", names=lst_ReadoutColumns)
        except:
            return None
    # Get location of "Cycle" and ensure there is a corresponding time stamp
    lst_CycleTimes = []
    lst_CyclesLines = []
    for line in range(len(dfr_Direct)):
        if (dfr_Direct.iloc[line,0].find("Cycle:") != -1 and
            dfr_Direct.iloc[line+1,0].find("Time") != -1):
            lst_CycleTimes.append(float(dfr_Direct.iloc[line+1,2]))
            lst_CyclesLines.append(line)
    # Check if any cycles have actually been found. If not, return None and
    # next checks in the process will flag that raw data file was not the
    # right type
    if len(lst_CycleTimes) == 0:
        return None
    # Time of cycle is given in file
    dfr_Timecourse = pd.DataFrame(index=range(int_PlateFormat),
                                  columns=lst_CycleTimes)
    # Initialise timecourse
    for row in range(int_Rows):
        for col in range(int_Columns):
            for cycle in range(dfr_Timecourse.shape[1]):
                dfr_Timecourse.iloc[pf.col_row_to_index(row,col,int_PlateFormat),cycle] = float(dfr_Direct.iloc[lst_CyclesLines[cycle]+3+row,1+col])
    return dfr_Timecourse

def get_FLIPR_DRTC_readout(datafile: str):
    '''
    Parses FLIPR output for dose response time course experiments.

    Arguments:
        datafile -> string. Path of datafile

    Returns pandas dataframe with wells as indices, timepoints as columns
    '''
    # Read file. Cells in FLIPR output are tab stop separated (Symbol: \t)
    try:
        dfr_Direct = pd.read_csv(datafile, sep="\t", header=None, index_col=False,
                                 engine="python")
    except:
        return None
    # Get location of cycles
    int_WellColumn = 0
    for col in range(dfr_Direct.shape[1]):
        if dfr_Direct.iloc[0,col] == "Well":
            int_WellColumn = col
    dfr_Timecourse = dfr_Direct.iloc[1:,int_WellColumn+1:dfr_Direct.shape[1]-1].reset_index(drop=True)
    new_columns = dfr_Direct.iloc[0,int_WellColumn+1:dfr_Direct.shape[1]-1].tolist()
    dfr_Timecourse.columns = new_columns

    return dfr_Timecourse
        
def get_prometheus_readout(datafile: str):
    """
    Parses processed or unprocessed Nanotemper Prometheus output.

    Arguments:
        datafile -> string. Path of datafile.

    Returns dataframe with capillaries as indices and readouts as columns
    (actual measurements are lists in the dataframe's cells)
    """
    # Each readout gets parsed into its own dataframe.
    # If it fails the first time, return None because it's
    # not the correct file type.
    try:
        dfr_Ratio = pd.read_excel(datafile, sheet_name="Ratio", header=None,
                                  engine="openpyxl")
    except Exception:
        return None
    dfr_330nm = pd.read_excel(datafile, sheet_name="330nm", header=None,
                              engine="openpyxl")
    dfr_350nm = pd.read_excel(datafile, sheet_name="350nm", header=None,
                              engine="openpyxl")
    dfr_Scattering = pd.read_excel(datafile, sheet_name="Scattering", header=None,
                                   engine="openpyxl")
    # Check whether we have a derivative already determined
    try:
        dfr_RatioDeriv = pd.read_excel(datafile, sheet_name="Ratio (1st deriv.)",
                                       header=None, engine="openpyxl")
        dfr_330nmDeriv = pd.read_excel(datafile, sheet_name="330nm (1st deriv.)",
                                       header=None, engine="openpyxl")
        dfr_350nmDeriv = pd.read_excel(datafile, sheet_name="350nm (1st deriv.)",
                                       header=None, engine="openpyxl")
        dfr_ScatteringDeriv = pd.read_excel(datafile, sheet_name="Scattering (1st deriv.)",
                                            header=None, engine="openpyxl")
        bol_Derivative = True
    except Exception:
        bol_Derivative = False
    
    int_Capillaries = 0
    for col in range(len(dfr_Ratio.columns)):
        if dfr_Ratio.iloc[1,col].find("Time") != -1:
            int_Capillaries += 1

    dfr_Prometheus = pd.DataFrame(index=range(int_Capillaries),
                                  columns=["CapIndex","CapillaryName","Time","Temp",
                                           "Ratio","330nm","350nm","Scattering",
                                           "RatioDeriv","330nmDeriv","350nmDeriv",
                                           "ScatteringDeriv"])
    idx_Sample = -1
    for col in range(len(dfr_Ratio.columns)):
        if dfr_Ratio.iloc[1,col].find("Time") != -1:
            idx_Sample += 1
            int_Pound = dfr_Ratio.iloc[0,col].find("#")
            if dfr_Ratio.iloc[0,col][int_Pound+2:int_Pound+3] == " ":
                # Recurring reminder: human friendly index vs machine index!
                idx_Capillary = int(dfr_Ratio.iloc[0,col][int_Pound+1:int_Pound+2])-1
            else:
                idx_Capillary = int(dfr_Ratio.iloc[0,col][int_Pound+1:int_Pound+3])-1
            dfr_Prometheus.loc[idx_Sample,"CapIndex"] = idx_Capillary
            idx_Open = dfr_Ratio.iloc[0,col].find("(")
            idx_Close = dfr_Ratio.iloc[0,col].find(")")
            if idx_Open != -1:
                dfr_Prometheus.loc[idx_Sample,"CapillaryName"] = dfr_Ratio.iloc[0,col][idx_Open+1:idx_Close]
            else:
                dfr_Prometheus.loc[idx_Sample,"CapillaryName"] = dfr_Ratio.iloc[0,col]
            dfr_Prometheus.loc[idx_Sample,"Time"] = dfr_Ratio[col].tolist()[2:]
            dfr_Prometheus.loc[idx_Sample,"Temp"] = dfr_Ratio[col+1].tolist()[2:]
            dfr_Prometheus.loc[idx_Sample,"Ratio"] = dfr_Ratio[col+2].tolist()[2:]
            dfr_Prometheus.loc[idx_Sample,"330nm"] = dfr_330nm[col+2].tolist()[2:]
            dfr_Prometheus.loc[idx_Sample,"350nm"] = dfr_350nm[col+2].tolist()[2:]
            dfr_Prometheus.loc[idx_Sample,"Scattering"] = dfr_Scattering[col+2].tolist()[2:]
            if bol_Derivative == True:
                dfr_Prometheus.loc[idx_Sample,"RatioDeriv"] = dfr_RatioDeriv[col+2].tolist()[2:]
                dfr_Prometheus.loc[idx_Sample,"330nmDeriv"] = dfr_330nmDeriv[col+2].tolist()[2:]
                dfr_Prometheus.loc[idx_Sample,"350nmDeriv"] = dfr_350nmDeriv[col+2].tolist()[2:]
                dfr_Prometheus.loc[idx_Sample,"ScatteringDeriv"] = dfr_ScatteringDeriv[col+2].tolist()[2:]

    return dfr_Prometheus

def get_prometheus_capillaries(datafile: int):
    """
    Simplified function based on get_prometheus_readout.
    Only returns the names of the capillaries in a dataframe prepped
    for the assay's metadata.

    Arguments:
        datafile -> string. Path of datafile.
    
    Returns dataframe with the capillaries as indices and the following
    columns: "CapIndex","CapillaryName","PurificationID","ProteinConc",
    "SampleID","SampleConc","Buffer","CapillaryType"
    """
    try:
        dfr_Ratio = pd.read_excel(datafile, sheet_name="Ratio", header=None,
                                  engine="openpyxl")
    except:
        return None

    int_Capillaries = 0
    for col in range(len(dfr_Ratio.columns)):
        if dfr_Ratio.iloc[1,col].find("Time") != -1:
            int_Capillaries += 1
    
    dfr_Capillaries = pd.DataFrame(index=range(int_Capillaries),
                                   columns=["CapIndex","CapillaryName","PurificationID",
                                            "ProteinConc","SampleID","SampleConc",
                                            "Buffer","CapillaryType"])
    idx_Sample = -1
    for col in range(len(dfr_Ratio.columns)):
        if dfr_Ratio.iloc[1,col].find("Time") != -1:
            idx_Sample += 1
            int_Pound = dfr_Ratio.iloc[0,col].find("#")
            if dfr_Ratio.iloc[0,col][int_Pound+2:int_Pound+3] == " ":
                # Recurring reminder: human friendly index vs machine index!
                idx_Capillary = int(dfr_Ratio.iloc[0,col][int_Pound+1:int_Pound+2])-1
            else:
                idx_Capillary = int(dfr_Ratio.iloc[0,col][int_Pound+1:int_Pound+3])-1
            dfr_Capillaries.loc[idx_Sample,"CapIndex"] = idx_Capillary
            idx_Open = dfr_Ratio.iloc[0,col].find("(")
            idx_Close = dfr_Ratio.iloc[0,col].find(")")
            if idx_Open != -1:
                dfr_Capillaries.loc[idx_Sample,"CapillaryName"] = dfr_Ratio.iloc[0,col][idx_Open+1:idx_Close]
            else:
                dfr_Capillaries.loc[idx_Sample,"CapillaryName"] = dfr_Ratio.iloc[0,col]
    
    return dfr_Capillaries

def get_operetta_readout(datafile: str, processor: str):
    """
    Parses processed readout of PerkinElmer Operetta Phoenix.

    Arguments:
        datafile -> string. Path to datafile
        processor -> string. Software/platform that has been used
                     to process raw images. Permitted values:
                     "Columbus", "Harmony"
    """
    # Choose direct read strategy based on data processor
    if processor == "Columbus":
        try:
            dfr_Direct = pd.read_csv(datafile, sep="\t", header=0, index_col=False,
                                     engine="python")
        except Exception:
            return None
    elif processor == "Harmony":
        try:
            # Read file, but only first column to find desired header row.
            dfr_Direct = pd.read_csv(datafile, sep="\t", usecols=[0], header=None,
                                     index_col=False, engine="python")
            # Find header row
            headerrow = dfr_Direct.index[dfr_Direct[0] == "[Data]"].tolist()[0]+1
            # Re-read file because we now know how many columns we need.
            dfr_Direct = pd.read_csv(datafile, sep="\t", header=headerrow,
                                     index_col=False, engine="python")

        except Exception:
            return None
    else:
        return None

    # Reduce columns to the ones we need and simplify column names
    dfr_Direct = dfr_Direct[["Row","Column","Nuclei Selected - Number of Objects"]].rename(
                        columns={"Nuclei Selected - Number of Objects":"Readout"})

    int_PlateFormat = 384
    dfr_Output = pd.DataFrame(index=range(int_PlateFormat),
                                columns=["Row","Column","Readout","Normalised"])

    int_PlateColumns = pf.plate_columns(int_PlateFormat)
    for line in range(dfr_Direct.shape[0]):
        # Transform from "human indexed" well to index base 0 well numbering
        int_Well = dfr_Direct.loc[line,"Column"] + (dfr_Direct.loc[line,"Row"]-1) * int_PlateColumns - 1
        dfr_Output.loc[int_Well,"Readout"] = dfr_Direct.loc[line,"Readout"]
        dfr_Output.loc[int_Well,"Row"] = dfr_Direct.loc[line,"Row"]
        dfr_Output.loc[int_Well,"Column"] = dfr_Direct.loc[line,"Column"]
    return dfr_Output


def get_readout(file_path, plate_name, data_rules):
    """
    Takes raw data file parsing rules (as pandas dataframe) and file path of raw data file to parse (as string)
    and builds a data frame.
    
    Returns pandas dataframe "dfr_RawData" and boolean value for success of parsing.
    """

    # Make it easy on yourself, read out rules into shorter to write variables ######################################################################
    # Data File Parsing
    str_Extension = data_rules["Extension"]
    str_FileType = data_rules["FileType"]
    str_Engine = data_rules["Engine"]
    str_Worksheet = data_rules["Worksheet"]
    # File verification
    bool_Verification = data_rules["UseVerificationKeyword"]
    if bool_Verification == True:
        str_VerificationKeyword = data_rules["VerificationKeyword"]
        int_VerificationAxis = int(data_rules["VerificationKeywordAxis"]) 
        int_VerificationRow = int(data_rules["VerificationKeywordRow"])
        int_VerificationColumn = int(data_rules["VerificationKeywordColumn"])
        bool_ExactVerificationKeyword = data_rules["ExactVerificationKeyword"]

    # if plate_name is a list, we are dealing with mltiple plates. Obvs.
    if type(plate_name) == list:
        openthis = file_path
    else:
        openthis = os.path.join(file_path,plate_name)

    # Get the first read ############################################################################################################################
    if str_FileType == "csv" or str_FileType == "txt":
        print("Trying to parse CSV or TXT file.")
        try:
            dfr_ParsedDataFile = pd.read_csv(openthis,
                                             sep=None,
                                             header=None,
                                             index_col=False,
                                             engine=str_Engine)
            print("Successfully parsed a CSV or TXT file.")
        except:
            try: 
                print("Couldn't parse, return empty dataframe and no success.")
                dfr_ParsedDataFile = pd.read_excel(openthis,
                                                  sep=None,
                                                  header=None,
                                                  index_col=False,
                                                  engine=str_Engine)
            except:
                print("Successfully parsed a XLS file.")
                return pd.DataFrame(), False
    elif str_FileType[0:3] == "xls":
        print("Trying to parse XLS or XLSX file.")
        try:
            dfr_ParsedDataFile = pd.read_excel(openthis,
                                               sheet_name=str_Worksheet,
                                               header=None,
                                               index_col=None,
                                               engine=str_Engine)
        except:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False
        print("Successfully parsed a XLS or XLSX file")
    print(f"Shape: {dfr_ParsedDataFile.shape[0]} by {dfr_ParsedDataFile.shape[1]}")

    # Verify whether we're dealing with a valid data file ###########################################################################################
    if bool_Verification == True:
        bool_Verified = False
        # Trawl file for specified keyword in specified column
        if int_VerificationAxis == 0:
            for idx in dfr_ParsedDataFile.index:
                # Make sure we actually only look at strings:
                var_Cell = str(dfr_ParsedDataFile.loc[idx, int_VerificationColumn])
                bool_Verified = Verification(var_Cell, str_VerificationKeyword, bool_ExactVerificationKeyword)
                if bool_Verified == True:
                    break
        elif int_VerificationAxis == 1:
            for col in dfr_ParsedDataFile.columns:
                # Make sure we actually only look at strings:
                var_Cell = dfr_ParsedDataFile.loc[int_VerificationRow, col]
                bool_Verified = Verification(var_Cell, str_VerificationKeyword, bool_ExactVerificationKeyword)
                if bool_Verified == True:
                    break
        # If keyword is NOT found:
        if bool_Verified == False:
            print("could not verify file")
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False

    # Continue writing rules to variables ###########################################################################################################
    # 
    str_PlateOrSample = data_rules["PlateOrSample"]
    if str_PlateOrSample == "Plate":
        int_Wells = data_rules["AssayPlateFormat"]
    
    str_GridOrTable = data_rules["GridOrTable"]

    # First dataset
    bool_DatasetKeyword = data_rules["UseDatasetKeyword"]
    bool_ExactDatasetKeyword = data_rules["ExactDatasetKeyword"]
    str_DatasetKeyword = data_rules["DatasetKeyword"]
    int_DatasetKeywordRow = data_rules["DatasetKeywordRow"]
    int_DatasetKeywordColumn = data_rules["DatasetKeywordColumn"]
    tpl_DatasetKeywordOffset = data_rules["DatasetKeywordOffset"]
    tpl_DatasetCoordinates = data_rules["DatasetCoordinates"]
    
    # Multiple datasets
    bool_MultipleDatasets = data_rules["MultipleDatasets"]
    int_DatasetAxis = int(data_rules["DatasetAxis"])
    int_Datasets = int(data_rules["NumberMultipleDatasets"])
    str_NewDatasetSeparator = data_rules["NewDatasetSeparator"]
    if str_NewDatasetSeparator == "SameAsMain":
        str_NewDatasetKeyword = str_DatasetKeyword
        bool_ExactNewDatasetKeyword = bool_ExactDatasetKeyword
        int_NewDatasetKeywordColumn = int_DatasetKeywordColumn
        tpl_NewDatasetKeywordOffset = tpl_DatasetKeywordOffset
    elif str_NewDatasetSeparator == "Keyword":
        str_NewDatasetKeyword = data_rules["NewDatasetKeyword"]
        bool_ExactNewDatasetKeyword = bool_ExactDatasetKeyword
        int_NewDatasetKeywordColumn = data_rules["NewDatasetKeywordColumn"]
        tpl_NewDatasetKeywordOffset = data_rules["NewDatasetKeywordOffset"]
    elif str_NewDatasetSeparator == "SetDistance":
        tpl_NewDatasetOffset = data_rules["NewDatasetOffset"]

    # Sub-Datasets
    bool_SubDatasets = data_rules["UseSubDatasets"]
    int_SubDatasets = int(data_rules["NumberSubDatasets"])
    int_SubDatasetAxis = int(data_rules["SubDatasetAxis"])
    str_SubDatasetSeparator = data_rules["SubDatasetSeparator"]
    if str_SubDatasetSeparator == "SameAsMain":
        if bool_DatasetKeyword == True:
            str_SubDatasetKeyword = data_rules["DatasetKeyword"]


    # Start looking at files ########################################################################################################################
    dfr_DatasetCoordinates = pd.DataFrame(index=[0],columns=[0])
    # First step: Identify datasets and sub-datasets
    print(f"Dataset axis: {int_DatasetAxis}")
    lst_Coordinates = []
    # Find index of first dataset
    # First case: Keywords
    if bool_DatasetKeyword == True:
        if int_DatasetAxis == 0:
            lst_Coordinates.append(FindKeywordVertically(dfr_ParsedDataFile, 0, int_DatasetKeywordColumn, str_DatasetKeyword,
                                bool_ExactDatasetKeyword))
        elif int_DatasetAxis == 1:
            lst_Coordinates.append(FindKeywordHorizontally(dfr_ParsedDataFile, 0, int_DatasetKeywordRow, str_DatasetKeyword,
                                bool_ExactDatasetKeyword))
    # Continue if we have multiple datasets:
    if bool_MultipleDatasets == True:
        print("Multiple datasets")
        # Branch for different separators:
        if str_NewDatasetSeparator == "Keyword" or (str_NewDatasetSeparator == "SameAsMain" and bool_DatasetKeyword == True):
            print("First dataset: by keyword")
            if int_DatasetAxis == 0:
                lst_Coordinates += FindKeywordsVertically(dfr_ParsedDataFile, dfr_DatasetCoordinates.iloc[0,0]+1, int_DatasetKeywordColumn,
                                                    str_NewDatasetKeyword, bool_ExactDatasetKeyword,dfr_ParsedDataFile.shape[int_DatasetAxis]-1)
            elif int_DatasetAxis == 1:
                lst_Coordinates += FindKeywordsHorizontally(dfr_ParsedDataFile, dfr_DatasetCoordinates.iloc[0,0]+1, int_DatasetKeywordRow,
                                                    str_NewDatasetKeyword, bool_ExactDatasetKeyword,dfr_ParsedDataFile.shape[int_DatasetAxis]-1)
        elif str_NewDatasetSeparator == "SetDistance":
            print("Further dataset: by fixed offset")
            # For this one, we create a completely new dataframe instead of merging with the old one.
            if int_DatasetAxis == 0:
                int_NewRow = lst_Coordinates[0] + tpl_NewDatasetOffset[int_DatasetAxis]
                while int_NewRow < dfr_ParsedDataFile.shape[int_DatasetAxis]:                    
                    print(int_NewRow)
                    lst_Coordinates.append(int_NewRow)
                    int_NewRow += tpl_NewDatasetOffset[0]
            elif int_DatasetAxis == 1:
                int_NewCol = lst_Coordinates[0] + tpl_NewDatasetOffset[int_DatasetAxis]
                while int_NewCol < dfr_ParsedDataFile.shape[int_DatasetAxis]:                    
                    print(int_NewCol)
                    lst_Coordinates.append(int_NewCol)
                    int_NewCol += tpl_NewDatasetOffset[int_DatasetAxis]
    dfr_DatasetCoordinates = pd.DataFrame(index=range(len(lst_Coordinates)),columns=[0],data=lst_Coordinates)
    
    # Do we have sub-datasets?
    if bool_SubDatasets == True:
        print("Sub-datasets")
        print(f"Sub-dataset axis: {int_SubDatasetAxis}")
        dfr_SubDatasetCoordinates = pd.DataFrame(index=dfr_DatasetCoordinates.index)
        # Branch for different separators:
        # Keyword separator
        print(f"Sub-dataset separator: {str_SubDatasetSeparator}")
        if str_SubDatasetSeparator == "Keyword" or (str_SubDatasetSeparator == "SameAsMain" and bool_DatasetKeyword == True):
            print(f"Sub-dataset keyword: {str_SubDatasetKeyword}")
            # Branch for axis:
            if int_SubDatasetAxis == 0:
                for idx in dfr_DatasetCoordinates.index:
                    lst_SubDatasetCoordinates = []
                    int_StartRow = dfr_DatasetCoordinates.loc[idx,0] + 1
                    lst_SubDatasetCoordinates += FindKeywordsVertically(dfr_ParsedDataFile, int_StartRow,
                                                                        int_DatasetKeywordColumn, str_SubDatasetKeyword,
                                                                        bool_ExactDatasetKeyword, dfr_DatasetCoordinates.loc[idx,0]-1)
                    # Enlarge dataframe if necessary:
                    if len(lst_SubDatasetCoordinates) > dfr_SubDatasetCoordinates.shape[1]:
                        dfr_SubDatasetCoordinates = dfr_SubDatasetCoordinates.reindex(columns=range(len(lst_SubDatasetCoordinates)))
                    dfr_SubDatasetCoordinates.loc[idx] = lst_SubDatasetCoordinates
            elif int_SubDatasetAxis == 1:
                for idx in dfr_DatasetCoordinates.index:
                    lst_SubDatasetCoordinates = []
                    int_StartCol = dfr_DatasetCoordinates.loc[idx,0] + 1
                    lst_SubDatasetCoordinates += FindKeywordsHorizontally(dfr_ParsedDataFile, int_StartCol,
                                                                        int_DatasetKeywordRow, str_SubDatasetKeyword,
                                                                        bool_ExactDatasetKeyword, dfr_DatasetCoordinates.loc[idx,0]-1)
                    # Enlarge dataframe if necessary:
                    if len(lst_SubDatasetCoordinates) > dfr_SubDatasetCoordinates.shape[1]:
                        dfr_SubDatasetCoordinates = dfr_SubDatasetCoordinates.reindex(columns=range(len(lst_SubDatasetCoordinates)))
                    dfr_SubDatasetCoordinates.loc[idx] = lst_SubDatasetCoordinates
        # Offset separator
        elif str_SubDatasetSeparator == "SetDistance":
            print("Sub-dataset separator: keyword.")
            int_NewRow = lst_SubDatasetCoordinates[0]
            while int_NewRow in dfr_ParsedDataFile.index:
                print(int_NewRow)
                lst_SubDatasetCoordinates.append(int_NewRow)
                int_NewRow += tpl_NewDatasetOffset[int_SubDatasetAxis]
        # Create dataframe to merge
        print(dfr_SubDatasetCoordinates)
        dfr_DatasetCoordinates = pd.concat([dfr_DatasetCoordinates, dfr_SubDatasetCoordinates], axis=1, join="inner")
        dfr_DatasetCoordinates.columns = range(len(dfr_DatasetCoordinates.columns))
        # Convert all values to integers:
        for col in dfr_DatasetCoordinates.columns:
            dfr_DatasetCoordinates[col] = dfr_DatasetCoordinates[col].astype(int)
        print(dfr_DatasetCoordinates)

    # Print info for sanity check
    print(f"Datasets: {dfr_DatasetCoordinates.shape[0]}")
    print(u"Dataset start rows: \n" + str(dfr_DatasetCoordinates.iloc[:,0]))

    # Branching: Plate or samples?
    if str_PlateOrSample == "Plate":
        print("We have a plate")
        # Brancking: Table or Grid?
        if str_GridOrTable == "Grid":
            # Create dataframe -> assuming one dataset for now
            dfr_RawData = pd.DataFrame(index=dfr_DatasetCoordinates.index,columns=dfr_DatasetCoordinates.columns)
            int_PlateRows = pf.plate_rows(int_Wells)
            int_PlateCols = pf.plate_columns(int_Wells)
            lst_RowLetters = pf.plate_rows_letters(int_Wells)
            lst_ColumnNumbers = pf.plate_columns_numbers(int_Wells)
            for dfrrow in range(dfr_RawData.shape[0]):
                print(f"Dataframe row: {dfrrow}")
                for dfrcol in range(dfr_RawData.shape[1]):
                    print(f"Dataframe column: {dfrcol}")
                    # remember dataframes are indexed from zero!
                    startrow = dfr_DatasetCoordinates.iloc[dfrrow,dfrcol] + tpl_DatasetKeywordOffset[0]
                    print(f"Startrow: {startrow}")
                    startcol = int_DatasetKeywordColumn + tpl_DatasetKeywordOffset[1]
                    print(f"Startcol: {startcol}")
                    dfr_RawData.iloc[dfrrow,dfrcol] = dfr_ParsedDataFile.iloc[startrow:startrow+int_PlateRows,
                                                                            startcol:startcol+int_PlateCols]
                    # Rename rows and columns:
                    dfr_RawData.iloc[dfrrow,dfrcol] = dfr_RawData.iloc[dfrrow,dfrcol].set_axis(lst_RowLetters, axis=0)
                    dfr_RawData.iloc[dfrrow,dfrcol] = dfr_RawData.iloc[dfrrow,dfrcol].set_axis(lst_ColumnNumbers, axis=1)
                    print(dfr_RawData.iloc[dfrrow,dfrcol])

            # change for current setup:
            readouts = []
            for row in dfr_RawData.iloc[0,0].index:
                readouts.extend(dfr_RawData.iloc[0,0].loc[row].to_list())
            print(len(readouts))
            wells = [*range(0, int_Wells)]
            wells = [pf.index_to_well(w+1,int_Wells) for w in wells]
            dfr_RawData = pd.DataFrame(data={"Well":wells,plate_name:readouts})


    print(dfr_RawData)

    #print(dfr_ParsedDataFile)

    return dfr_RawData, True


def FindKeywordVertically(dfr, startrow, col, keyword, exact):
    for idx in dfr.index[startrow:]:
        cell = dfr.loc[idx,col]
        if not pd.isna(cell) == True:
            if keyword in cell:
                if exact == True:
                    if cell == keyword:
                        return idx
                else:
                    return idx

def FindKeywordsVertically(dfr, startrow, column, keyword, exact, stoprow):
    """
    Takes a pandas dataframe (dfr) and looks through specified column from startrow until stoprow is reached.
    If keyword is found, the corresponding row is added to the return list
    """
    lst_Return = []
    for idx in dfr.index[startrow:]:
        cell = dfr.loc[idx,column]
        if not pd.isna(cell) == True:
            if keyword in cell:
                if exact == True:
                    if cell == keyword:
                        lst_Return.append(idx)
                else:
                    lst_Return.append(idx)
        if idx == stoprow:
            break
    return lst_Return

def FindKeywordHorizontally(dfr, startcol, idx, keyword, exact):
    for col in dfr.columns[startcol:]:
        cell = dfr.loc[idx,col]
        if not pd.isna(cell) == True:
            if keyword in cell:
                if exact == True:
                    if cell == keyword:
                        return col
                else:
                    return col

def FindKeywordsHorizontally(dfr, startcolumn, row, keyword, exact, stopcol):
    """
    Takes a pandas dataframe (dfr) and looks through specified column starting at startcolumn until stopcolumn is reached.
    If keyword is found, the corresponding row is added to the return list
    """
    lst_Return = []
    for column in dfr.columns[startcolumn:]:
        cell = dfr.loc[row,column]
        if not pd.isna(cell) == True:
            if keyword in cell:
                if exact == True:
                    if cell == keyword:
                        lst_Return.append(column)
                else:
                    lst_Return.append(column)
        if column == stopcol:
            break
    return lst_Return

def Verification(str_Test, str_Keyword, bool_Exact):
    if bool_Exact == True and str_Keyword == str_Test:
        return True
    elif str_Keyword in str_Test:
        return True
    else:
        return False