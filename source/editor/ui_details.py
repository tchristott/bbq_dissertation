
"""
    In this module:
    
    User interface elements for determining the rules to process data
    for a certain assay.

"""

# Imports ##############################################################################

import wx
import wx.xrc
import wx.grid

import pandas as pd
import os
from pathlib import Path
import zipfile as zf
import datetime
import json as js


import lib_messageboxes as mb
import lib_colourscheme as cs

################################################################################################
##                                                                                            ##
##    #####   ######  ######  ##  ##  ##  ######    #####   ##  ##  ##      ######   #####    ##
##    ##  ##  ##      ##      ##  ### ##  ##        ##  ##  ##  ##  ##      ##      ##        ##
##    ##  ##  ####    ####    ##  ######  ####      #####   ##  ##  ##      ####     ####     ##
##    ##  ##  ##      ##      ##  ## ###  ##        ##  ##  ##  ##  ##      ##          ##    ##
##    #####   ######  ##      ##  ##  ##  ######    ##  ##   ####   ######  ######  #####     ##
##                                                                                            ##
################################################################################################

class AssayDetails(wx.Panel):

    def __init__(self, parent, wkflw, assay):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object of this panel
            wkflow -> wofklow editor window
            assay -> assay definition dictionary
        """
        wx.Panel.__init__(self, parent,
                          id = wx.ID_ANY,
                          pos = wx.DefaultPosition, size = wx.DefaultSize,
                          style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetBackgroundColour(cs.BgUltraLight)
        self.pnlbgclr = cs.BgLight

        self.location = os.path.dirname(os.path.realpath(__file__))

        self.parent = parent
        self.wkflw = wkflw
        self.assay = assay

        self.meta = self.assay["Meta"]
        self.assay["DefaultDetails"] = CreateBlankRuleSet()
        self.details = self.assay["DefaultDetails"]
        self.reagents = self.assay["Reagents"]
        self.widgets = {"Buffer": {
                            "Type": "Multi Line Text Box",
                            "Detail": "Buffer",
                            "Lines": 3,
                            "Limit": False,
                            "Optional": False
                        },
                        "LIMS": {
                            "Type": "Property",
                            "ELN Page": {
                                "Detail": "ELN",
                                "Allowed": "str",
                                "Unit": False,
                                "Size": 100
                            },
                            "Optional": False
                        },
                        "DateOfExperiment":
                            {"Type": "Date Picker",
                            "Detail": "DateOfExperiment",
                            "Optional": False}
                       }

        # Associated variables:

        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)

        self.pnl_Wizard = wx.Panel(self)
        self.pnl_Wizard.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Wizard = wx.BoxSizer(wx.VERTICAL)

        # Simplebook ####################################################################
        # To make the generation of the dataframe easy, user will be guided through a
        # wizard. wxPython offers an inbuilt Wizard, but I'll make
        # my own with a simplebook to have more flexibility.
        self.sbk_Wizard = wx.Simplebook(self.pnl_Wizard,
                                        size = wx.Size(420,-1),
                                        style = wx.TAB_TRAVERSAL)
        self.sbk_Wizard.SetMaxSize(wx.Size(420,600))
        # Define dictionary that holds saving functions for each page:
        self.dic_PageSaveFunctions = {}

        #   # ##### #####  ###     ####   ###  #####  ###
        ## ## #       #   #   #    #   # #   #   #   #   #
        ##### ###     #   #####    #   # #####   #   #####
        # # # #       #   #   #    #   # #   #   #   #   #
        #   # #####   #   #   #    ###   #   #   #   #   #

        # Wizard Page: Meta data ########################################################
        self.pnl_MetaData = wx.ScrolledWindow(self.sbk_Wizard,
                                              style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_MetaData.SetScrollRate(5,5)
        self.pnl_MetaData.SetBackgroundColour(self.pnlbgclr)
        self.szr_MetaData = wx.BoxSizer(wx.VERTICAL)
        self.lbl_MetaData = wx.StaticText(self.pnl_MetaData, wx.ID_ANY,
                                          u"Information about this rule analysis workflow:",
                                          wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_MetaData.Add(self.lbl_MetaData, 0, wx.ALL, 5)
        self.szr_MetaDataFields = wx.FlexGridSizer(8, 2, 0, 0)
        self.szr_MetaDataFields.SetFlexibleDirection( wx.BOTH )
        self.szr_MetaDataFields.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
        self.lbl_Author = wx.StaticText(self.pnl_MetaData, wx.ID_ANY,
                                        u"Original author:", wx.DefaultPosition,
                                        wx.DefaultSize, 0)
        self.lbl_Author.Wrap(-1)
        self.szr_MetaDataFields.Add(self.lbl_Author, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Author = wx.TextCtrl(self.pnl_MetaData,
                                      value = "")
        # get username
        try:
            username = str(os.getlogin())
        except:
            username = ""
        self.txt_Author.SetValue(username)
        self.szr_MetaDataFields.Add(self.txt_Author, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_Timestamp = wx.StaticText(self.pnl_MetaData, wx.ID_ANY,
                                           u"Rule set created:", wx.DefaultPosition,
                                           wx.DefaultSize, 0)
        self.lbl_Timestamp.Wrap(-1)
        self.szr_MetaDataFields.Add(self.lbl_Timestamp, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Timestamp = wx.TextCtrl(self.pnl_MetaData, wx.ID_ANY, wx.EmptyString,
                                         wx.DefaultPosition, wx.DefaultSize, wx.TE_READONLY)
        self.txt_Timestamp.SetValue(str(datetime.datetime.now())[0:16])
        self.szr_MetaDataFields.Add(self.txt_Timestamp, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_Assay = wx.StaticText(self.pnl_MetaData,
                                       label = u"Name of assay:")
        self.lbl_Assay.Wrap(-1)
        self.szr_MetaDataFields.Add(self.lbl_Assay, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Assay = wx.TextCtrl(self.pnl_MetaData,
                                     value = u"My First Assay")
        self.szr_MetaDataFields.Add(self.txt_Assay, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_Shorthand = wx.StaticText(self.pnl_MetaData,
                                          label = u"Shorthand:")
        self.lbl_Shorthand.Wrap(-1)
        self.szr_MetaDataFields.Add(self.lbl_Shorthand, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Shorthand = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_Shorthand = wx.TextCtrl(self.pnl_MetaData,
                                         value = u"MFA")
        self.szr_Shorthand.Add(self.txt_Shorthand, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Shorthand.Add((5,5), 0, wx.ALL, 0)
        self.lbl_SixUpper = wx.StaticText(self.pnl_MetaData,
                                                label = u"(6 Characaters, uppercase)")
        self.szr_Shorthand.Add(self.lbl_SixUpper, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_MetaDataFields.Add(self.szr_Shorthand, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.lbl_AssayNameDB = wx.StaticText(self.pnl_MetaData,
                                          label = u"Assay name in databse:")
        self.lbl_AssayNameDB.Wrap(-1)
        self.szr_MetaDataFields.Add(self.lbl_AssayNameDB, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_AssayNameDB = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_AssayNameDB = wx.TextCtrl(self.pnl_MetaData,
                                         value = u"MFA-IC50")
        self.szr_AssayNameDB.Add(self.txt_AssayNameDB, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_AssayNameDB.Add((5,5), 0, wx.ALL, 0)
        self.lbl_ANDBExplain = wx.StaticText(self.pnl_MetaData,
                                                label = u"(can be used in results table to identify assay)")
        self.lbl_ANDBExplain.Wrap(150)
        self.szr_AssayNameDB.Add(self.lbl_ANDBExplain, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_MetaDataFields.Add(self.szr_AssayNameDB, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.lbl_Description = wx.StaticText(self.pnl_MetaData,
                                             label = u"Short description:")
        self.lbl_Description.Wrap(-1)
        self.szr_MetaDataFields.Add(self.lbl_Description, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Description = wx.TextCtrl(self.pnl_MetaData, 
                                           size = wx.Size(150,50))
        self.szr_MetaDataFields.Add(self.txt_Description, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_MainCategory = wx.StaticText(self.pnl_MetaData,
                                              label = u"Main category:")
        self.szr_MetaDataFields.Add(self.lbl_MainCategory, 0, wx.ALL, 5)
        self.szr_MainCategory = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_Yes = wx.RadioButton(self.pnl_MetaData,
                                      label = u"Assay is plate based",
                                      style = wx.RB_SINGLE)
        self.rad_Yes.SetValue(True)
        self.szr_MainCategory.Add(self.rad_Yes, 0, wx.ALL, 0)
        self.szr_MainCategory.Add((5,5), 0, wx.ALL, 0)
        self.rad_No = wx.RadioButton(self.pnl_MetaData,
                                     label = u"Not plate based",
                                     style = wx.RB_SINGLE)
        self.szr_MainCategory.Add(self.rad_No, 0, wx.ALL, 0)
        self.szr_MetaDataFields.Add(self.szr_MainCategory, 0, wx.ALL, 5)
        self.lbl_SecondaryCategory = wx.StaticText(self.pnl_MetaData,
                                                   label = u"Secondary Category")
        self.szr_MetaDataFields.Add(self.lbl_SecondaryCategory, 0, wx.ALL, 5)
        self.cho_SecondaryCategory = wx.Choice(self.pnl_MetaData,
                                               choices = ["Protein Protein Interaction", "Enzymatic", "Cell Based", "Continuous", "NA"])
        self.cho_SecondaryCategory.SetSelection(0)
        self.szr_MetaDataFields.Add(self.cho_SecondaryCategory, 0, wx.ALL, 5)
        self.szr_MetaData.Add(self.szr_MetaDataFields, 0, wx.ALL, 5)

        # All elements added to sizer
        self.pnl_MetaData.SetSizer(self.szr_MetaData)
        self.pnl_MetaData.Layout()
        self.szr_MetaData.Fit(self.pnl_MetaData)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_MetaData, u"MetaData", True)
        self.dic_PageSaveFunctions["MetaData"] = self.save_metadata
        #################################################################################

         ####  ###  #   # ####  #     #####    # ####   ####
        #     #   # ## ## #   # #     #        # #   # #
         ###  ##### ##### ####  #     ###      # #   #  ###
            # #   # # # # #     #     #        # #   #     #
        ####  #   # #   # #     ##### #####    # ####  ####

        # Wizard Page: Sample ID Source ################################################
        self.pnl_SampleIDSource = wx.ScrolledWindow(self.sbk_Wizard,
                                                style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_SampleIDSource.SetScrollRate(5,5)
        self.pnl_SampleIDSource.SetBackgroundColour(self.pnlbgclr)
        self.szr_SampleIDSource = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SampleIDSource = wx.StaticText(self.pnl_SampleIDSource,
                                                label = u"Source of Sample IDs/Names:")
        self.szr_SampleIDSource.Add(self.lbl_SampleIDSource, 0, wx.ALL, 5)
        # Liquid handler transfer file \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.rad_SampleIDTransfer = wx.RadioButton(self.pnl_SampleIDSource,
                                                   label = u"Liquid handler transfer file:",
                                                   style = wx.RB_SINGLE)
        self.rad_SampleIDTransfer.SetValue(True)
        self.szr_SampleIDSource.Add(self.rad_SampleIDTransfer, 0, wx.ALL, 5)
        self.szr_TransferFile = wx.FlexGridSizer(2,2,0,0)
        self.szr_TransferFile.Add((15,5), 0, wx.ALL, 0)
        self.lbl_TransferFile = wx.StaticText(self.pnl_SampleIDSource,
                                             label = u"Sample IDs are included in the liquid handler transfer file and will be extracted when the file is read.")
        self.lbl_TransferFile.Wrap(380)
        self.szr_TransferFile.Add(self.lbl_TransferFile, 0, wx.ALL, 0)
        self.szr_TransferFile.Add((15,5), 0, wx.ALL, 0)
        self.szr_SampleIDSource.Add(self.szr_TransferFile, 0, wx.ALL, 0)
        # Manual entry \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.rad_SampleIDManual = wx.RadioButton(self.pnl_SampleIDSource,
                                                label = u"Manual entry:",
                                                style = wx.RB_SINGLE)
        self.szr_SampleIDSource.Add(self.rad_SampleIDManual, 0, wx.ALL, 5)
        self.szr_ManualEntry = wx.FlexGridSizer(2,2,0,0)
        self.szr_ManualEntry.Add((15,5), 0, wx.ALL, 0)
        self.lbl_ManualEntry = wx.StaticText(self.pnl_SampleIDSource,
                                             label = u"Manually enter sample IDs/names, or copy and paste a plate map in a standard format from MS Excel.")
        self.lbl_ManualEntry.Wrap(380)
        self.szr_ManualEntry.Add(self.lbl_ManualEntry, 0, wx.ALL, 0)
        self.szr_ManualEntry.Add((15,5), 0, wx.ALL, 0)
        self.szr_SampleIDSource.Add(self.szr_ManualEntry, 0, wx.ALL, 0)
        # Raw Data File \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.rad_SampleIDDataFile = wx.RadioButton(self.pnl_SampleIDSource,
                                                   label = u"Included in raw data file:",
                                                   style = wx.RB_SINGLE)
        self.szr_SampleIDSource.Add(self.rad_SampleIDDataFile, 0, wx.ALL, 5)
        self.szr_RawDataFile = wx.FlexGridSizer(2,2,0,0)
        self.szr_RawDataFile.Add((15,5), 0, wx.ALL, 0)
        self.lbl_RawDataFile = wx.StaticText(self.pnl_SampleIDSource,
                                             label = u"If the raw data file(s) will include the sample IDs, you can chose this option.")
        self.lbl_RawDataFile.Wrap(380)
        self.szr_RawDataFile.Add(self.lbl_RawDataFile, 0, wx.ALL, 0)
        self.szr_RawDataFile.Add((15,5), 0, wx.ALL, 0)
        self.szr_SampleIDSource.Add(self.szr_RawDataFile, 0, wx.ALL, 0)

        # All elements added to sizer
        self.pnl_SampleIDSource.SetSizer(self.szr_SampleIDSource)
        self.pnl_SampleIDSource.Layout()
        self.szr_SampleIDSource.Fit(self.pnl_SampleIDSource)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_SampleIDSource, u"SampleIDSource", False)
        self.dic_PageSaveFunctions["SampleIDSource"] = self.save_sampleidsource
        #################################################################################

        ####  #      ###  ##### #####    #      ###  #   #  ###  #   # #####
        #   # #     #   #   #   #        #     #   # #   # #   # #   #   #
        ####  #     #####   #   ###      #     #####  ###  #   # #   #   #
        #     #     #   #   #   #        #     #   #   #   #   # #   #   #
        #     ##### #   #   #   #####    ##### #   #   #    ###   ###    #

        # Wizard Page: Plate Layout #####################################################
        self.pnl_PlateLayout = wx.ScrolledWindow(self.sbk_Wizard,
                                                style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_PlateLayout.SetScrollRate(5,5)
        self.pnl_PlateLayout.SetBackgroundColour(self.pnlbgclr)
        self.szr_PlateLayout = wx.BoxSizer(wx.VERTICAL)
        self.lbl_PlateLayout = wx.StaticText(self.pnl_PlateLayout,
                                                label = u"Plate Layout/Map:")
        self.szr_PlateLayout.Add(self.lbl_PlateLayout, 0, wx.ALL, 5)
        # Dynamic \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.rad_Dynamic = wx.RadioButton(self.pnl_PlateLayout,
                                          label = u"Dynamically generated",
                                          style = wx.RB_SINGLE)
        self.rad_Dynamic.SetValue(True)
        self.szr_PlateLayout.Add(self.rad_Dynamic, 0, wx.ALL, 5)
        self.szr_Dynamic = wx.FlexGridSizer(2,2,0,0)
        self.szr_Dynamic.Add((15,5), 0, wx.ALL, 0)
        self.lbl_TransferFile = wx.StaticText(self.pnl_PlateLayout,
                                             label = u"If you choose this option, the plate layout/map will be dynamically generated from the liquid handler transfer file.\nControl compound(s) must be included with the correct naming scheme as defined in the 'Data Processing' tab.")
        self.lbl_TransferFile.Wrap(380)
        self.szr_Dynamic.Add(self.lbl_TransferFile, 0, wx.ALL, 0)
        self.szr_Dynamic.Add((15,5), 0, wx.ALL, 0)
        self.szr_PlateLayout.Add(self.szr_Dynamic, 0, wx.ALL, 0)
        # Manual entry \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.rad_ManualDefinition = wx.RadioButton(self.pnl_PlateLayout,
                                                label = u"Manually defined:",
                                                style = wx.RB_SINGLE)
        self.szr_PlateLayout.Add(self.rad_ManualDefinition, 0, wx.ALL, 5)
        self.szr_ManualDefinition = wx.FlexGridSizer(2,2,0,0)
        self.szr_ManualDefinition.Add((15,5), 0, wx.ALL, 0)
        self.lbl_ManualDefinition = wx.StaticText(self.pnl_PlateLayout,
                                             label = u"Manually assign areas on the assay plate for samples, control compounds, and solvent-only additons.\nYou will be able to save and import plate layout files for use in with other workflows.")
        self.lbl_ManualDefinition.Wrap(380)
        self.szr_ManualDefinition.Add(self.lbl_ManualDefinition, 0, wx.ALL, 0)
        self.szr_ManualDefinition.Add((15,5), 0, wx.ALL, 0)
        self.szr_PlateLayout.Add(self.szr_ManualDefinition, 0, wx.ALL, 0)
        # All elements added to sizer
        self.pnl_PlateLayout.SetSizer(self.szr_PlateLayout)
        self.pnl_PlateLayout.Layout()
        self.szr_PlateLayout.Fit(self.pnl_PlateLayout)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_PlateLayout, u"PlateLayout", False)
        self.dic_PageSaveFunctions["PlateLayout"] = self.save_platelayout
        #################################################################################

        ####  #####  ###   #### ##### #   # #####  ####
        #   # #     #   # #     #     ##  #   #   #
        ####  ###   ##### #  ## ###   #####   #    ###
        #   # #     #   # #   # #     #  ##   #       #
        #   # ##### #   #  #### ##### #   #   #   ####

        # Wizard Page: Enzymes ##########################################################
        self.pnl_Reagents = wx.ScrolledWindow(self.sbk_Wizard,
                                                style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Reagents.SetScrollRate(5,5)
        self.pnl_Reagents.SetBackgroundColour(self.pnlbgclr)
        self.szr_Reagents = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Reagents = wx.StaticText(self.pnl_Reagents,
                                                label = u"Assay Reagents")
        self.szr_Reagents.Add(self.lbl_Reagents, 0, wx.ALL, 5)
        self.lbl_ReagentsDescription = wx.StaticText(self.pnl_Reagents,
                                                    label = u"On this page, you can define how many assay reagents (enzymes, substrates, pepties, detection antibodies, etc.) are involved in the assay, and which details of them you want to record.")
        self.lbl_ReagentsDescription.Wrap(380)
        self.szr_Reagents.Add(self.lbl_ReagentsDescription, 0, wx.ALL, 5)
        # Properties \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.pnl_PropFrame = wx.Panel(self.pnl_Reagents)
        self.pnl_PropFrame.SetBackgroundColour(cs.BgMediumDark)
        self.szr_PropFrame = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_Properties = wx.Panel(self.pnl_PropFrame)
        self.pnl_Properties.SetBackgroundColour(self.pnlbgclr)
        self.szr_Properties = wx.BoxSizer(wx.VERTICAL)
        self.szr_ReagentName = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_ReagentName = wx.StaticText(self.pnl_Properties,
                                          label = u"Reagent (e.g. Enzyme 1, Substrate 1, etc):")
        self.szr_ReagentName.Add(self.lbl_ReagentName, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ReagentName.Add((5,5), 0, wx.ALL, 0)
        self.txt_ReagentName = wx.TextCtrl(self.pnl_Properties,
                                           value = u"Protein")
        self.szr_ReagentName.Add(self.txt_ReagentName, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Properties.Add(self.szr_ReagentName, 0, wx.ALL, 5)
        self.szr_RecordName = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_RecordName = wx.CheckBox(self.pnl_Properties,
                                        label = u"Name (e.g. ATP). Default value:")
        self.chk_RecordName.SetValue(True)
        self.szr_RecordName.Add(self.chk_RecordName, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_RecordName.Add((5,5), 0, wx.ALL, 0)
        self.txt_DefaultName = wx.TextCtrl(self.pnl_Properties,
                                           value = u"MLLT1")
        self.szr_RecordName.Add(self.txt_DefaultName, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Properties.Add(self.szr_RecordName, 0, wx.ALL, 5)
        self.szr_ReagentBatch = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_ReagentBatch = wx.CheckBox(self.pnl_Properties,
                                        label = u"ID (e.g. batch/lot/prep). Default value:")
        self.chk_ReagentBatch.SetValue(True)
        self.szr_ReagentBatch.Add(self.chk_ReagentBatch, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ReagentBatch.Add((5,5), 0, wx.ALL, 0)
        self.txt_DefaultBatch = wx.TextCtrl(self.pnl_Properties,
                                            value = u"MLLT1A-p001")
        self.szr_ReagentBatch.Add(self.txt_DefaultBatch, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Properties.Add(self.szr_ReagentBatch, 0, wx.ALL, 5)
        self.szr_Concentration = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_Concentration = wx.CheckBox(self.pnl_Properties,
                                             label = u"Record concentration, in unit:")
        self.chk_Concentration.SetValue(True)
        self.szr_Properties.Add(self.chk_Concentration, 0, wx.ALL, 5)
        self.szr_Concentration = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Concentration.Add((15,5), 0, wx.ALL, 0)
        self.rad_Molar = wx.RadioButton(self.pnl_Properties,
                                        label = u"Molar:")
        self.rad_Molar.SetValue(True)
        self.szr_Concentration.Add(self.rad_Molar, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Concentration.Add((5,5), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.cho_Molar = wx.Choice(self.pnl_Properties,
                                      choices = ["M","mM","uM","nM","pM"])
        self.cho_Molar.SetSelection(2)
        self.szr_Concentration.Add(self.cho_Molar, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Concentration.Add((5,5), 0, wx.ALL, 0)
        self.rad_Mass = wx.RadioButton(self.pnl_Properties,
                                        label = u"Mass:")
        self.szr_Concentration.Add(self.rad_Mass, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Concentration.Add((5,5), 0, wx.ALL, 0)
        self.cho_Mass = wx.Choice(self.pnl_Properties,
                                      choices = ["mg/ml","ng/ml"])
        self.cho_Mass.SetSelection(0)
        self.cho_Mass.Enable(False)
        self.szr_Concentration.Add(self.cho_Mass, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Properties.Add(self.szr_Concentration, 0, wx.ALL, 5)
        self.szr_DefaultConc = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_DefaultConc.Add((15,5), 0, wx.ALL, 0)
        self.lbl_DefaultConc = wx.StaticText(self.pnl_Properties,
                                             label = u"Default concentration:")
        self.szr_DefaultConc.Add(self.lbl_DefaultConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_DefaultConc.Add((5,5), 0, wx.ALL, 0)
        self.txt_DefaultConc = wx.TextCtrl(self.pnl_Properties,
                                           size = wx.Size(40,-1),
                                           value = u"0.2")
        self.szr_DefaultConc.Add(self.txt_DefaultConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_DefaultConc.Add((5,5), 0, wx.ALL, 0)
        self.lbl_DefaultConcUnit = wx.StaticText(self.pnl_Properties,
                                                 label = u"uM")
        self.szr_DefaultConc.Add(self.lbl_DefaultConcUnit, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Properties.Add(self.szr_DefaultConc, 0, wx.ALL, 5)
        self.chk_Optional = wx.CheckBox(self.pnl_Properties,
                                        label = u"This is an optional reagent")
        self.chk_Optional.SetValue(False)
        self.szr_Properties.Add(self.chk_Optional, 0, wx.ALL, 5)
        # Add to sizers
        self.pnl_Properties.SetSizer(self.szr_Properties)
        self.pnl_Properties.Layout()
        self.szr_Properties.Fit(self.pnl_Properties)
        # Add to frame sizer for colour bar
        self.szr_PropFrame.Add(self.pnl_Properties, 0, wx.ALL, 1)
        self.pnl_PropFrame.SetSizer(self.szr_PropFrame)
        self.pnl_PropFrame.Layout()
        self.szr_PropFrame.Fit(self.pnl_PropFrame)
        self.szr_Reagents.Add(self.pnl_PropFrame, 0, wx.ALL, 5)
        self.szr_ReagentButton = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ReagentButton.Add((15,15), 1, wx.ALL, 0)
        self.btn_AddReagent = wx.Button(self.pnl_Reagents,
                                        label = u"Add new/update selected reagent")
        self.szr_ReagentButton.Add(self.btn_AddReagent, 0, wx.ALL, 0)
        self.szr_Reagents.Add(self.szr_ReagentButton, 0, wx.ALL, 5)
        self.lbl_Existing = wx.StaticText(self.pnl_Reagents,
                                          label = u"Existing Reagents and default values:")
        self.szr_Reagents.Add(self.lbl_Existing, 0, wx.ALL, 5)
        self.lbc_Existing = wx.ListCtrl(self.pnl_Reagents,
                                        style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Existing.InsertColumn(0, heading = "Reagent")
        self.lbc_Existing.InsertColumn(1, heading = "Name")
        self.lbc_Existing.InsertColumn(2, heading = "Batch/Lot")
        self.lbc_Existing.InsertColumn(3, heading = "Concentration")
        self.lbc_Existing.SetColumnWidth(3, 100)
        self.lbc_Existing.InsertColumn(4, heading = "Unit")
        self.lbc_Existing.SetColumnWidth(4, 50)
        self.szr_Reagents.Add(self.lbc_Existing, 0, wx.ALL, 5)
        self.szr_ExistingButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_DeleteSelected = wx.Button(self.pnl_Reagents,
                                            label = u"Delete selected reagent")
        self.szr_ExistingButtons.Add(self.btn_DeleteSelected, 0, wx.ALL, 0)
        self.szr_Reagents.Add(self.szr_ExistingButtons, 0, wx.ALL, 5)
        # All elements added to sizer
        self.pnl_Reagents.SetSizer(self.szr_Reagents)
        self.pnl_Reagents.Layout()
        self.szr_Reagents.Fit(self.pnl_Reagents)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Reagents, u"Reagents", False)
        self.dic_PageSaveFunctions["Reagents"] = self.save_reagents
        #################################################################################

        #   # #  ####  ####
        ## ## # #     #
        ##### #  ###  #
        # # # #     # #
        #   # # ####   ####

        # Wizard Page: Miscellaneous ####################################################
        self.pnl_Miscellaneous = wx.ScrolledWindow(self.sbk_Wizard,
                                                  style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Miscellaneous.SetScrollRate(5,5)
        self.pnl_Miscellaneous.SetBackgroundColour(self.pnlbgclr)
        self.szr_Miscellaneous = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Miscellaneous = wx.StaticText(self.pnl_Miscellaneous,
                                              label = u"Miscellaneous")
        self.szr_Miscellaneous.Add(self.lbl_Miscellaneous, 0, wx.ALL, 5)
        # Control compound \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.chk_Control = wx.CheckBox(self.pnl_Miscellaneous,
                                       label = u"Define control comompound name")
        self.chk_Control.SetValue(True)
        self.szr_Miscellaneous.Add(self.chk_Control, 0, wx.ALL, 5)
        self.szr_Control = wx.FlexGridSizer(4,2,0,0)
        self.szr_Control.Add((15,5), 0, wx.ALL, 0)
        self.lbl_Control = wx.StaticText(self.pnl_Miscellaneous,
                                         label = u"If the control compound name is not defined here, BBQ will look for 'Control' in the transfer file to chose the wells used for data normalisation (if the option is chosen under 'Data Processing')")
        self.lbl_Control.Wrap(380)
        self.szr_Control.Add(self.lbl_Control, 0, wx.ALL, 0)
        self.szr_Control.Add((15,5), 0, wx.ALL, 0)
        self.szr_ControlText = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_ControlText = wx.StaticText(self.pnl_Miscellaneous,
                                             label = u"Control compound name/ID: ")
        self.szr_ControlText.Add(self.lbl_ControlText, 0, wx.ALL, 0)
        self.txt_Control = wx.TextCtrl(self.pnl_Miscellaneous,
                                       value = u"Control")
        self.szr_ControlText.Add(self.txt_Control, 0, wx.ALL, 0)
        self.szr_Control.Add(self.szr_ControlText, 0, wx.ALL, 0)
        self.szr_Miscellaneous.Add(self.szr_Control, 0, wx.ALL, 5)
        # Buffer \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.chk_Buffer = wx.CheckBox(self.pnl_Miscellaneous,
                                      label = u"Record buffer composition")
        self.chk_Buffer.SetValue(True)
        self.szr_Miscellaneous.Add(self.chk_Buffer, 0, wx.ALL, 5)
        self.szr_Buffer = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Buffer.Add((15,5), 0, wx.ALL, 0)
        self.lbl_DefaultBuffer = wx.StaticText(self.pnl_Miscellaneous,
                                               label = u"Default buffer composition:")
        self.szr_Buffer.Add(self.lbl_DefaultBuffer, 0, wx.ALL, 0)
        self.szr_Buffer.Add((5,5), 0, wx.ALL, 0)
        self.txt_DefaultBuffer = wx.TextCtrl(self.pnl_Miscellaneous,
                                             value = u"20 mM HEPES, 100 mM NaCl, 2 mM TCEP, 0.5%(w/v) CHAPS, pH 7.5",
                                             style = wx.TE_MULTILINE,
                                             size = wx.Size(200,45))
        self.szr_Buffer.Add(self.txt_DefaultBuffer, 0, wx.ALL, 0)
        self.szr_Miscellaneous.Add(self.szr_Buffer, 0, wx.ALL, 5)
        # ELN PAGE \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.chk_LIMS = wx.CheckBox(self.pnl_Miscellaneous,
                                    label = u"Record LIMS/ELN page reference.")
        self.chk_LIMS.SetValue(True)
        self.szr_Miscellaneous.Add(self.chk_LIMS, 0, wx.ALL, 5)
        self.szr_LIMS = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_LIMS.Add((15,5), 0, wx.ALL, 0)
        self.lbl_LIMS = wx.StaticText(self.pnl_Miscellaneous,
                                      label = u"Default page:")
        self.szr_LIMS.Add(self.lbl_LIMS, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_LIMS.Add((5,5), 0, wx.ALL, 0)
        self.txt_LIMS = wx.TextCtrl(self.pnl_Miscellaneous,
                                    value = u"PAGE23-00271")
        self.szr_LIMS.Add(self.txt_LIMS, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Miscellaneous.Add(self.szr_LIMS, 0, wx.ALL, 5)
        # Datestamps \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.chk_DateOfExperiment = wx.CheckBox(self.pnl_Miscellaneous,
                                                label = u"Record date of experiment")
        self.chk_DateOfExperiment.SetValue(True)
        self.szr_Miscellaneous.Add(self.chk_DateOfExperiment, 0, wx.ALL, 5)
        self.chk_DateOfAnalysis = wx.CheckBox(self.pnl_Miscellaneous,
                                                label = u"Record date of analysis")
        self.szr_Miscellaneous.Add(self.chk_DateOfAnalysis, 0, wx.ALL, 5)
        # Assay Volume \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.chk_AssayVolume = wx.CheckBox(self.pnl_Miscellaneous,
                                           label = u"Record assay volume")
        self.szr_Miscellaneous.Add(self.chk_AssayVolume, 0, wx.ALL, 5)
        self.szr_AssayVolume = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_AssayVolume.Add((15,5), 0, wx.ALL, 0)
        self.lbl_AssayVolume = wx.StaticText(self.pnl_Miscellaneous,
                                             label = u"Default volume:")
        self.szr_AssayVolume.Add(self.lbl_AssayVolume, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_AssayVolume.Add((5,5), 0, wx.ALL, 0)
        self.txt_AssayVolume = wx.TextCtrl(self.pnl_Miscellaneous,
                                           size = wx.Size(40,-1),
                                           value = u"20")
        self.txt_AssayVolume.Enable(False)
        self.szr_AssayVolume.Add(self.txt_AssayVolume, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_AssayVolume.Add((5,5), 0, wx.ALL, 0)
        self.cho_AssayVolumeUnit = wx.Choice(self.pnl_Miscellaneous,
                                             choices = ["ml", "ul", "nl"])
        self.cho_AssayVolumeUnit.SetSelection(1)
        self.cho_AssayVolumeUnit.Enable(False)
        self.szr_AssayVolume.Add(self.cho_AssayVolumeUnit, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_Miscellaneous.Add(self.szr_AssayVolume, 0, wx.ALL, 5)
        # All elements added to sizer
        self.pnl_Miscellaneous.SetSizer( self.szr_Miscellaneous )
        self.pnl_Miscellaneous.Layout()
        self.szr_Miscellaneous.Fit( self.pnl_Miscellaneous )
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Miscellaneous, u"Miscellaneous", False)
        self.dic_PageSaveFunctions["Miscellaneous"] = self.save_miscellaneous
        #################################################################################


        # Add simplebook to main sizer ##################################################
        self.szr_Wizard.Add(self.sbk_Wizard, 1, wx.ALL, 5)

        # Simplebook Next/Back/Finish buttons ###########################################
        self.szr_WizardButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_WizardButtons.SetMinSize(wx.Size(420,35))
        self.szr_WizardButtons.Add((-1,-1), 1 , wx.EXPAND, 5)
        self.btn_WizardBack = wx.Button(self.pnl_Wizard,
                                        label = u"< Back",
                                        size = wx.Size(50,25))
        self.btn_WizardBack.Enable(False)
        self.szr_WizardButtons.Add(self.btn_WizardBack, 0, wx.ALL, 5)
        self.btn_WizardNext = wx.Button(self.pnl_Wizard,
                                        label = u"Next >",
                                        size = wx.Size(50,25))
        self.szr_WizardButtons.Add(self.btn_WizardNext, 0, wx.ALL, 5)
        self.btn_WizardPrintRules = wx.Button(self.pnl_Wizard, 
                                              label = u"Print rules", 
                                              size = wx.Size(50,25))
        self.szr_WizardButtons.Add(self.btn_WizardPrintRules, 0, wx.ALL, 5)

        self.szr_Wizard.Add(self.szr_WizardButtons, 0, wx.FIXED_MINSIZE, 5)
        self.pnl_Wizard.SetSizer(self.szr_Wizard)
        self.pnl_Wizard.Layout()
        self.szr_Wizard.Fit(self.pnl_Wizard)

        # Finish Wizard Sizer
        self.szr_Surround.Add(self.pnl_Wizard, 0, wx.EXPAND, 5)
        #################################################################################

        self.SetSizer(self.szr_Surround)
        self.Layout()

        self.Centre(wx.BOTH)

        self.update_editor_label()
        self.save_metadata()
        self.save_platelayout()
        self.save_sampleidsource()
        self.save_reagents()
        self.save_miscellaneous()
        

        ####  # #   # ####  # #   #  ####
        #   # # ##  # #   # # ##  # #
        ####  # ##### #   # # ##### #  ##
        #   # # #  ## #   # # #  ## #   #
        ####  # #   # ####  # #   #  ####

        # Bindings #####################################################################

        # Meta Data
        self.txt_Assay.Bind(wx.EVT_TEXT, self.on_txt_assay)
        self.txt_Shorthand.Bind(wx.EVT_TEXT, self.on_txt_shorthand)
        self.rad_Yes.Bind(wx.EVT_RADIOBUTTON, self.on_rad_yes)
        self.rad_No.Bind(wx.EVT_RADIOBUTTON, self.on_rad_no)

        # Plate Layout
        self.rad_Dynamic.Bind(wx.EVT_RADIOBUTTON, self.on_rad_dynamic)
        self.rad_ManualDefinition.Bind(wx.EVT_RADIOBUTTON, self.on_rad_manualdefinition)

        # Sample ID source
        self.rad_SampleIDTransfer.Bind(wx.EVT_RADIOBUTTON, self.on_rad_sampleidtransfer)
        self.rad_SampleIDManual.Bind(wx.EVT_RADIOBUTTON, self.on_rad_sampleidmanual)
        self.rad_SampleIDDataFile.Bind(wx.EVT_RADIOBUTTON, self.on_rad_sampleiddatafile)

        # Reagents
        self.chk_RecordName.Bind(wx.EVT_CHECKBOX, self.on_chk_recordname)
        self.chk_ReagentBatch.Bind(wx.EVT_CHECKBOX, self.on_chk_reagentbatch)
        self.chk_Concentration.Bind(wx.EVT_CHECKBOX, self.on_chk_concentration)
        self.rad_Molar.Bind(wx.EVT_RADIOBUTTON, self.on_rad_molar)
        self.rad_Mass.Bind(wx.EVT_RADIOBUTTON, self.on_rad_mass)
        self.cho_Mass.Bind(wx.EVT_CHOICE, self.on_unit_select)
        self.cho_Molar.Bind(wx.EVT_CHOICE, self.on_unit_select)
        self.txt_DefaultConc.Bind(wx.EVT_TEXT, self.on_txt_defaultconc)
        self.btn_AddReagent.Bind(wx.EVT_BUTTON, self.on_btn_addreagent)
        self.lbc_Existing.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_click_lbcexisting)
        self.btn_DeleteSelected.Bind(wx.EVT_BUTTON, self.on_btn_deleteselected)

        # Miscellaneous
        self.chk_Control.Bind(wx.EVT_CHECKBOX, self.on_chk_control)
        self.chk_Buffer.Bind(wx.EVT_CHECKBOX, self.on_chk_buffer)
        self.chk_LIMS.Bind(wx.EVT_CHECKBOX, self.on_chk_lims)
        self.chk_DateOfExperiment.Bind(wx.EVT_CHECKBOX, self.on_chk_dateofexperiment)
        self.chk_DateOfAnalysis.Bind(wx.EVT_CHECKBOX, self.on_chk_dateofanalysis)
        self.chk_AssayVolume.Bind(wx.EVT_CHECKBOX, self.on_chk_assayvolume)
        self.txt_AssayVolume.Bind(wx.EVT_TEXT, self.on_txt_assayvolume)
        self.cho_AssayVolumeUnit.Bind(wx.EVT_CHOICE, self.on_cho_assayvolumeunit)

        # Wizard navigation buttons
        self.btn_WizardBack.Bind(wx.EVT_BUTTON, self.on_wzd_back)
        self.btn_WizardNext.Bind(wx.EVT_BUTTON, self.on_wzd_next)
        self.btn_WizardPrintRules.Bind(wx.EVT_BUTTON, self.PrintRules)

        #################################################################################


    def __del__( self ):
        pass

    def on_wzd_back(self, event):
        """
        Event handler. Goes back one page in the wizard.
        """
        # Get page indices
        int_CurrentPage = self.sbk_Wizard.GetSelection()
        int_BackPage = int_CurrentPage - 1

        # Save information and check whether we can proceed:
        str_Proceed = self.dic_PageSaveFunctions[self.sbk_Wizard.GetPageText(int_CurrentPage)]()
        if "Backward" in str_Proceed:
            if int_BackPage >= 0:
                self.sbk_Wizard.SetSelection(int_BackPage)
                # Ensure buttons are enabled/disabled correctly:
                if int_BackPage == 0:
                    self.btn_WizardBack.Enable(False)
                if int_BackPage < self.sbk_Wizard.GetPageCount()-1:
                    self.btn_WizardNext.Enable(True)
        
        # Check for grid highlights:

    def on_wzd_next(self, event):
        # Get page indices
        int_CurrentPage = self.sbk_Wizard.GetSelection()
        int_NextPage = int_CurrentPage + 1

        # Save information and check whether we can proceed:
        str_Proceed = self.dic_PageSaveFunctions[self.sbk_Wizard.GetPageText(int_CurrentPage)]()
        if not "Stop" in str_Proceed:
            if int_NextPage < self.sbk_Wizard.GetPageCount():
                self.sbk_Wizard.SetSelection(int_NextPage)
                # Ensure buttons are enabled/disabled correctly:
                if int_NextPage > 0:
                    self.btn_WizardBack.Enable(True)
                if int_NextPage == self.sbk_Wizard.GetPageCount()-1:
                    self.btn_WizardNext.Enable(False)
        else:
            mb.info(self, "One or more fields have not been filled out.")

        # Check for grid highlights:
    
    def PrintRules(self, event):
        print("Rule set:")
        print(js.dumps(self.assay, sort_keys= False, indent = 2))

        #print("")
        #print("Widgets")
        #print(self.widgets)

    def populate_from_file(self, assay):
        """
        Populates this tab after an assay definition file has been
        loaded.
        """
        self.assay = assay
        self.meta = self.assay["Meta"]
        self.details = self.assay["DefaultDetails"]
        self.reagents = self.assay["Reagents"]

        # Meta data tab
        self.txt_Author.SetValue(self.meta["Author"])
        self.txt_Timestamp.SetValue(self.meta["Timestamp"])
        self.txt_Assay.SetValue(self.meta["FullName"])
        self.txt_Shorthand.SetValue(self.meta["Shorthand"])
        self.txt_AssayNameDB.SetValue(self.meta["AssayNameDB"])
        self.txt_Description.SetValue("FNORD")
        if self.meta["MainCategory"] == "Plate Based":
            plate_based = True
        else:
            plate_based = False
        self.rad_Yes.SetValue(plate_based)
        self.rad_No.SetValue(not plate_based)
        secondary = self.meta["SecondaryCategory"]
        sel = self.cho_SecondaryCategory.FindString(secondary)
        self.cho_SecondaryCategory.SetSelection(sel)
        # SampleIDs
        self.rad_SampleIDTransfer.SetValue(False)
        self.rad_SampleIDManual.SetValue(False)
        self.rad_SampleIDDataFile.SetValue(False)
        if self.assay["SampleIDSource"] == "TransferFile":
            self.rad_SampleIDTransfer.SetValue(True)
        elif self.assay["SampleIDSource"] == "ManualEntry":
            self.rad_SampleIDManual.SetValue(True)
        else:
            self.rad_SampleIDDataFile.SetValue(True)
        if self.details["PlateLayout"] == "Dynamic":
            plate_layout = True
        else:
            plate_layout = False
        self.rad_Dynamic.SetValue(plate_layout)
        self.rad_ManualDefinition.SetValue(not plate_layout)
        # Reagents
        reagent_names = self.reagents.keys()
        if len(reagent_names) > 0:
            for reagent_name in reagent_names:
                self.lbc_Existing.InsertItem(self.lbc_Existing.GetItemCount(),
                                             reagent_name)
                self.lbc_Existing.SetItem(self.lbc_Existing.GetItemCount()-1, 1,
                                          self.reagents[reagent_name]["Name"])
                self.lbc_Existing.SetItem(self.lbc_Existing.GetItemCount()-1, 2,
                                          self.reagents[reagent_name]["Batch"])
                self.lbc_Existing.SetItem(self.lbc_Existing.GetItemCount()-1, 3,
                                          self.reagents[reagent_name]["Conc"])
                self.lbc_Existing.SetItem(self.lbc_Existing.GetItemCount()-1, 4,
                                          self.reagents[reagent_name]["Conc Unit"])
            # Trigger update of UI elements for reagent:
            self.lbc_Existing.Select(0)
        # Miscellaneous
        self.chk_Control.SetValue(False)
        self.txt_Control.Enable(False)
        self.txt_Control.SetValue("")
        if "Control" in self.details.keys():
            self.chk_Control.SetValue(True)
            self.txt_Control.Enable(True)
            self.txt_Control.SetValue(self.details["Control"])
            self.widgets["Control"] = {"Type": "Property",
                                       "Control": {
                                                  "Detail": "ControlID",
                                                  "Allowed": "str",
                                                  "Unit": False,
                                                  "Size": 100
                                                  },
                                       "Optional": False
                                       }
        self.chk_Buffer.SetValue(False)
        self.txt_DefaultBuffer.SetValue("")
        self.txt_DefaultBuffer.Enable(False)
        if "Buffer" in self.details.keys():
            self.chk_Buffer.SetValue(True)
            self.txt_DefaultBuffer.Enable(True)
            self.txt_DefaultBuffer.SetValue(self.details["Buffer"])
            self.widgets["Buffer"] = {
                    "Type": "Multi Line Text Box",
                    "Detail": "Buffer",
                    "Lines": 3,
                    "Limit": False,
                    "Optional": False
                }
        self.chk_LIMS.SetValue(False)
        self.txt_LIMS.SetValue("")
        self.txt_LIMS.Enable(False)
        if "LIMS" in self.details.keys():
            self.chk_LIMS.SetValue(True)
            self.txt_LIMS.SetValue(self.details["LIMS"])
            self.txt_LIMS.Enable(True)
            self.widgets["LIMS"] = {"Type": "Property",
                                    "ELN Page": {
                                        "Detail": "ELN",
                                        "Allowed": "str",
                                        "Unit": False,
                                        "Size": 100
                                    },
                                    "Optional": False
                                   }
        self.chk_DateOfExperiment.SetValue(False)
        if "DateOfExperiment" in self.details.keys():
            self.chk_DateOfExperiment.SetValue(True)
            self.widgets["DateOfExperiment"] = {
                    "Type": "Date Picker",
                    "Detail": "DateOfExperiment",
                    "Optional": False
                }
        self.chk_DateOfAnalysis.SetValue(False)
        if "DateOfAnalysis" in self.details.keys():
            self.chk_DateOfAnalysis.SetValue(True)
            self.widgets["DateOfAnalysis"] = {
                    "Type": "Date Picker",
                    "Detail": "DateOfAnalysis",
                    "Optional": False
                }
        self.chk_AssayVolume.SetValue(False)
        self.txt_AssayVolume.Enable(False)
        self.txt_AssayVolume.SetValue("")
        self.cho_AssayVolumeUnit.Enable(False)
        if "AssayVolume" in self.details.keys():
            self.chk_AssayVolume.SetValue(True)
            self.txt_AssayVolume.Enable(True)
            self.txt_AssayVolume.SetValue(self.details["AssayVolume"])
            unit = self.details["AssayVolumeUnit"]
            idx = self.cho_AssayVolumeUnit.FindString(unit)
            self.cho_AssayVolumeUnit.Select(idx)
            self.widgets["AssayVolume"] = {"Type": "Property",
                                    "Assay Volume": {
                                        "Detail": "AssayVolume",
                                        "Allowed": "float",
                                        "Unit": unit,
                                        "Size": 100
                                    },
                                    "Optional": False
                                   }
            

    ##### #   # ##### #   # #####    #   #  ###  #   # ####  #     ##### ####   ####
    #     #   # #     ##  #   #      #   # #   # ##  # #   # #     #     #   # #
    ###   #   # ###   #####   #      ##### ##### ##### #   # #     ###   ####   ###
    #      # #  #     #  ##   #      #   # #   # #  ## #   # #     #     #   #     #
    #####   #   ##### #   #   #      #   # #   # #   # ####  ##### ##### #   # ####

    # Event handlers for simple book pages #########################################

    def on_txt_assay(self, event):
        """
        Event handler
        """        
        self.update_editor_label()

    def update_editor_label(self):
        """
        Updates label above button bar with assay name
        """
        assay = self.txt_Assay.GetValue()
        shorthand = self.txt_Shorthand.GetValue()
        self.wkflw.pnl_ButtonBar.lbl_Filename.SetLabel(f"{assay} ({shorthand})")

    def on_txt_shorthand(self, event):
        """
        Event handler.

        Ensures entered text is only all caps letters
        """
        text = event.GetEventObject()
        value = text.GetValue()
        # Find insertion point
        insert = event.GetEventObject().GetInsertionPoint()
        # Check if string is emtpty
        if not value == "":
            # Get new character
            if insert == len(value):
                new = value[-1]
            else:
                new = value[insert-1:insert]
            # Check if integer
            if not new.isalpha():
                # Reset text control
                reset = value[:insert-1] + value[insert:]
                text.ChangeValue(reset)
                text.SetInsertionPoint(insert-1)
            else:
                #Ensure uppercase and length of 6 chars
                text.ChangeValue(value.upper()[0:5])
                text.SetInsertionPoint(insert)
            self.assay["Meta"]["Shorthand"] = text.GetValue()

        self.update_editor_label()

    def on_rad_yes(self, event):
        """
        Event handler.
        Sets "Main Category" to "Plate Based"
        """
        self.rad_No.SetValue(False)
        self.assay["Meta"]["MainCategory"] = "Plate Based"

    def on_rad_no(self, event):
        """
        Event handler.
        Sets "Main Category" to "Other"
        """
        self.rad_Yes.SetValue(False)
        self.assay["Meta"]["MainCategory"] = "Other"

    def on_rad_sampleidtransfer(self, event):
        """
        Event Handler.
        """
        self.rad_SampleIDDataFile.SetValue(False)
        self.rad_SampleIDManual.SetValue(False)
        self.assay["DefaultDetails"]["SampleSource"] = "TransferFile"

    def on_rad_sampleidmanual(self, event):
        """
        Event Handler.
        """
        self.rad_SampleIDDataFile.SetValue(False)
        self.rad_SampleIDTransfer.SetValue(False)
        self.assay["DefaultDetails"]["SampleSource"] = "ManualEntry"

    def on_rad_sampleiddatafile(self, event):
        """
        Event Handler.
        """
        self.rad_SampleIDTransfer.SetValue(False)
        self.rad_SampleIDManual.SetValue(False)
        self.assay["DefaultDetails"]["SampleSource"] = "RawDataFile"

    def on_rad_dynamic(self, event):
        """
        Event handler
        """
        self.rad_ManualDefinition.SetValue(False)
        self.assay["DefaultDetails"]["PlateLayout"] = "Dynamic"
        
    def on_rad_manualdefinition(self, event):
        """
        Event handler
        """
        self.rad_Dynamic.SetValue(False)
        self.assay["DefaultDetails"]["PlateLayout"] = "Manual"

    def on_chk_concentration(self, event):
        """
        Event handler
        """
        concentration = event.GetEventObject().GetValue()
        self.rad_Molar.Enable(concentration)
        self.rad_Mass.Enable(concentration)

    def on_chk_recordname(self, event):
        """
        Event handler
        """
        name = event.GetEventObject().GetValue()
        self.txt_DefaultName.Enable(name)

    def on_chk_reagentbatch(self, event):
        """
        Event handler
        """
        batch = event.GetEventObject().GetValue()
        self.txt_DefaultBatch.Enable(batch)

    def on_chk_concentration(self, event):
        """
        Event handler
        """
        conc = event.GetEventObject().GetValue()
        self.rad_Molar.Enable(conc)
        self.rad_Mass.Enable(conc)
        self.txt_DefaultConc.Enable(conc)
        if conc == True:
            if self.rad_Molar.GetValue() == True:
                self.cho_Molar.Enable(True)
                self.cho_Mass.Enable(False)
            else:
                self.cho_Molar.Enable(False)
                self.cho_Mass.Enable(True)
        else:
            self.cho_Molar.Enable(False)
            self.cho_Mass.Enable(False)

    def on_rad_molar(self, event):
        """
        Event handler
        """
        conc = event.GetEventObject().GetValue()
        self.cho_Molar.Enable(conc)
        self.cho_Mass.Enable(not conc)
        unit = self.cho_Molar.GetString(self.cho_Molar.GetSelection())
        self.lbl_DefaultConcUnit.SetLabel(unit)

    def on_rad_mass(self, event):
        """
        Event handler
        """
        conc = event.GetEventObject().GetValue()
        self.cho_Molar.Enable(not conc)
        self.cho_Mass.Enable(conc)
        unit = self.cho_Mass.GetString(self.cho_Mass.GetSelection())
        self.lbl_DefaultConcUnit.SetLabel(unit)

    def on_unit_select(self, event):
        """
        Event handler.
        Called by either cho_Mass or cho_Molar. Updates StaticText with unit.
        """
        event_object = event.GetEventObject()
        unit = event_object.GetString(event_object.GetSelection())
        self.lbl_DefaultConcUnit.SetLabel(unit)

    def on_txt_defaultconc(self, event):
        """
        Event handler
        Ensures only floating point numbers can be entered.
        """
        text = event.GetEventObject()
        value = text.GetValue()
        # Find insertion point
        insert = event.GetEventObject().GetInsertionPoint()
        # Check if string is emtpty
        if not value == "":
            # Get new character
            if insert == len(value):
                new = value[-1]
            else:
                new = value[insert-1:insert]
            # Check if alphanumeric
            if not new.isnumeric():
                if not new == ".":
                    # Reset text control
                    reset = value[:insert-1] + value[insert:]
                    text.ChangeValue(reset)
                    text.SetInsertionPoint(insert-1)

    def on_btn_addreagent(self, event):
        """
        Adds a reagent to the list and to the rule set.
        If the name in txt_ReagentName is already in the
        ListCtrl, the corresponding entry will be updated.
        """

        reagent_name = self.txt_ReagentName.GetValue()
        self.assay["Reagents"][reagent_name] = {}

        if not reagent_name in self.widgets.keys():
            self.widgets[reagent_name] = {"Type":"Property"}

        if self.chk_RecordName.GetValue() == True:
            use_name = True
            default_name = self.txt_DefaultName.GetValue()
        else:
            use_name = False
            default_name = None

        if self.chk_ReagentBatch.GetValue() == True:
            use_batch = True
            default_batch = self.txt_DefaultBatch.GetValue()
        else:
            use_batch = False
            default_batch = None

        if self.chk_Concentration.GetValue() == True:
            use_concentration = True
            if self.rad_Mass.GetValue() == True:
                conc_unit = self.cho_Mass.GetString(self.cho_Mass.GetSelection())
            else:
                conc_unit = self.cho_Molar.GetString(self.cho_Molar.GetSelection())
            default_conc = self.txt_DefaultConc.GetValue()
        else:
            use_concentration = False
            conc_unit = None
            default_conc = None

        if self.chk_Optional.GetValue() == True:
            self.assay["Reagents"][reagent_name]["Optional"] = True
        else:
            self.assay["Reagents"][reagent_name]["Optional"] = False
        
        if not any(key.startswith(reagent_name) for key in self.details.keys()):
            row = self.lbc_Existing.GetItemCount()
            self.lbc_Existing.InsertItem(row, reagent_name)
        else:
            for row in range(self.lbc_Existing.GetItemCount()):
                if self.lbc_Existing.GetItemText(row,0) == reagent_name:
                    break # row will hold last value
        
        # Use "row" variable to update ListCtrl
        self.lbc_Existing.SetItem(row, 0, reagent_name)

        if use_name == True:
            self.lbc_Existing.SetItem(row, 1, default_name)
            self.assay["Reagents"][reagent_name]["Name"] = default_name
            self.widgets[reagent_name][f"{reagent_name} Name"]  = {"Detail":f"{reagent_name} Name",
                                                                   "Allowed":"str",
                                                                   "Unit":False,
                                                                   "Size":100}
        else:
            self.lbc_Existing.SetItem(row, 1, "")
            if "Name" in self.assay["Reagents"][reagent_name].keys():
                self.assay["Reagents"][reagent_name].pop("Name")
                self.widgets[reagent_name].pop(f"{reagent_name} Name")

        if use_batch == True:
            self.lbc_Existing.SetItem(row, 2, default_batch)
            self.assay["Reagents"][reagent_name]["Batch"] = default_batch
            self.widgets[reagent_name][f"{reagent_name} Batch"] = {"Detail":f"{reagent_name} Batch",
                                                                   "Allowed":"str",
                                                                   "Unit":False,
                                                                   "Size":100}
        else:
            self.lbc_Existing.SetItem(row, 2, "")
            if "Batch" in self.assay["Reagents"][reagent_name].keys():
                self.assay["Reagents"][reagent_name].pop("Batch")
                self.widgets[reagent_name].pop(f"{reagent_name} Batch")
        
        if use_concentration == True:
            self.lbc_Existing.SetItem(row, 3, default_conc)
            self.lbc_Existing.SetItem(row, 4, conc_unit)
            self.assay["Reagents"][reagent_name]["Conc"] = default_conc
            self.assay["Reagents"][reagent_name]["Conc Unit"] = conc_unit
            self.widgets[reagent_name][f"{reagent_name} concentration"] = {"Detail":f"{reagent_name} Conc",
                                                                           "Allowed":"float",
                                                                           "Unit":conc_unit,
                                                                           "Size":40}
        else:
            self.lbc_Existing.SetItem(row, 4, "")
            if f"{reagent_name} Conc" in self.assay["Reagents"].keys():
                self.assay["Reagents"][reagent_name].pop("Conc")
                self.reagents[reagent_name].pop("Conc Unit")
                self.widgets[reagent_name].pop(f"{reagent_name} concentration")

        self.widgets[reagent_name]["Optional"] = self.chk_Optional.GetValue()

        #for key in self.details.keys():
        #    print(f"{key}: {self.details[key]}")
        #for key in self.widgets.keys():
        #    print(self.widgets[key])

    def on_btn_deleteselected(self, event):
        """
        Event handler
        Deletes the reagent selected on lbc_Existing from the listCtrl and the dictionaries
        """
        # Find the selected reagent
        row = self.lbc_Existing.GetNextSelected(-1)
        rows = self.lbc_Existing.GetItemCount()
        if row == -1:
            return None
        
        reagent_name = self.lbc_Existing.GetItemText(row, 0)
        
        # print(row, reagent_name)
        
        # Avoid .keys() conflicting with changing dictionary size during
        # running of for loop
        self.lbc_Existing.DeleteItem(row)
        keys = list(self.details.keys())
        for key in keys:
            if reagent_name in key:
                self.details.pop(key)

        self.widgets.pop(reagent_name)
        
        #for key in self.details.keys():
        #    print(f"{key}: {self.details[key]}")
        #for key in self.widgets.keys():
        #    print(self.widgets[key])

        if row < rows:
            self.lbc_Existing.Select(row - 1)
        elif row == 0 and self.lbc_Existing.GetItemCount() > 0:
            self.lbc_Existing.Select(0)
        
        pass

    def on_click_lbcexisting(self, event):
        """
        Event handler.
        Updates UI elements for editing of details with valus for selected item
        in lbc_Existing
        """
        # Get the first selected item. Start at -1. There will always be only one
        # selected item.
        row = event.GetEventObject().GetNextSelected(-1)
        self.refresh_reagent(row)

    def refresh_reagent(self, row):
        """
        Refreshes the UI elements for the reagents with the indicated
        item from the lbc_Existing.
        """
        reagent_name = self.lbc_Existing.GetItemText(row, 0)
        self.txt_ReagentName.ChangeValue(reagent_name)

        if "Name" in self.reagents[reagent_name].keys():
            default_name = self.reagents[reagent_name]["Name"]
            self.chk_RecordName.SetValue(True)
            self.txt_DefaultName.ChangeValue(default_name)
        else:
            self.chk_RecordName.SetValue(False)
            self.txt_DefaultName.ChangeValue("")
            self.txt_DefaultName.Enable(False)

        if "Batch" in self.reagents[reagent_name].keys():
            default_batch = self.reagents[reagent_name]["Batch"]
            self.chk_ReagentBatch.SetValue(True)
            self.txt_DefaultBatch.ChangeValue(default_batch)
        else:
            self.chk_ReagentBatch.SetValue(False)
            self.txt_DefaultBatch.ChangeValue("")
            self.txt_DefaultBatch.Enable(False)

        if "Conc" in self.reagents[reagent_name].keys():
            default_conc = self.reagents[reagent_name]["Conc"]
            default_unit = self.reagents[reagent_name]["Conc Unit"]
            self.chk_Concentration.SetValue(True)
            self.cho_Molar.Enable(True)
            self.cho_Mass.Enable(True)
            self.txt_DefaultConc.ChangeValue(default_conc)
            self.txt_DefaultConc.Enable(True)
            # Select correct concentration.
            conc = self.cho_Molar.FindString(default_unit)
            if not conc == -1:
                self.rad_Molar.SetValue(True)
                self.rad_Mass.SetValue(False)
                self.cho_Molar.Enable(True)
                self.cho_Mass.Enable(False)
                self.cho_Molar.SetSelection(conc)
            else:
                conc = self.cho_Mass.FindString(default_unit)
                self.rad_Molar.SetValue(False)
                self.rad_Mass.SetValue(True)
                self.cho_Molar.Enable(False)
                self.cho_Mass.Enable(True)
                self.cho_Mass.SetSelection(conc)
            self.txt_DefaultConc.ChangeValue(default_conc)
            self.lbl_DefaultConcUnit.Enable(True)
            self.lbl_DefaultConcUnit.SetLabel(default_unit)
        else:
            self.chk_Concentration.SetValue(False)
            self.cho_Molar.Enable(False)
            self.cho_Mass.Enable(False)
            self.lbl_DefaultConc.Enable(False)
            self.txt_DefaultConc.Enable(False)
            self.lbl_DefaultConcUnit.Enable(False)

        if self.reagents[reagent_name]["Optional"] == True:
            self.chk_Optional.SetValue(True)
        else:
            self.chk_Optional.SetValue(False)
        #print(default_name, default_batch, default_conc, default_unit)

    def on_chk_control(self, event):
        """
        Event handler
        """        
        control = self.chk_Control.GetValue()
        self.lbl_Control.Enable(control)
        self.lbl_ControlText.Enable(control)
        self.txt_Control.Enable(control)
        if control == True:
            self.assay["DefaultDetails"]["Control"] = self.txt_Control.GetValue()
            self.widgets["Control"] = {"Type": "Property",
                                       "Control": {
                                                  "Detail": "ControlID",
                                                  "Allowed": "str",
                                                  "Unit": False,
                                                  "Size": 100
                                                  },
                                       "Optional": False
                                       }
        else:
            if "Control" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("Control")
            if "Control" in self.widgets.keys():
                self.widgets.pop("Control")

    def on_chk_buffer(self, event):
        """
        Event handler
        """
        buffer = self.chk_Buffer.GetValue()
        self.lbl_DefaultBuffer.Enable(buffer)
        self.txt_DefaultBuffer.Enable(buffer)
        if buffer == True:
            self.assay["DefaultDetails"]["Buffer"] = self.txt_DefaultBuffer.GetValue()
            self.widgets["Buffer"] = {
                    "Type": "Multi Line Text Box",
                    "Detail": "Buffer",
                    "Lines": 3,
                    "Limit": False,
                    "Optional": False
                }
        else:
            if "Buffer" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("Buffer")
            if "Buffer" in self.widgets.keys():
                self.widgets.pop("Buffer")

    def on_chk_lims(self, event):
        """
        Event handler
        """
        eln = self.chk_LIMS.GetValue()
        self.txt_LIMS.Enable(eln)
        if eln == True:
            self.assay["DefaultDetails"]["LIMS"] = self.txt_LIMS.GetValue()
            self.widgets["LIMS"] = {"Type": "Property",
                                    "ELN Page": {
                                        "Detail": "ELN",
                                        "Allowed": "str",
                                        "Unit": False,
                                        "Size": 100
                                    },
                                    "Optional": False
                                   }
        else:
            if "LIMS" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("LIMS")
            if "LIMS" in self.widgets.keys():
                self.widgets.pop("LIMS")

    def on_chk_dateofexperiment(self, event):
        """
        Event handler
        """
        date = self.chk_DateOfExperiment.GetValue()
        if date == True:
            self.assay["DefaultDetails"]["DateOfExperiment"] = ""
            self.widgets["DateOfExperiment"] = {
                    "Type": "Date Picker",
                    "Detail": "DateOfExperiment",
                    "Optional": False
                }
        else:
            if "DateOfExperiment" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("DateOfExperiment")
            if "DateOfExperiment" in self.widgets.keys():
                self.widgets.pop("DateOfExperiment")

    def on_chk_dateofanalysis(self, event):
        """
        Event handler
        """
        date = self.chk_DateOfAnalysis.GetValue()
        if date == True:
            self.assay["DefaultDetails"]["DateOfAnalysis"] = ""
            self.widgets["DateOfAnalysis"] = {
                    "Type": "Date Picker",
                    "Detail": "DateOfAnalysis",
                    "Optional": False
                }
        else:
            if "DateOfAnalysis" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("DateOfAnalysis")
            if "DateOfAnalysis" in self.widgets.keys():
                self.widgets.pop("DateOfAnalysis")

    def on_chk_assayvolume(self, event):
        """"
        Event handler
        """
        volume = self.chk_AssayVolume.GetValue()
        self.lbl_AssayVolume.Enable(volume)
        self.txt_AssayVolume.Enable(volume)
        self.cho_AssayVolumeUnit.Enable(volume)
        if volume == True:
            self.assay["DefaultDetails"]["AssayVolume"] = self.txt_AssayVolume.GetValue()
            idx = self.cho_AssayVolumeUnit.GetSelection()
            unit = self.cho_AssayVolumeUnit.GetString(idx)
            self.assay["DefaultDetails"]["AssayVolumeUnit"] = unit
            self.widgets["AssayVolume"] = {"Type": "Property",
                                    "Assay Volume": {
                                        "Detail": "AssayVolume",
                                        "Allowed": "float",
                                        "Unit": unit,
                                        "Size": 100
                                    },
                                    "Optional": False
                                   }
        else:
            if "AssayVolume" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("AssayVolume")
                self.assay["DefaultDetails"].pop("AssayVolumeUnit")

    def on_txt_assayvolume(self, event):
        """
        Event handler
        Ensures only floating point numbers can be entered.
        """
        text = event.GetEventObject()
        value = text.GetValue()
        # Find insertion point
        insert = event.GetEventObject().GetInsertionPoint()
        # Check if string is emtpty
        if not value == "":
            # Get new character
            if insert == len(value):
                new = value[-1]
            else:
                new = value[insert-1:insert]
            # Check if alphanumeric
            if not new.isnumeric():
                if not new == ".":
                    # Reset text control
                    reset = value[:insert-1] + value[insert:]
                    text.ChangeValue(reset)
                    text.SetInsertionPoint(insert-1)

    def on_cho_assayvolumeunit(self, event):
        """
        Event handler
        """
        idx = event.GetEventObject().GetSelection()
        unit = event.GetEventObject().GetString(idx)
        self.assay["DefaultDetails"]["AssayVolumeUnit"] = unit


    def CheckForDataFrame(self):
        """
        Checks whether rule_set exists and has been created properly.
        """
        if hasattr(self, "assay") == False:
            return False
        else:
            if len(self.assay) > 0:
                return True
            else:
                return False

    ####  #   # #     #####     ####  ###  #   # # #   #  ####
    #   # #   # #     #        #     #   # #   # # ##  # #
    ####  #   # #     ###       ###  ##### #   # # ##### #  ##
    #   # #   # #     #            # #   #  # #  # #  ## #   #
    #   #  ###  ##### #####    ####  #   #   #   # #   #  ####

    # Simplebook page saving functions #################################################

    def fun_Dummy(self):
        return "ForwardBackward"
    
    def save_metadata(self):

        str_Return = "Backward"
        # Author
        author = self.txt_Author.GetValue()
        if len(author) == 0:
            mb.info(self, "Workflow author name has not been entered.")
            str_Return = "Stop"
        else:
            self.assay["Meta"]["Author"] = author
            str_Return += "Forward"
        # Timestamp

        # Name of Assay
        assay_name = self.txt_Assay.GetValue()
        if len(assay_name) == 0:
            mb.info(self, "Assay name has not been defined")
            str_Return = "Stop"
        else:
            self.assay["Meta"]["FullName"] = assay_name
            str_Return += "Forward"
        # Shorthand
        shorthand = self.txt_Shorthand.GetValue()
        if len(shorthand) == 0:
            mb.info(self, "Assay shorthand has not been defined")
            str_Return = "Stop"
        else:
            self.assay["Meta"]["Shorthand"] = shorthand
            str_Return += "Forward"
        # Assay Name in database
        assaynamedb = self.txt_AssayNameDB.GetValue()
        if len(assaynamedb) == 0:
            mb.info(self, "Assay name for database has not been defined")
            str_Return = "Stop"
        else:
            self.assay["Meta"]["AssayNameDB"] = assaynamedb
            str_Return += "Forward"
        # Main Category
        if self.rad_Yes.GetValue() == True:
            self.assay["Meta"]["MainCategory"] = "Plate Based"
        elif self.rad_No.GetValue() == True:
            self.assay["Meta"]["MainCategory"] = "Other"
        # Secondary category:
        secondary = self.cho_SecondaryCategory.GetSelection()
        secondary = self.cho_SecondaryCategory.GetString(secondary)
        self.assay["Meta"]["SecondaryCategory"] = secondary

        return str_Return

    def save_sampleidsource(self):
        """
        
        This is really simple since the ruleset gets updated by the event handlers
        bound to the UI on this page. A special function might not be needed, but
        I like to keep it consistent.
        """

        if self.rad_SampleIDTransfer.GetValue() == True:
            self.assay["SampleIDSource"] = "TransferFile"
        elif self.rad_SampleIDManual.GetValue() == True:
            self.assay["SampleIDSource"] = "ManualEntry"
        elif self.rad_SampleIDDataFile.GetValue() == True:
            self.assay["SampleIDSource"] = "DataFile"

        return "ForwardBackward"
    
    def save_platelayout(self):

        if self.rad_Dynamic.GetValue() == True:
            self.assay["DefaultDetails"]["PlateLayout"] = "Dynamic"
        else:
            self.assay["DefaultDetails"]["PlateLayout"] = "Manual"

        return "ForwardBackward"

    def save_reagents(self):

        self.assay["Reagents"] = {}
        for row in range(0, self.lbc_Existing.GetItemCount()):
            reagent_name = self.lbc_Existing.GetItemText(row, 0)
            self.assay["Reagents"][reagent_name] = {}
            self.assay["Reagents"][reagent_name]["Name"] = self.lbc_Existing.GetItemText(row, 1)
            self.assay["Reagents"][reagent_name]["Batch"] = self.lbc_Existing.GetItemText(row, 2)
            self.assay["Reagents"][reagent_name]["Conc"] = self.lbc_Existing.GetItemText(row, 3)
            self.assay["Reagents"][reagent_name]["Conc Unit"] = self.lbc_Existing.GetItemText(row, 4)

        return "ForwardBackward"
    
    def save_miscellaneous(self):
        """
        Saves information from miscellaneous tab to rule set.
        """
        if self.chk_Buffer.GetValue() == True:
            self.assay["DefaultDetails"]["Buffer"] = self.txt_DefaultBuffer.GetValue()
        else:
            if "Buffer" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("Buffer")

        if self.chk_LIMS.GetValue() == True:
            self.assay["DefaultDetails"]["LIMS"] = self.txt_LIMS.GetValue()
        else:
            if "LIMS" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("LIMS")

        if self.chk_DateOfExperiment.GetValue() == True:
            self.assay["DefaultDetails"]["DateOfExperiment"] = ""
        else:
            if "DateOfExperiment" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("DateOfExperiment")

        if self.chk_DateOfAnalysis.GetValue() == True:
            self.assay["DefaultDetails"]["DateOfAnalysis"] = ""
        else:
            if "DateOfAnalysis" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("DateOfAnalysis")

        if self.chk_AssayVolume.GetValue() == True:
            self.assay["DefaultDetails"]["AssayVolume"] = self.txt_AssayVolume.GetValue()
            idx = self.cho_AssayVolumeUnit.GetSelection()
            unit = self.cho_AssayVolumeUnit.GetString(idx)
            self.assay["DefaultDetails"]["AssayVolumeUnit"] = unit
        else:
            if "AssayVolume" in self.assay["DefaultDetails"].keys():
                self.assay["DefaultDetails"].pop("AssayVolume")
                self.assay["DefaultDetails"].pop("AssayVolumeUnit")

        str_Return = "Backward"

        return str_Return

def CreateBlankRuleSet():
    rule_set = {"Buffer":u"20 mM HEPES, 100 mM NaCl, 2 mM TCEP, 0.5%(w/v) CHAPS, pH 7.5",
                "DateOfExperiment":"01/01/1970",
                "LIMS":"PAGE23-00271"}
    return rule_set
