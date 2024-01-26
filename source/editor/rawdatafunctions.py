##############################################################################
##                                                                          ##
##    #####    ####   ##      ##    #####    ####   ######   ####           ##
##    ##  ##  ##  ##  ##      ##    ##  ##  ##  ##    ##    ##  ##          ##
##    #####   ######  ##  ##  ##    ##  ##  ######    ##    ######          ##
##    ##  ##  ##  ##  ##  ##  ##    ##  ##  ##  ##    ##    ##  ##          ##
##    ##  ##  ##  ##   ########     #####   ##  ##    ##    ##  ##          ##
##                                                                          ##
##    ######  ##  ##  ##  ##   #####  ######  ##   ####   ##  ##   #####    ##
##    ##      ##  ##  ### ##  ##        ##    ##  ##  ##  ### ##  ##        ##
##    ####    ##  ##  ######  ##        ##    ##  ##  ##  ######   ####     ##
##    ##      ##  ##  ## ###  ##        ##    ##  ##  ##  ## ###      ##    ##
##    ##       ####   ##  ##   #####    ##    ##   ####   ##  ##  #####     ##
##                                                                          ##
##############################################################################
"""
    This module contains all functions to parse liquid handler transfer files
    and bring the information therein in a usable format.
"""

# Imports #####################################################################################################################################################

from doctest import FAIL_FAST
from math import fabs
from msilib.schema import CompLocator
import pandas as pd
import datetime

import lib_platefunctions as pf
import lib_excelfunctions as ef

###############################################################################################################################################################

#####   ##       ####   ##  ##  ##  ##    #####   ##  ##  ##      ######   #####  ######  ######
##  ##  ##      ##  ##  ### ##  ##  ##    ##  ##  ##  ##  ##      ##      ##      ##        ##
#####   ##      ######  ######  #####     #####   ##  ##  ##      ####     ####   ####      ##
##  ##  ##      ##  ##  ## ###  ##  ##    ##  ##  ##  ##  ##      ##          ##  ##        ##
#####   ######  ##  ##  ##  ##  ##  ##    ##  ##   ####   ######  ######  #####   ######    ##

