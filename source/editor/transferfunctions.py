##############################################################################
##                                                                          ##
##    ######  #####    ####   ##  ##   #####  ######  ######  #####         ##
##      ##    ##  ##  ##  ##  ### ##  ##      ##      ##      ##  ##        ##
##      ##    #####   ######  ######   ####   ####    ####    #####         ##
##      ##    ##  ##  ##  ##  ## ###      ##  ##      ##      ##  ##        ##
##      ##    ##  ##  ##  ##  ##  ##  #####   ##      ######  ##  ##        ##
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

import pandas as pd
import datetime

import lib_platefunctions as pf
import lib_excelfunctions as ef
import json as js
import os

################################################################################################################################################################

def CreateBlankRuleSet():
    """
    Creates a blank (with default values) set of parsing rules for transfer files
    and returns it as a pandas dataframe.
    """

    real_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(real_path)
    json_path = os.path.join(dir_path, "bbq_transfer_mapping.json")

    transfer_rules = {"Extension":".csv",
                      "FileType":"csv",
                      "Engine":"Python",
                      "Worksheet":None,
                      "DestinationPlateFormat":384,
                      "Verification": {"Use":True,
                                       "Keyword":None,
                                       "Exact":True},
                      "Start":{"UseKeyword":True,
                               "Keyword":None,
                               "Axis":0,
                               "Row":None,
                               "Column":None,
                               "Coordinates":None},
                      "Stop":{"UseKeyword":True,
                              "Keyword":None,
                              "Exact":True,
                              "Column":None,
                              "UseCoordinates":False,
                              "Coordinates":None,
                              "UseEmptyLine":True},
                      "CatchSolventOnlyTransfers":True,
                      "TransferFileColumns":js.load(open(json_path, "r")),
                      "Exceptions":{"Catch":False,
                                    "UseKeyword":False,
                                    "Keyword":None,
                                    "Exact":True,
                                    "Axis":None,
                                    "Column":None,
                                    "Row":None,
                                    "UseCoordinates":False,
                                    "Coordinates":None}
                     }

    return transfer_rules
    