def CreateBlankRuleSet():
    """
    Creates a blank (with default values) set of parsing rules for raw data files and returns it as a pandas dataframe.
    """
    
    # Start with a blank dataframe for now. We will expand it as needed.
    # This takes a bit more processing time afaik, so once we're settled
    # on the fields we really need, the dataframe can be created with fixed
    # dimensions
    data_rules = {}

    # What do we need to parse the file properly ##############################################################################################################
    data_rules["Extension"] = None
    data_rules["FileType"] = None
    data_rules["Engine"] = None
    data_rules["Worksheet"] = None

    # After the file is parsed, how do we make sure that the contents actually are what we expect #############################################################
    data_rules["Verification"] = {"Use":False,
                                  "Keyword":None,
                                  "Row":None,
                                  "Column":None,
                                  "Axis":0,
                                  "Exact":True}
        # Options for Axis: 0 -> Down, along the indices
        #                   1 -> Right, along the columns


    # How is the data represented #############################################################################################################################
    data_rules["PlateOrSample"] = "Plate"
        # Options: "Plate"
        #          "Sample"
        # Explanation: If the assay data is collected on a plate reader, the data is organised as a representation
        #              of a microtitre plate. This can be either a grid representing it (each cell -> one well) or
        #              a table where each line/row corresponds to a well.
        #              If the data is collected otherwise, the dataset is most likely represented as a table where
        #              each line/row is a datapoint, e.g. along a concentration, time or temperature gradient.
    data_rules["AssayPlateFormat"] = 384
        # Most common plate format at CMD
    data_rules["GridOrTable"] = "Grid"
        # Options: "Grid"
        #          "Table"
        # Explanation: A "grid" would be a representation of a micro-titre plate with rows A-P and columns 1-24,
        #              whereas a "table" would have the wells of a plate (or individual samples) listed sequentially.
        #              If there are multiple datasets (i.e. plates or samples), these can be either in a sequence of
        #              tables or a number of columns in the same table. Sub-datasets may be organised in the same way.
    data_rules["GridLabelsIncluded"] = True
        # Options: True
        #          False
        # Explanation: Labels for rows and columns may not be included in the raw data file.

    # Are there multiple datasets #############################################################################################################################
    # Dataset here refers to the data for one plate or sample, depending on the readout from the instrument.
    # This can include sub-datasets, such as measurements at different timepoints or wavelengths.
    data_rules["MultipleDatasets"] = False
        # Options: True
        #          False
        # Example: Multiple tables or lists in the same data file.
    data_rules["NumberMultipleDatasets"] = 1
        # Options: 1 -> Set to 1 when "MultipleDatasets" is False
        #          -1 -> Undefined number of datasets, determine dynamically.
        #          Any other integer -> this many datasets
    data_rules["DatasetAxis"] = 0
        # Options: 0 -> Down, along the indices
        #          1 -> Right, along the columns
    data_rules["UseDatasetKeyword"] = True
        # Explanation: Look for a keyword in the specified column as the original keyword, if applicable.
    data_rules["ExactDatasetKeyword"] = False
        # Explanation: Keyword might not always be exact. For instance, in a kinetic experiment, the datasets might
        #              be preceded by "Time[s]: 0", "Time[s]: 60", etc., so you might want to look for "Time[s]:"
        #              in cells of the spreadsheet.
    data_rules["DatasetKeyword"] = None
    data_rules["DatasetKeywordRow"] = None
    data_rules["DatasetKeywordColumn"] = None
    data_rules["DatasetKeywordOffset"] = None
        # Explanation: The dataset will not start in the cell where the keyword is found. This field defines the offset
        #              as a two-tuple (rows, cols).
    data_rules["DatasetCoordinates"] = None
        # Explanation: This is a two-tuple of integers (row,column)
    data_rules["NewDatasetSeparator"] = "SameAsMain"
        # Relevant when data is organised in grids.
        # Options: "SameAsMain" -> Use same rulest used to find first dataset.
        #          "EmptyLine" -> New dataset starts immediately after old, separated only by one empty line.
        #          "Keyword" -> Once dataset is read, find keyword in same column as original keyword.
        #          "SetDistance" -> New dataset starts set distance from previous. Tupel of x and y distance as integers.
        #                           If number of datasets is dynamically determined, it will end when the cell is empty
        #                           (or outside the dataframe).
    data_rules["NewDatasetKeyword"] = None
    data_rules["NewDatasetKeywordColumn"] = None
    data_rules["NewDatasetKeywordOffset"] = None
    data_rules["NewDatasetOffset"] = None
        # Explanation: If "NewDatasetSeparator" == "SetDistance", this will be a integer tuple of the format
        #              (distance in rows, distance in columns)        
    data_rules["DatasetNamesFromFile"] = True
    data_rules["DatasetNames"] = None
        # This will either be a n-tuple defined from user input or an n-tuple from data file readout.
    data_rules["DatasetNamesFromFile"] = False
        # Options: True
        #          False
        # Explanation: If True, the names of datasets (effectively column titles if in table format)
        #              will be taken from file. Otherwise entered by user in GUI.
    data_rules["DatasetNames"] = None
        # Will be tuple of strings. Either parsed from file or entered by user.
        # These will be used as indices for the generated rawdata dataframe.
    
    # Are there sub-datasets ##################################################################################################################################
    # Sub-datasets can be measurements at different timepoints or wavelengths
    data_rules["UseSubDatasets"] = False
        # Options: True
        #          False
    data_rules["NumberSubDatasets"] = 1
        # Options: 1 -> Set to 1 when "UseSubDatasets" is False
        #          -1 -> Undefined number of sub-datasets, determine dynamically.
        #          Any other integer -> this many sub-datasets
        # Example 1: HTRF -> Fixed number. Three sub data-sets (Donor fluorescence, FRET signal, FRET ratio)
        # Example 2: Enzymatic reaction -> determine dynamically. Record fluorescence of substrate or product over time,
        #            user might change temporal resolution on plate reader.
    data_rules["SubDatasetAxis"] = 0
        # Options: 0 -> Down, along the indices
        #          1 -> Right, along the columns
    data_rules["SubDatasetSeparator"] = "SameAsMain"
        # Relevant when data is organised in grids.
        # Options:  "SameAsMain" -> Same conditions as main dataset
        #           "Keyword" -> Once dataset is read, find keyword in same column as original keyword.
        #           "SetDistance" -> New dataset starts set distance from previous. Tupel of x and y distance as integers.
        #                            If number of datasets is dynamically determined, it will end when the cell is empty
        #                            (or outside the dataframe).
        #            "EmptyLine" -> New dataset starts immediately after old, separated only by one empty line.
    data_rules["SubDatasetKeyword"] = None
        # Explanation: Look for a keyword in the same column as the original keyword, if applicable.
    data_rules["SubDatasetKeywordOffset"] = None
        # Explanation: Same as for dataset. Tupel of 2 integers for rows and columns.
    data_rules["SubDatasetDistance"] = None
        # Explanation: If "SubDatasetSeparator" == "SetDistance", this will be a integer tuple of the format
        #              (distance in rows, distance in columns)
    data_rules["SubDatasetNamesFromFile"] = False
        # Options: True
        #          False
        # Explanation: If True, the names of sub-datasets (effectively column titles if in table format)
        #              will be taken from file. Otherwise entered by user in GUI.
    data_rules["SubDatasetNames"] = None
        # Will be tuple of strings. Either parsed from file or entered by user.
        # This will either be a n-tuple defined from user input or an n-tuple from data file readout.
    
    return data_rules
