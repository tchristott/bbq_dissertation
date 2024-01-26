
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
import shutil
import datetime
import json as js

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backend_bases import MouseButton
from matplotlib.figure import Figure

import editor.rawdatafunctions as rf
import lib_platefunctions as pf
import lib_excelfunctions as ef
import lib_messageboxes as mb
import lib_colourscheme as cs
import editor.fn_functiondesigner as fdfn

################################################################################################
##                                                                                            ##
##    #####   ######  ######  ##  ##  ##  ######    #####   ##  ##  ##      ######   #####    ##
##    ##  ##  ##      ##      ##  ### ##  ##        ##  ##  ##  ##  ##      ##      ##        ##
##    ##  ##  ####    ####    ##  ######  ####      #####   ##  ##  ##      ####     ####     ##
##    ##  ##  ##      ##      ##  ## ###  ##        ##  ##  ##  ##  ##      ##          ##    ##
##    #####   ######  ##      ##  ##  ##  ######    ##  ##   ####   ######  ######  #####     ##
##                                                                                            ##
################################################################################################

class DataProcessing (wx.Panel):

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
        self.assay = assay

        self.assay["DataProcessing"] = CreateBlankRuleSet()
        self.rule_set = self.assay["DataProcessing"]
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

        # #   #  #### ##### ####  #   #  #### ##### #  ###  #   #  ####
        # ##  # #       #   #   # #   # #       #   # #   # ##  # #
        # #####  ###    #   ####  #   # #       #   # #   # #####  ###
        # #  ##     #   #   #   # #   # #       #   # #   # #  ##     #
        # #   # ####    #   #   #  ###   ####   #   #  ###  #   # ####

        # Wizard Page: Instructions #####################################################
        self.pnl_Instructions = wx.ScrolledWindow(self.sbk_Wizard,
                                                  style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Instructions.SetScrollRate(5,5)
        self.pnl_Instructions.SetBackgroundColour(self.pnlbgclr)
        self.szr_Instructions = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Instructions = wx.StaticText(self.pnl_Instructions,
                                              label = u"Instructions")
        self.szr_Instructions.Add(self.lbl_Instructions, 0, wx.ALL, 5)
        # All elements added to sizer
        self.pnl_Instructions.SetSizer( self.szr_Instructions )
        self.pnl_Instructions.Layout()
        self.szr_Instructions.Fit( self.pnl_Instructions )
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Instructions, u"Instructions", True)
        self.dic_PageSaveFunctions["Instructions"] = self.fun_Dummy
        #################################################################################


        #   #  ###  ####  #   #  ###  #     #  ####  ###  ##### #  ###  #   #
        ##  # #   # #   # ## ## #   # #     # #     #   #   #   # #   # ##  #
        ##### #   # ####  ##### ##### #     #  ###  #####   #   # #   # #####
        #  ## #   # #   # # # # #   # #     #     # #   #   #   # #   # #  ##
        #   #  ###  #   # #   # #   # ##### # ####  #   #   #   #  ###  #   #

        # Wizard Page: Normalisation ###################################################
        self.pnl_Normalisation = wx.ScrolledWindow(self.sbk_Wizard,
                                                style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Normalisation.SetScrollRate(5,5)
        self.pnl_Normalisation.SetBackgroundColour(self.pnlbgclr)
        self.szr_Normalisation = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Normalisation = wx.StaticText(self.pnl_Normalisation,
                                            label = u"Choose data normalisation options:")
        self.szr_Normalisation.Add(self.lbl_Normalisation, 0, wx.ALL, 5)
        self.chk_BackgroundSubtraction = wx.CheckBox(self.pnl_Normalisation,
                                                     label = u"Subtract background")
        self.chk_BackgroundSubtraction.SetValue(True)
        self.szr_Normalisation.Add(self.chk_BackgroundSubtraction, 0, wx.ALL, 5)
        self.szr_Background = wx.FlexGridSizer(4,2,0,0)
        self.szr_Background.Add((15,5), 0, wx.ALL, 2)
        self.rad_ControlIsBackground = wx.RadioButton(self.pnl_Normalisation,
                                                      label = u"Control compound is background signal",
                                                      style = wx.RB_SINGLE)
        self.rad_ControlIsBackground.SetValue(True)
        self.szr_Background.Add(self.rad_ControlIsBackground, 0, wx.ALL, 2)
        self.szr_Background.Add((15,5), 0, wx.ALL, 2)
        self.rad_SolventIsBackground = wx.RadioButton(self.pnl_Normalisation,
                                                      label = u"Solvent-only-addition wells are background signal",
                                                      style = wx.RB_SINGLE)
        self.szr_Background.Add(self.rad_SolventIsBackground, 0, wx.ALL, 2)
        self.szr_Background.Add((15,5), 0, wx.ALL, 2)
        self.rad_BufferIsBackground = wx.RadioButton(self.pnl_Normalisation,
                                                     label = u"No-addition wells (only reagents) are background signal",
                                                     style = wx.RB_SINGLE)
        self.szr_Background.Add(self.rad_BufferIsBackground, 0, wx.ALL, 2)
        self.szr_Background.Add((15,5), 0, wx.ALL, 2)
        self.chk_BackgroundBackup = wx.CheckBox(self.pnl_Normalisation,
                                                     label = u"If no-addition/solvent is selected but not detected,\nuse other as replacement.")
        self.chk_BackgroundBackup.SetValue(True)
        self.chk_BackgroundBackup.Enable(False)
        self.szr_Background.Add(self.chk_BackgroundBackup, 0, wx.ALL, 2)
        self.szr_Normalisation.Add(self.szr_Background, 0, wx.ALL, 0)
        self.lin_Background = wx.StaticLine(self.pnl_Normalisation,
                                             style = wx.LI_HORIZONTAL)
        self.szr_Normalisation.Add(self.lin_Background, 0, wx.EXPAND|wx.ALL, 5)
        self.chk_NormToControl = wx.CheckBox(self.pnl_Normalisation,
                                             label = u"Normalisation to reference:")
        self.chk_NormToControl.SetValue(True)
        self.szr_Normalisation.Add(self.chk_NormToControl, 0, wx.ALL, 5)
        self.szr_NormalisationScales = wx.FlexGridSizer(4,2,0,0)
        self.szr_NormalisationScales.Add((15,5), 0, wx.ALL, 2)
        self.lbl_NormalisationOrder = wx.StaticText(self.pnl_Normalisation,
                                                    label = u"Baseline signal will be subtracted from all values before normalisation, including references.")
        self.lbl_NormalisationOrder.Wrap(380)
        self.szr_NormalisationScales.Add(self.lbl_NormalisationOrder, 0, wx.ALL, 2)
        self.szr_NormalisationScales.Add((15,5), 0, wx.ALL, 2)
        self.lbl_NormalisationScales = wx.StaticText(self.pnl_Normalisation,
                                                    label = u"Express normalised data as:")
        self.szr_NormalisationScales.Add(self.lbl_NormalisationScales, 0, wx.ALL, 2)
        self.szr_NormalisationScales.Add((15,5), 0, wx.ALL, 2)
        self.rad_Ratio = wx.RadioButton(self.pnl_Normalisation,
                                        label = u"Simple ratio (0 - 1)",
                                          style = wx.RB_SINGLE)
        self.rad_Ratio.SetValue(True)
        self.szr_NormalisationScales.Add(self.rad_Ratio, 0, wx.ALL, 2)
        self.szr_NormalisationScales.Add((15,5), 0, wx.ALL, 2)
        self.rad_PerCent = wx.RadioButton(self.pnl_Normalisation,
                                          label = u"Per cent value (0 - 100%)",
                                          style = wx.RB_SINGLE)
        self.szr_NormalisationScales.Add(self.rad_PerCent, 0, wx.ALL, 2)
        self.szr_Normalisation.Add(self.szr_NormalisationScales, 0, wx.ALL, 0)
        self.lin_NormalisationScales = wx.StaticLine(self.pnl_Normalisation,
                                                     style = wx.LI_HORIZONTAL)
        self.szr_Normalisation.Add(self.lin_NormalisationScales, 0, wx.EXPAND|wx.ALL, 5)
        self.chk_NormInvert = wx.CheckBox(self.pnl_Normalisation,
                                          label = u"Invert normalisation")
        self.szr_Normalisation.Add(self.chk_NormInvert, 0, wx.ALL, 5)
        self.szr_NormInvert = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_NormInvert.Add((15,5), 0, wx.ALL, 0)
        self.lbl_NormInvert = wx.StaticText(self.pnl_Normalisation,
                                            label = u"Select this option if your raw data corresponds to e.g. product formation but you want to express it as per-cent inhibition compared to a no-inhibitor reference.")
        self.lbl_NormInvert.Wrap(380)
        self.szr_NormInvert.Add(self.lbl_NormInvert, 0, wx.ALL, 0)
        self.szr_Normalisation.Add(self.szr_NormInvert, 0, wx.ALL, 5)
        
        # All elements added to sizer
        self.pnl_Normalisation.SetSizer(self.szr_Normalisation)
        self.pnl_Normalisation.Layout()
        self.szr_Normalisation.Fit(self.pnl_Normalisation)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Normalisation, u"Normalisation", False)
        self.dic_PageSaveFunctions["Normalisation"] = self.save_normalisation
        #################################################################################


        ####  ##### ####  #     #  #####  ###  ##### #####  ####
        #   # #     #   # #     # #      #   #   #   #     #
        ####  ###   ####  #     # #      #####   #   ###    ###
        #   # #     #   # #     # #      #   #   #   #         #
        #   # ##### #   # ##### #  ##### #   #   #   ##### ####

        # Wizard Page: Data Organisation ################################################
        self.pnl_Replicates = wx.ScrolledWindow(self.sbk_Wizard,
                                                style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Replicates.SetScrollRate(5,5)
        self.pnl_Replicates.SetBackgroundColour(self.pnlbgclr)
        self.szr_Replicates = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Datapoints = wx.StaticText(self.pnl_Replicates,
                                            label = u"Maximum number of datapoints")
        self.szr_Replicates.Add(self.lbl_Datapoints, 0, wx.ALL, 5)
        self.szr_Datapoints = wx.FlexGridSizer(4,2,0,0)
        self.szr_Datapoints.Add((5,15), 0, wx.ALL, 2)
        self.lbl_DatapointsNote = wx.StaticText(self.pnl_Replicates,
                                                label = u"For non-continuous assays, the number of datapoints is usually limited by the plate format. (e.g. 16 doses of a sample on a 384 well plate)")
        self.lbl_DatapointsNote.Wrap(390)
        self.szr_Datapoints.Add(self.lbl_DatapointsNote, 0, wx.ALL, 2)
        self.szr_Datapoints.Add((5,15), 0, wx.ALL, 2)
        self.szr_DatapointsTxt = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_DatapointsTxt = wx.StaticText(self.pnl_Replicates,
                                               label = u"Number of datapoints:")
        self.szr_DatapointsTxt.Add(self.lbl_DatapointsTxt, 0, wx.ALL|wx.CENTER, 0)
        self.szr_DatapointsTxt.Add((5,5), 0, wx.ALL, 0)
        self.txt_Datapoints = wx.TextCtrl(self.pnl_Replicates,
                                          value = u"16",
                                          size = wx.Size(30,25))
        self.szr_DatapointsTxt.Add(self.txt_Datapoints, 0, wx.ALL, 0)
        self.szr_Datapoints.Add(self.szr_DatapointsTxt, 0, wx.ALL, 2)
        self.szr_Replicates.Add(self.szr_Datapoints, 0, wx.ALL, 0)
        self.lin_Datapoints = wx.StaticLine(self.pnl_Replicates,
                                            style = wx.LI_HORIZONTAL)
        self.szr_Replicates.Add(self.lin_Datapoints, 0, wx.EXPAND|wx.ALL, 5)
        self.lbl_Replicates = wx.StaticText(self.pnl_Replicates,
                                            label = u"How to deal with replicates:")
        self.szr_Replicates.Add(self.lbl_Replicates, 0, wx.ALL, 5)
        self.rad_SamePlate = wx.RadioButton(self.pnl_Replicates,
                                          label = u"Replicates are on same plate",
                                          style = wx.RB_SINGLE)
        self.rad_SamePlate.SetValue(True)
        self.szr_Replicates.Add(self.rad_SamePlate, 0, wx.ALL, 5)
        self.rad_AcrossPlates = wx.RadioButton(self.pnl_Replicates,
                                               label = u"Replicates are across plates",
                                               style = wx.RB_SINGLE)
        self.szr_Replicates.Add(self.rad_AcrossPlates, 0, wx.ALL, 5)
        self.lin_ReplicatesWhere = wx.StaticLine(self.pnl_Replicates,
                                                 style = wx.LI_HORIZONTAL)
        self.szr_Replicates.Add(self.lin_ReplicatesWhere, 0, wx.ALL, 5)
        self.chk_ReplicateError = wx.CheckBox(self.pnl_Replicates,
                                              label = u"Calculate errors between replicates:")
        self.szr_Replicates.Add(self.chk_ReplicateError, 0, wx.ALL, 5)
        self.rad_StandardDeviation = wx.RadioButton(self.pnl_Replicates,
                                               label = u"Standard Deviation",
                                               style = wx.RB_SINGLE)
        self.rad_StandardDeviation.SetValue(True)
        self.szr_Replicates.Add(self.rad_StandardDeviation, 0, wx.ALL, 5)
        #self.szr_StandardDeviation = wx.BoxSizer(wx.HORIZONTAL)
        #self.szr_StandardDeviation.Add((15,5), 0, wx.ALL, 0)
        #self.lbl_StandardDeviation = wx.StaticText(self.pnl_Replicates,
        #                                           label = u"When To Use This Error")
        #self.szr_StandardDeviation.Add(self.lbl_StandardDeviation, 0, wx.ALL, 0)
        #self.bmp_StandardDeviation = wx.StaticBitmap(self.pnl_Replicates,
        #                                             bitmap = wx.Bitmap(f"{self.location}\standard_deviation.png"))
        #self.szr_StandardDeviation.Add(self.bmp_StandardDeviation, 0, wx.ALL, 0)
        #self.szr_Replicates.Add(self.szr_StandardDeviation, 0, wx.ALL, 5)
        self.rad_StandardError = wx.RadioButton(self.pnl_Replicates,
                                               label = u"Standard Error of the Mean",
                                               style = wx.RB_SINGLE)
        self.szr_Replicates.Add(self.rad_StandardError, 0, wx.ALL, 5)
        self.szr_StandardError = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_StandardError.Add((15,5), 0, wx.ALL, 0)
        #self.lbl_StandardError = wx.StaticText(self.pnl_Replicates,
        #                                       label = u"When To Use This Error")
        #self.lbl_StandardError.Enable(False)
        #self.szr_StandardError.Add(self.lbl_StandardError, 0, wx.ALL, 0)
        self.szr_Replicates.Add(self.szr_StandardError, 0, wx.ALL, 5)
        # All elements added to sizer
        self.pnl_Replicates.SetSizer(self.szr_Replicates)
        self.pnl_Replicates.Layout()
        self.szr_Replicates.Fit(self.pnl_Replicates)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Replicates, u"Replicates", False)
        self.dic_PageSaveFunctions["Replicates"] = self.save_replicates
        #################################################################################

        ##### # ##### ##### # #   #  ####
        #     #   #     #   # ##  # #
        ###   #   #     #   # ##### #   ##
        #     #   #     #   # #  ## #    #
        #     #   #     #   # #   #  #####

        # Wizard Page: Fitting FUnction #################################################

        TMIndigo_RGB = wx.Colour(51,34,136)
        TMBlue_RGB =  wx.Colour(68,119,170)
        TMCyan_RGB = wx.Colour(136,204,238)
        TMTeal_RGB = wx.Colour(68,180,153)
        TMGreen_RGB = wx.Colour(17,119,51)
        TMOlive_RGB = wx.Colour(153,153,51)
        TMSand_RGB = wx.Colour(201,204,119)
        TMRose_RGB = wx.Colour(204,102,119)
        TMWine_RGB = wx.Colour(136,34,85)
        TMPurple_RGB = wx.Colour(170,68,153)
        self.TM_RGB_List = [TMIndigo_RGB, TMBlue_RGB, TMCyan_RGB, TMTeal_RGB, TMGreen_RGB,
                            TMOlive_RGB, TMSand_RGB, TMRose_RGB, TMWine_RGB, TMPurple_RGB]
        self.dic_ParamColours = {}

        lst_XData = [200, 100, 50, 25, 12.5, 6.25, 3.125, 1.5625, 0.78125, 0.390625]
        lst_YData = [100, 100, 95, 80, 50, 20, 5, 0, 0, 0]

        self.lst_ParameterBlacklist = ["def","exp","sin","cos","tan","log"]

        self.pnl_Function = wx.ScrolledWindow(self.sbk_Wizard,
                                              style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Function.SetScrollRate(5,5)
        self.pnl_Function.SetBackgroundColour(self.pnlbgclr)
        self.szr_Function = wx.BoxSizer(wx.VERTICAL)
        self.chk_Function = wx.CheckBox(self.pnl_Function,
                                        label = u"Fit a model to the datapoints")
        self.chk_Function.SetValue(True)
        self.szr_Function.Add(self.chk_Function, 0, wx.ALL, 5)

        self.szr_Definition = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_IndependentAndParameters = wx.BoxSizer(wx.VERTICAL)
        # Independent Variable
        self.szr_Independent = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Independent = wx.StaticText(parent = self.pnl_Function,
                                             label = u"Independent variable:")
        self.szr_Independent.Add(self.lbl_Independent, 0, wx.ALL, 5)
        self.szr_IndependentText = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_Independent = wx.TextCtrl(parent = self.pnl_Function,
                                           value = u"x",
                                           size = wx.Size(75,25),
                                           style = wx.TE_PROCESS_ENTER)
        self.txt_Independent.SetMaxLength(10)
        self.txt_Independent.Enable(False)
        self.szr_IndependentText.Add(self.txt_Independent, 0, wx.ALL, 0)
        self.szr_IndependentText.Add((5,25), 0, wx.ALL, 0)
        self.tgl_Independent = wx.ToggleButton(parent = self.pnl_Function,
                                               label =  u"Edit",
                                               size = wx.Size(50,25))
        self.tgl_Independent.SetValue(False)
        self.szr_IndependentText.Add(self.tgl_Independent, 0, wx.ALL,0)
        self.szr_Independent.Add(self.szr_IndependentText, 0, wx.ALL, 5)
        self.szr_IndependentAndParameters.Add(self.szr_Independent, 0, wx.ALL, 0)
        self.lin_Independent = wx.StaticLine(self.pnl_Function,
                                                 style = wx.LI_HORIZONTAL)
        self.szr_IndependentAndParameters.Add(self.lin_Independent, 0, wx.ALL, 5)
        # Parameters \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.szr_Parameters = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Parameters = wx.StaticText(parent = self.pnl_Function,
                                            label = u"Function parameters (up to 10 alphanumeric characters)")
        self.lbl_Parameters.Wrap(130)
        self.szr_Parameters.Add(self.lbl_Parameters, 0, wx.ALL, 5)
        self.szr_ParameterBox = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_Parameter = wx.TextCtrl(parent = self.pnl_Function,
                                         value = u"AParameter",
                                         size = wx.Size(75,25),
                                         style = wx.TE_PROCESS_ENTER)
        self.txt_Parameter.SetMaxLength(10)
        self.szr_ParameterBox.Add(self.txt_Parameter, 0, wx.ALL, 0)
        self.szr_ParameterBox.Add((5,25), 0, wx.ALL, 0)
        self.btn_AddParameter = wx.Button(parent = self.pnl_Function,
                                          label =  u"Add",
                                          size = wx.Size(50,25))
        self.szr_ParameterBox.Add(self.btn_AddParameter, 0, wx.ALL, 0)
        self.szr_Parameters.Add(self.szr_ParameterBox, 0, wx.ALL, 5)
        self.lbx_Parameters = wx.ListBox(parent = self.pnl_Function,
                                         size =  wx.Size(130,200))
                                         #choices = ["ybot","ytop","h","i"])
        self.szr_Parameters.Add(self.lbx_Parameters, 0, wx.ALL, 5)
        self.szr_IndependentAndParameters.Add(self.szr_Parameters, 0, wx.ALL, 0)
        self.szr_Definition.Add(self.szr_IndependentAndParameters, 0, wx.ALL, 5)
        self.lin_Parameters = wx.StaticLine(self.pnl_Function,
                                            style = wx.LI_VERTICAL)
        self.szr_Definition.Add(self.lin_Parameters, 0, wx.ALL|wx.EXPAND, 5)
        # Define function \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        self.szr_DefineFunction = wx.BoxSizer(wx.VERTICAL)
        self.lbl_DefineFunction = wx.StaticText(parent = self.pnl_Function,
                                                label = u"Define function: (200 characters max)")
        self.szr_DefineFunction.Add(self.lbl_DefineFunction, 0, wx.ALL, 5)
        self.szr_FunctionTextbox = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Y = wx.StaticText(parent = self.pnl_Function,
                                   label = u"Y = ")
        self.szr_FunctionTextbox.Add(self.lbl_Y, 0, wx.ALL, 5)
        self.txt_DefineFunction = wx.TextCtrl(parent = self.pnl_Function,
                                              value = "ybot + (ytop - ybot)/(1 + (i/x)**h)",
                                              size = wx.Size(240,60),
                                              style = wx.TE_MULTILINE|wx.TE_RICH)
        self.txt_DefineFunction.SetMaxLength(200)
        self.szr_FunctionTextbox.Add(self.txt_DefineFunction, 0, wx.ALL, 0)
        self.szr_DefineFunction.Add(self.szr_FunctionTextbox, 0, wx.ALL, 5)
        self.lbl_DefineFunctionExplainer = wx.StaticText(parent = self.pnl_Function,
                                                         label = u"Write function in the field above.")
        self.szr_DefineFunction.Add(self.lbl_DefineFunctionExplainer, 0, wx.ALL, 5)
        self.szr_Definition.Add(self.szr_DefineFunction, 0, wx.ALL, 0)
        self.szr_Function.Add(self.szr_Definition, 0, wx.ALL, 0)

        self.pnl_Function.SetSizer(self.szr_Function)
        self.pnl_Function.Layout()
        self.szr_Function.Fit(self.pnl_Function)
        # Add to simplebook ############################################################
        self.sbk_Wizard.AddPage(self.pnl_Function, u"Function", False)
        self.dic_PageSaveFunctions["Function"] = self.save_function
        ################################################################################

        # Add simplebook to main sizer #################################################
        self.szr_Wizard.Add(self.sbk_Wizard, 1, wx.EXPAND|wx.ALL, 5)

        # Simplebook Next/Back/Finish buttons ##########################################
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

        # Finish RawDataWizard Sizer
        self.szr_Surround.Add(self.pnl_Wizard, 0, wx.EXPAND, 5)


        # Function test panel ##########################################################
        self.pnl_TestFunction = wx.Panel(parent = self)
        self.szr_TestFunction = wx.BoxSizer(wx.HORIZONTAL)
        # Example data ##################################################################
        self.pnl_ExampleData = wx.Panel(parent = self.pnl_TestFunction)
        self.szr_ExampleData = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ExampleData = wx.StaticText(parent = self.pnl_ExampleData,
                                             label = u"Example data")
        self.szr_ExampleData.Add(self.lbl_ExampleData, 0, wx.ALL, 5)
        # Gridl - Database
        self.grd_ExampleData = wx.grid.Grid(parent = self.pnl_ExampleData)
        # Grid
        self.grd_ExampleData.CreateGrid(20, 2)
        self.grd_ExampleData.EnableEditing(True)
        self.grd_ExampleData.EnableGridLines(True)
        self.grd_ExampleData.EnableDragGridSize(False)
        self.grd_ExampleData.SetMargins(0, 0)
        # Columns
        self.grd_ExampleData.EnableDragColMove(False)
        self.grd_ExampleData.EnableDragColSize(True)
        self.grd_ExampleData.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.grd_ExampleData.SetColLabelValue(0, u"XData")
        self.grd_ExampleData.SetColLabelValue(1, u"YData")
        # Rows
        self.grd_ExampleData.EnableDragRowSize(False)
        self.grd_ExampleData.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.grd_ExampleData.SetRowLabelSize(25)
        # Label Appearance
        # Cell Defaults
        self.grd_ExampleData.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.grd_ExampleData.SingleSelection = (0,0)
        # Fill grid with testdata
        for row in range(len(lst_XData)):
            self.grd_ExampleData.SetCellValue(row, 0, str(lst_XData[row]))
            self.grd_ExampleData.SetCellValue(row, 1, str(lst_YData[row]))
        self.szr_ExampleData.Add(self.grd_ExampleData, 0, wx.ALL, 5)
        self.pnl_ExampleData.SetSizer(self.szr_ExampleData)
        self.pnl_ExampleData.Layout()
        self.szr_ExampleData.Fit(self.pnl_ExampleData)
        self.szr_TestFunction.Add(self.pnl_ExampleData, 0, wx.ALL, 5)
        # Example Data Plot #############################################################
        self.pnl_ExamplePlot = wx.Panel(parent = self.pnl_TestFunction)
        self.szr_ExamplePlot = wx.BoxSizer(wx.VERTICAL)
        self.plt_ExamplePlot = ExamplePlot(self.pnl_ExamplePlot, (400,300))
        self.szr_ExamplePlot.Add(self.plt_ExamplePlot, 0, wx.ALL, 5)
        self.chk_XDataLogScale = wx.CheckBox(parent = self.pnl_ExamplePlot,
                                             label = u"XData on log10 scale")
        self.szr_ExamplePlot.Add(self.chk_XDataLogScale, 0, wx.ALL, 5)
        self.btn_ExamplePlot = wx.Button(self.pnl_ExamplePlot, wx.ID_ANY,
                                         u"Plot example data", wx.DefaultPosition,
                                         wx.DefaultSize, 0)
        self.szr_ExamplePlot.Add(self.btn_ExamplePlot, 0, wx.ALL, 5)
        self.btn_TestFunction = wx.Button(self.pnl_ExamplePlot,
                                          label = u"Test Function")
        self.szr_ExamplePlot.Add(self.btn_TestFunction, 0, wx.ALL, 5)
        self.pnl_ExamplePlot.SetSizer(self.szr_ExamplePlot)
        self.pnl_ExamplePlot.Layout()
        self.szr_ExamplePlot.Fit(self.pnl_ExamplePlot)
        self.szr_TestFunction.Add(self.pnl_ExamplePlot, 0, wx.ALL, 5)
        # Parameter values ##############################################################
        self.pnl_ParameterValues = wx.Panel(parent = self.pnl_TestFunction,
                                            name = u"ParameterValues")
        self.szr_ParameterValues = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ParamterValues = wx.StaticText(parent = self.pnl_ParameterValues,
                                                label = u"Parameter Values")
        self.szr_ParameterValues.Add(self.lbl_ParamterValues, 0, wx.ALL, 5)
        self.lbc_ParameterValues = wx.ListCtrl(parent = self.pnl_ParameterValues,
                                                size = wx.Size(150,200),
                                                style = wx.LC_REPORT)
        self.lbc_ParameterValues.AppendColumn(heading = u"Parameter",
                                              width = 75)
        self.lbc_ParameterValues.AppendColumn(heading = u"Value",
                                              width = 75)
        self.szr_ParameterValues.Add(self.lbc_ParameterValues, 0, wx.ALL, 5)
        self.pnl_ParameterValues.SetSizer(self.szr_ParameterValues)
        self.pnl_ParameterValues.Layout()
        self.szr_ParameterValues.Fit(self.pnl_ParameterValues)
        self.szr_TestFunction.Add(self.pnl_ParameterValues, 0, wx.ALL, 5)
        self.pnl_TestFunction.SetSizer(self.szr_TestFunction)
        self.pnl_TestFunction.Layout()
        self.szr_TestFunction.Fit(self.pnl_TestFunction)
        self.szr_Surround.Add(self.pnl_TestFunction, 1, wx.ALL, 5)
        self.pnl_TestFunction.Show(False)

        #############################################################################################################################################

        self.SetSizer(self.szr_Surround)
        self.Layout()

        self.Centre(wx.BOTH)

        ####  # #   # ####  # #   #  ####
        #   # # ##  # #   # # ##  # #
        ####  # ##### #   # # ##### #  ##
        #   # # #  ## #   # # #  ## #   #
        ####  # #   # ####  # #   #  ####

        # Bindings ##################################################################################################################################

        # Replicates
        self.txt_Datapoints.Bind(wx.EVT_TEXT, self.on_txt_datapoints)
        self.txt_Datapoints.Bind(wx.EVT_TEXT_PASTE, self.on_paste_datapoints)
        self.rad_SamePlate.Bind(wx.EVT_RADIOBUTTON, self.on_rad_sameplate)
        self.rad_AcrossPlates.Bind(wx.EVT_RADIOBUTTON, self.on_rad_acrossplates)
        self.chk_ReplicateError.Bind(wx.EVT_CHECKBOX, self.on_chk_replicate_error)
        self.rad_StandardDeviation.Bind(wx.EVT_RADIOBUTTON, self.on_rad_standarddeviaton)
        self.rad_StandardError.Bind(wx.EVT_RADIOBUTTON, self.on_rad_standarderror)

        # Normalisation
        self.chk_BackgroundSubtraction.Bind(wx.EVT_CHECKBOX, self.on_chk_backgroundsubtraction)
        self.rad_ControlIsBackground.Bind(wx.EVT_RADIOBUTTON, self.on_rad_controlisbackground)
        self.rad_SolventIsBackground.Bind(wx.EVT_RADIOBUTTON, self.on_rad_solventisbackground)
        self.rad_BufferIsBackground.Bind(wx.EVT_RADIOBUTTON, self.on_rad_bufferisbackground)
        self.chk_BackgroundBackup.Bind(wx.EVT_CHECKBOX, self.on_chk_backgroundbackup)
        self.chk_NormToControl.Bind(wx.EVT_CHECKBOX, self.on_chk_normtocontrol)
        self.rad_Ratio.Bind(wx.EVT_RADIOBUTTON, self.on_rad_ratio)
        self.rad_PerCent.Bind(wx.EVT_RADIOBUTTON, self.on_rad_percent)

        # Fitting
        self.chk_Function.Bind(wx.EVT_CHECKBOX, self.on_chk_function)
        # Example Data
        self.grd_ExampleData.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_grd_rightclick)
        self.grd_ExampleData.Bind(wx.EVT_KEY_DOWN, self.on_grd_keypress)
        self.grd_ExampleData.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.SingleSelection)
        # Independent variable
        self.txt_Independent.Bind(wx.EVT_TEXT, self.on_txt_independent)
        self.tgl_Independent.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_independent)
        self.tgl_Independent.Bind(wx.EVT_TEXT_PASTE, self. on_toggle_independent)
        # Parameters
        self.txt_Parameter.Bind(wx.EVT_TEXT, self.on_txt_parameter)
        self.txt_Parameter.Bind(wx.EVT_TEXT_ENTER, self.on_enter_parameter)
        self.txt_Parameter.Bind(wx.EVT_TEXT_PASTE, self.on_paste_parameter)
        self.btn_AddParameter.Bind(wx.EVT_BUTTON, self.on_btn_addparameter)
        self.lbx_Parameters.Bind(wx.EVT_RIGHT_UP, self.OpenParameterContextMenu)

        self.chk_XDataLogScale.Bind(wx.EVT_CHECKBOX, self.OnChkXDataLogScale)
        self.btn_ExamplePlot.Bind(wx.EVT_BUTTON, self.OnBtnExamplePlot)

        # Function
        self.txt_DefineFunction.Bind(wx.EVT_TEXT, self.FunctionLinter)
        self.txt_DefineFunction.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressTxtDefineFunction)
        self.txt_DefineFunction.Bind(wx.EVT_TEXT_PASTE, self.OnPasteTxtDefineFunction)
        self.txt_DefineFunction.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDownTxtDefineFunction)
        self.btn_TestFunction.Bind(wx.EVT_BUTTON, self.OnBtnTestFunction)

        # Wizard navigation buttons
        self.btn_WizardBack.Bind(wx.EVT_BUTTON, self.on_wzd_back)
        self.btn_WizardNext.Bind(wx.EVT_BUTTON, self.on_wzd_next)
        self.btn_WizardPrintRules.Bind(wx.EVT_BUTTON, self.PrintRules)



        # Initialise parameter colours dictionary -> testing purposes
        self.AssignParameterColours()
        self.PreviousInsertion = -1
        self.PreviousDefinition = self.txt_DefineFunction.GetValue()
        self.FunctionLinter(event = None)

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
                # Provision to hide example data/function plot
                if int_CurrentPage == 3:
                    self.pnl_TestFunction.Hide()
                    self.Layout()
                elif int_BackPage == 3:
                    self.pnl_TestFunction.Show()
                    self.Layout()
        
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
                # Provision to hide example data/function plot
                if int_CurrentPage == 3:
                    self.pnl_TestFunction.Hide()
                    self.Layout()
                elif int_NextPage == 3:
                    self.pnl_TestFunction.Show()
                    self.Layout()
        else:
            mb.info(self, "One or more fields have not been filled out.")

        # Check for grid highlights:
    

    ##### #   # ##### #   # #####    #   #  ###  #   # ####  #     ##### ####   ####
    #     #   # #     ##  #   #      #   # #   # ##  # #   # #     #     #   # #
    ###   #   # ###   #####   #      ##### ##### ##### #   # #     ###   ####   ###
    #      # #  #     #  ##   #      #   # #   # #  ## #   # #     #     #   #     #
    #####   #   ##### #   #   #      #   # #   # #   # ####  ##### ##### #   # ####

    # Event handlers for simple book pages ##########################################################################################################

    def on_txt_datapoints(self, event):
        """
        Checks if entered character is a number
        """
        # Get text
        str_TextControl = event.GetEventObject().GetValue()
        # Find insertion point
        int_Insertion = event.GetEventObject().GetInsertionPoint()
        # Check if string is emtpty
        if not str_TextControl == "":
            # Get new character
            if int_Insertion == len(str_TextControl):
                str_NewCharacter = str_TextControl[-1]
            else:
                str_NewCharacter = str_TextControl[int_Insertion-1:int_Insertion]
            # Check if alphanumeric
            if str_NewCharacter.isnumeric() == False:
                # Reset text control
                str_Reset = str_TextControl[:int_Insertion-1] + str_TextControl[int_Insertion:]
                event.GetEventObject().ChangeValue(str_Reset)
                event.GetEventObject().SetInsertionPoint(int_Insertion-1)
        self.update_datapoints()

    def on_paste_datapoints(self, event):
        """
        Trim any non-numeric characters from the pasted text.
        """
        obj_Text = wx.TextDataObject()
        if wx.TheClipboard.Open():
            bol_Success = wx.TheClipboard.GetData(obj_Text)
            wx.TheClipboard.Close()
        if bol_Success:
            str_Paste = obj_Text.GetText()
            str_Checked = ""
            for char in str_Paste:
                if char.isnumeric() == True: 
                    str_Checked += char
            if len(str_Checked) > 0:
                event.GetEventObject().ChangeValue(str_Checked)
        self.update_datapoints()

    def update_datapoints(self):
        """
        Updates rule set with the number of datapoints
        """
        self.rule_set["MaxDatapoints"] = int(self.txt_Datapoints.GetValue())

    def on_rad_sameplate(self, event):
        self.rad_AcrossPlates.SetValue(False)
        self.rule_set["ReplicatesAcrossPlates"] = False
        self.rule_set["ReplicatesSamePlate"] = True

    def on_rad_acrossplates(self, event):
        self.rad_SamePlate.SetValue(False)
        self.rule_set["ReplicatesAcrossPlates"] = True
        self.rule_set["ReplicatesSamePlate"] = False

    def on_chk_replicate_error(self, event):
        replicates = event.GetEventObject().GetValue()
        self.rad_StandardDeviation.Enable(replicates)
        #self.lbl_StandardDeviation.Enable(replicates)
        self.rad_StandardError.Enable(replicates)
        #self.lbl_StandardError.Enable(replicates)
        
    def on_rad_standarderror(self, event):
        #self.lbl_StandardError.Enable(True)
        self.rad_StandardDeviation.SetValue(False)
        #self.lbl_StandardDeviation.Enable(False)
        self.rule_set["ReplicateErrorTyoe"] = "StandardError"

    def on_rad_standarddeviaton(self, event):
        #self.lbl_StandardDeviation.Enable(True)
        self.rad_StandardError.SetValue(False)
        #self.lbl_StandardError.Enable(False)
        self.rule_set["ReplicateErrorTyoe"] = "StandardDeviation"

    def on_chk_backgroundsubtraction(self, event):
        """
        Event handler for check box "SubtractBackground"
        Updates UI elements with value of checkbock to disable/enable them.
        Also updates rule set
        """
        normalise = event.GetEventObject().GetValue()
        self.rule_set["SubtractBackground"] = normalise
        self.rad_ControlIsBackground.Enable(normalise)
        self.rad_SolventIsBackground.Enable(normalise)
        self.rad_BufferIsBackground.Enable(normalise)
        self.chk_BackgroundBackup.Enable(normalise)
        
    def on_rad_controlisbackground(self, event):
        """
        Event handler.
        Sets ruleset parameter "UseAsBackground" to True and updates
        UI elements of other options
        """
        self.rule_set["UseAsBackground"] = "Control"
        self.rad_SolventIsBackground.SetValue(False)
        self.rad_BufferIsBackground.SetValue(False)
        self.chk_BackgroundBackup.Enable(False)

    def on_rad_solventisbackground(self, event):
        """
        Event handler.
        Sets ruleset parameter "UseAsBackground" to True and updates
        UI elements of other options
        """
        self.rule_set["UseAsBackground"] = "Solvent"
        self.rad_ControlIsBackground.SetValue(False)
        self.rad_BufferIsBackground.SetValue(False)
        self.chk_BackgroundBackup.Enable(True)

    def on_rad_bufferisbackground(self, event):
        """
        Event handler.
        Sets ruleset parameter "UseAsBackground" to True and updates
        UI elements of other options
        """
        self.rule_set["UseAsBackground"] = "Solvent"
        self.rad_ControlIsBackground.SetValue(False)
        self.rad_SolventIsBackground.SetValue(False)
        self.chk_BackgroundBackup.Enable(True)

    def on_chk_backgroundbackup(self, event):
        """
        Event handler.
        Sets rule set parameter "BackgroundBackup" to value of
        check box.
        If this is enabled/True, normalisation will fail over to no-addition
        wells, if solvent is selected for normalisation but not detected, or vice versa.
        """
        self.rule_set["BackgroundBackup"] = event.GetEventObject().GetValue()

    def on_chk_normtocontrol(self, event):
        """
        Event handler for check box "NormaliseToControl"
        Updates UI elements with value of checkbock to disable/enable them.
        Also updates rule set
        """
        normalise = event.GetEventObject().GetValue()
        self.rule_set["NormaliseData"] = normalise
        self.lbl_NormalisationOrder.Enable(normalise)
        self.lbl_NormalisationScales.Enable(normalise)
        self.rad_Ratio.Enable(normalise)
        self.rad_PerCent.Enable(normalise)

    def on_rad_ratio(self, event):
        """
        Event handler.
        Sets expression of normalisation as simple ratio from 0-1 and updates
        UI elements accordinly.
        """
        self.rad_PerCent.SetValue(False)
        self.rule_set["NormalisedValue"] = "Ratio"

    def on_rad_percent(self, event):
        """
        Event handler.
        Sets expression of normalisation as simple prcentage from 0-100 and updates
        UI elements accordinly.
        """
        self.rad_Ratio.SetValue(False)
        self.rule_set["NormalisedValue"] = "PerCent"

    def on_chk_function(self, event):
        """
        Event handler.
        Hides/shows the ui elements for defining the function.
        """
        fitting = event.GetEventObject().GetValue()
        self.rule_set["DataFitting"] = fitting

        self.lbl_Independent.Enable(fitting)
        self.tgl_Independent.Enable(fitting)
        indie = self.tgl_Independent.GetValue()
        if fitting == True and indie == False:
            self.txt_Independent.Enable(indie)
        else:
            self.txt_Independent.Enable(fitting)
        self.lbl_Parameters.Enable(fitting)
        self.txt_Parameter.Enable(fitting)
        self.btn_AddParameter.Enable(fitting)
        self.lbx_Parameters.Enable(fitting)
        self.lbl_DefineFunction.Enable(fitting)
        self.lbl_Y.Enable(fitting)
        self.txt_DefineFunction.Enable(fitting)
        self.lbl_DefineFunctionExplainer.Enable(fitting)
        self.lbl_ExampleData.Enable(fitting)
        self.grd_ExampleData.Enable(fitting)
        self.plt_ExamplePlot.Enable(fitting)
        self.chk_XDataLogScale.Enable(fitting)
        self.btn_ExamplePlot.Enable(fitting)
        self.btn_TestFunction.Enable(fitting)
        self.lbl_ParamterValues.Enable(fitting)
        self.lbc_ParameterValues.Enable(fitting)


    def PrintRules(self, event):
        print("Rule set:")
        print(js.dumps(self.assay, sort_keys= False, indent = 2))


    def on_grd_keypress(self, event):
        # based on first answer here:
        # https://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
        # by user Sinan Çetinkaya
        """
        Handles all key events.
        """

        obj_Grid = self.grd_ExampleData

        # Ctrl+C or Ctrl+Insert
        if event.ControlDown() and event.GetKeyCode() in [67, 322]:
            self.GridCopy()

        # Ctrl+V
        elif event.ControlDown() and event.GetKeyCode() == 86:
            self.GridPaste(obj_Grid, obj_Grid.SingleSelection[0], obj_Grid.SingleSelection[1])

        # DEL
        elif event.GetKeyCode() == 127:
            self.GridClear()

        # Ctrl+A
        elif event.ControlDown() and event.GetKeyCode() == 65:
            obj_Grid.SelectAll()

        # Ctrl+X
        elif event.ControlDown() and event.GetKeyCode() == 88:
            # Call delete method
            self.GridCut()

        # Ctrl+V or Shift + Insert
        elif (event.ControlDown() and event.GetKeyCode() == 67) \
                or (event.ShiftDown() and event.GetKeyCode() == 322):
            self.GridPaste(obj_Grid, obj_Grid.SingleSelection[0], obj_Grid.SingleSelection[1])

        else:
            event.Skip()

    def GetGridSelection(self):
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_ExampleData.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_ExampleData.GetSelectionBlockBottomRight()
        lst_Selection = []
        for i in range(len(lst_TopLeftBlock)):
            # Nuber of columns:
            int_Columns = lst_BotRightBlock[i][1] - lst_TopLeftBlock[i][1] + 1 # add 1 because if just one cell/column is selected, subtracting the coordinates will be 0!
            # Nuber of rows:
            int_Rows = lst_BotRightBlock[i][0] - lst_TopLeftBlock[i][0] + 1 # add 1 because if just one cell/row is selected, subtracting the coordinates will be 0!
            # Get all cells:
            for x in range(int_Columns):
                for y in range(int_Rows):
                    new = [lst_TopLeftBlock[i][0]+y,lst_TopLeftBlock[i][1]+x]
                    if lst_Selection.count(new) == 0:
                        lst_Selection.append(new)
        return lst_Selection

    def GridCopy(self):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_ExampleData.SingleSelection[0], self.grd_ExampleData.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_ExampleData.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    def GridCut(self):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_ExampleData.SingleSelection[0], self.grd_ExampleData.SingleSelection[1]]]
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_ExampleData.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grd_ExampleData.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)
    
    def GridClear(self):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_ExampleData.SingleSelection[0], self.grd_ExampleData.SingleSelection[1]]]
        for i in range(len(lst_Selection)):
            self.grd_ExampleData.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GridPaste(self, obj_Grid, row, col):
        try:
            dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        except:
            return None
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        if int_Rows > self.grd_ExampleData.GetNumberRows():
            self.grd_ExampleData.AppendRows(int_Rows - self.grd_ExampleData.GetNumberRows())
        for i in range(int_Rows):
            for j in range(int_Columns):
                if j <= 5:
                    obj_Grid.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))

    def SingleSelection(self, event):
        event.GetEventObject().SingleSelection = (event.GetRow(), event.GetCol())

    def on_grd_rightclick(self, event):
        self.PopupMenu(GridContextMenu(self, event))
        
    def on_txt_independent(self, event):
        """
        Checks if entered character is a letter
        """
        # Get text
        str_TextControl = event.GetEventObject().GetValue()
        # Find insertion point
        int_Insertion = event.GetEventObject().GetInsertionPoint()
        # Check if string is emtpty
        if not str_TextControl == "":
            # Get new character
            if int_Insertion == len(str_TextControl):
                str_NewCharacter = str_TextControl[-1]
            else:
                str_NewCharacter = str_TextControl[int_Insertion-1:int_Insertion]
            # Check if alphanumeric
            if str_NewCharacter.isalpha() == False:
                # Reset text control
                str_Reset = str_TextControl[:int_Insertion-1] + str_TextControl[int_Insertion:]
                event.GetEventObject().ChangeValue(str_Reset)
                event.GetEventObject().SetInsertionPoint(int_Insertion-1)

    def on_toggle_independent(self, event):
        """
        Changes label of toggle button based on status and sets status
        of text control txt_Independent.
        """
        str_Independent = self.txt_Independent.GetValue()
        # Check if value appears in parameters
        lst_Parameters = []
        for line in range(self.lbx_Parameters.GetCount()):
            lst_Parameters.append(self.lbx_Parameters.GetString(line))
        if str_Independent in lst_Parameters:
            self.txt_Independent.Clear()
            mb.info(self, "Duplicate parameter name")
            event.GetEventObject().SetValue(True)
            event.GetEventObject().SetLabel("Edit")
        else:
            self.txt_Independent.Enable(event.GetEventObject().GetValue())
            if event.GetEventObject().GetValue() == False:
                event.GetEventObject().SetLabel("Edit")
            else:
                event.GetEventObject().SetLabel("Save")
            self.FunctionLinter(event = None)
    
    def on_txt_parameter(self, event):
        """
        Checks if entered character is in list of permissible characters (alphanumeric only)
        """
        # Get text
        str_TextControl = event.GetEventObject().GetValue()
        # Find insertion point
        int_Insertion = event.GetEventObject().GetInsertionPoint()
        # Check if string is emtpty
        if not str_TextControl == "":
            # Get new character
            if int_Insertion == len(str_TextControl):
                str_NewCharacter = str_TextControl[-1]
            else:
                str_NewCharacter = str_TextControl[int_Insertion-1:int_Insertion]
            # Check if alphanumeric
            if str_NewCharacter.isalnum() == False:
                # Reset text control
                str_Reset = str_TextControl[:int_Insertion-1] + str_TextControl[int_Insertion:]
                event.GetEventObject().ChangeValue(str_Reset)
                event.GetEventObject().SetInsertionPoint(int_Insertion-1)

    def on_enter_parameter(self, event):
        self.on_btn_addparameter(event)

    def on_paste_parameter(self, event):
        self.TruncatePastedText(textctrl = event.GetEventObject(),
                                length = 10,
                                alphanumonly = True)

    def on_btn_addparameter(self, event):
        """
        Event handler. Adds parameter from text ctrl to list box and
        clears list box again.
        """
        # Get Parameter
        str_Par = self.txt_Parameter.GetValue()
        if len(str_Par) == 0:
            return None

        # Check it's not identical to independent variable
        if str_Par == self.txt_Independent.GetValue():
            mb.info(self, "Parameter is identical to independent variable")
            return None

        # Check for duplication
        lst_Parameters = []
        for line in range(self.lbx_Parameters.GetCount()):
            lst_Parameters.append(self.lbx_Parameters.GetString(line))
        if str_Par in lst_Parameters:
            self.txt_Parameter.Clear()
            mb.info(self, "Duplicate parameter name")
            return None

        # Check if parameter is not empty string. If so, add to list and clear
        # text control.
        if str_Par not in self.lst_ParameterBlacklist:
            self.lbx_Parameters.Insert(str_Par, self.lbx_Parameters.GetCount())
            #self.lbc_ParameterValues.InsertItem(self.lbx_Parameters.GetCount(), str_Par)
            self.dic_ParamColours[str_Par] = self.TM_RGB_List[self.lbx_Parameters.GetCount()-1]
        else:
            mb.info(self, "Forbidden parameter name")
        self.txt_Parameter.Clear()
        self.UpdateParameters()
        self.AssignParameterColours()


        # Update text formatting in txt_DefineFunction
        self.FunctionLinter(event = None)

    def UpdateParameters(self):
        pars = []
        for par in self.lbx_Parameters.GetCount():
            pars.append(self.lbx_Parameters.GetString(par))
        self.rule_set["DataFitModel"]["Parameters"] = pars

    def OpenParameterContextMenu(self, event):
        self.PopupMenu(ParameterContextMenu(self, event))

    def OnKeyPressTxtDefineFunction(self, event):
        
        self.LastKey = event.GetUnicodeKey()
        event.Skip()

    def OnLeftDownTxtDefineFunction(self, event):
        self.PreviousInsertion = self.txt_DefineFunction.GetInsertionPoint()
        event.Skip()

    def OnPasteTxtDefineFunction(self, event):
        # get clipboard contents:
        self.TruncatePastedText(textctrl = event.GetEventObject(),
                                length = 200)

    def TruncatePastedText(self, textctrl, length, alphanumonly = False):
        obj_Text = wx.TextDataObject()
        if wx.TheClipboard.Open():
            bol_Success = wx.TheClipboard.GetData(obj_Text)
            wx.TheClipboard.Close()
        if bol_Success:
            str_Function = obj_Text.GetText()
            # only keep permitted characters:
            lst_Allowed = ["(",")","/","+","-","*","."]
            str_Checked = ""
            for char in range(len(str_Function)):
                if str_Function[char].isalnum() == True: 
                    str_Checked += str_Function[char]
                elif alphanumonly == False and str_Function[char] in lst_Allowed:
                    if str_Function[char] == ")" and str_Function[char-1] == "(":
                        pass
                    elif str_Function[char] == "." and str_Function[char-1].isalpha() == True:
                        pass
                    else:
                        str_Checked += str_Function[char]
                # We're not allowing more than x characters per function
                if len(str_Checked) == length:
                    break
            if len(str_Checked) > 0:
                textctrl.ChangeValue(str_Checked)
                self.PreviousDefinition = ""
                self.FunctionLinter(event = None)

    def FunctionLinter(self, event):
        """
        Checks if entered character is in list of permissible charac(alphanumeric and maths only)
        """
        bol_Backspace = False
        bol_Delete = False
        if not event == None:   
            #print("InsertionPoint: "+ str(event.GetEventObject().GetInsertionPoint()))
            #print("KeyPress:" + str(self.LastKey))
            if self.LastKey == 8:
                bol_Backspace = True
            elif self.LastKey == 127:
                bol_Delete = True

        lst_AllOperators = ["(",")","/","*","exp","+","-","log","ln","sqrt"]
        lst_Parameters = list(self.dic_ParamColours.keys())

        # Freeze application and unbind event from txt_DefineFunction to avoid
        # infinite recursion
        self.Freeze()
        self.txt_DefineFunction.Unbind(wx.EVT_TEXT)

        # Get text
        str_TextControl = self.txt_DefineFunction.GetValue()
        # Check if string is emtpty
        if str_TextControl == "":
            self.Thaw()
            return None
        
        # Get independent variable:
        str_Independent = self.txt_Independent.GetValue()

        # If function is called from txt_DefineFunction, find insertionpoint and newchar:
        bol_NewCharVeto = False
        if not event == None:
            bol_Doubling = False
            int_Insertion = self.txt_DefineFunction.GetInsertionPoint()
            str_BeforeInsertion = str_TextControl[:int_Insertion]
            # Get new character
            if int_Insertion == len(str_TextControl):
                newchar = str_TextControl[-1]
            else:
                newchar = str_TextControl[int_Insertion-1:int_Insertion]
            # remove newchar if not allowed:
            if newchar.isalnum() == False and not newchar in ["(",")","+","-","/","*"," "]:
                # Reset text control
                str_TextControl = str_TextControl[:int_Insertion-1] + str_TextControl[int_Insertion:]
                bol_NewCharVeto = True
            # no double operators except * and no double blank spaces
            if newchar in ["+","-","/"," "] and (newchar == str_TextControl[int_Insertion-2:int_Insertion-1]
                or newchar == str_TextControl[int_Insertion:int_Insertion+1]):
                    bol_Doubling = True
                    bol_NewCharVeto = True
        else:
            int_Insertion = -1

        # Extract function as list of parameters and operators:
        lst_Function = fdfn.FunctionToList(funcstring = str_TextControl)
        lst_Format = fdfn.Formatting(funclist = lst_Function,
                                     independent = str_Independent,
                                     operators = lst_AllOperators,
                                     parameters= lst_Parameters)
        
        # If an operator was doubled, it was not inserted and the insertion
        # point not advanced.
        if not event == None:
            if bol_Doubling == True: # or bol_NewCharVeto == True:
                int_Insertion -= 1

        int_FuncLen = len(lst_Function)

        # Formatting
        lst_NoSpaceAfter = ["(","/","*","exp","log","ln","sqrt"," "]
        lst_NoSpaceBefore = [")","/","*"," "]
        
        self.txt_DefineFunction.Clear()
        for elem in range(int_FuncLen):
            if not lst_Function[elem] == " ":
                # Set formatting:
                if lst_Format[elem] == "parameter":
                    TextColour = self.dic_ParamColours[lst_Function[elem]]
                    BackColour = wx.WHITE
                    Font = wx.Font(wx.FontInfo())
                elif lst_Format[elem] == "default" or lst_Function[elem].isnumeric() == True:
                    TextColour = wx.BLACK
                    BackColour = wx.WHITE
                    Font = wx.Font(wx.FontInfo())
                elif lst_Format[elem] == "independent":
                    TextColour = wx.BLACK
                    BackColour = wx.WHITE
                    Font = wx.Font(wx.FontInfo().Bold())
                elif lst_Format[elem] == "underlined":
                    TextColour = wx.BLACK
                    BackColour = wx.WHITE
                    Font = wx.Font(wx.FontInfo().Underlined())
                self.txt_DefineFunction.SetDefaultStyle(wx.TextAttr(colText = TextColour,
                                                                    colBack = BackColour,
                                                                    font = Font))
                # Spacing and appending
                if elem < int_FuncLen - 1:
                    if lst_Function[elem+1] in lst_NoSpaceBefore:
                        self.txt_DefineFunction.AppendText(lst_Function[elem])
                    elif not lst_Function[elem] in lst_NoSpaceAfter:
                        self.txt_DefineFunction.AppendText(lst_Function[elem])
                        self.txt_DefineFunction.SetDefaultStyle(wx.TextAttr(colText = wx.BLACK,
                                                                    colBack = wx.WHITE,
                                                                    font = wx.Font(wx.FontInfo())))
                        self.txt_DefineFunction.AppendText(" ")
                    else:
                        self.txt_DefineFunction.AppendText(lst_Function[elem])
                else:
                    self.txt_DefineFunction.AppendText(lst_Function[elem])
            elif lst_Function[elem] == " " and elem == int_FuncLen-1:
                self.txt_DefineFunction.AppendText(lst_Function[elem])

        # Set Insertion Point
        CurrentDefinition = self.txt_DefineFunction.GetValue()
        int_NewInsertion = -1

        if not self.PreviousDefinition == "":
            # Find which string is shorter
            if len(self.PreviousDefinition) > len(CurrentDefinition):
                ranger = len(self.PreviousDefinition)
            else:
               ranger = len(CurrentDefinition)
            i = -1
            for i in range(ranger):
                a = i*(-1)
                try:
                    if not CurrentDefinition[a] == self.PreviousDefinition[a]:
                        int_NewInsertion = ranger + a + 1
                        break
                except:
                    break

        if bol_Backspace == True or bol_Delete == True:
            int_NewInsertion -= 1

        if bol_NewCharVeto == False:
            self.txt_DefineFunction.SetInsertionPoint(int_Insertion)
            self.PreviousInsertion = int_Insertion
        else:
            self.txt_DefineFunction.SetInsertionPoint(self.PreviousInsertion)

        self.PreviousDefinition = CurrentDefinition
        self.txt_DefineFunction.Bind(wx.EVT_TEXT, self.FunctionLinter)
        self.Thaw()        

    def AssignParameterColours(self):
        self.dic_ParamColours = {}
        for parameter in range(self.lbx_Parameters.GetCount()):
            str_Par = self.lbx_Parameters.GetString(parameter)
            self.dic_ParamColours[str_Par] = self.TM_RGB_List[parameter]

    def OnChkXDataLogScale(self, event):
        """
        Event handler: Changes scale of x axis of example data plot
        """
        self.plt_ExamplePlot.XLogscale = event.GetEventObject().GetValue()
        self.plt_ExamplePlot.Draw()

    def OnBtnExamplePlot(self, event):
        """
        Checks example data, hands it to plot, draws plot.
        """
        lst_XData = []
        lst_YData = []
        for row in range(self.grd_ExampleData.GetNumberRows()):
            try:
                x = float(self.grd_ExampleData.GetCellValue(row, 0))
                y = float(self.grd_ExampleData.GetCellValue(row, 1))
                lst_XData.append(x)
                lst_YData.append(y)
            except:
                None
        if len(lst_XData) > 0:
            self.plt_ExamplePlot.XData = lst_XData
            self.plt_ExamplePlot.YData = lst_YData
            self.plt_ExamplePlot.Draw()

    def OnBtnTestFunction(self, event):
        """
        Tests user specified equation
        """
        # Test whether there is data to use:
        if not len(self.plt_ExamplePlot.XData) > 0:
            mb.info(self, "There is no example data to test the function with.")
            return None
        # Retrieve parameters
        lst_Parameters = list(self.dic_ParamColours.keys())
        if len(lst_Parameters) == 0:
            mb.info(self, "No parameters were defined")
            return None
        else:
            self.lbc_ParameterValues.DeleteAllItems()
            for par in lst_Parameters:
                self.lbc_ParameterValues.InsertItem(self.lbc_ParameterValues.GetItemCount(),
                                                    par)
        #    print("We have parameters")

        # Retrieve function
        str_Function = self.txt_DefineFunction.GetValue()
        if str_Function == "":
            mb.info(self, "A function has not been defined.")
            return None
        #else:
        #    print("We have a function: " + str_Function)
        
        # Get independent variable:
        str_Independent = self.txt_Independent.GetValue()
        if str_Independent == "":
            mb.info(self, "The Independent variable has not been defined")
            return None
        if fdfn.VerifyFunction(str_Function, lst_Parameters, str_Independent) == False:
            return None
        mb.info(self, "The function was succesfully verified")

        # Ensure any operators/functions in numpy
        # will work properly (e.g. exp, log, sin...)
        str_Function = fdfn.AddNumpyToFunction(str_Function)
        
        # Calculate values for parameters with example data
        lst_ParValues = fdfn.CalcParsValues(xdata = self.plt_ExamplePlot.XData,
                                            ydata = self.plt_ExamplePlot.YData,
                                            independent = str_Independent,
                                            funcpars = lst_Parameters,
                                            function = str_Function)

        # Add Parameter Values to listctrl lbc_ParameterValues
        for val in range(len(lst_ParValues)):
            self.lbc_ParameterValues.SetItem(val, 1, str(round(lst_ParValues[val],3)))

        #print("We could calculate values for parameters")
        # Perform curve fit with example data
        lst_YFit = fdfn.CalculateCurve(xdata = self.plt_ExamplePlot.XData,
                                       parvalues = lst_ParValues,
                                       independent = str_Independent,
                                       funcpars = lst_Parameters,
                                       function = str_Function)
        #print("We could fit the data with the provided function and parameter values.")
        # Add fit to plot
        self.plt_ExamplePlot.YFit = lst_YFit
        self.plt_ExamplePlot.Draw()




    def CheckRules(self):

        return True

    def Ruleset(self, str_Field):
        """
        Returns the specified value from the dataframe self.rule_set.
        """
        return self.rule_set[str_Field]

    def CheckColumns(self):
        """
        Checks whether the minimum required columns are assigned
        """
        #if (self.rule_set["TransferFileColumns"].loc["Destination Plate Name"] == None and 
        #    self.rule_set["TransferFileColumns"].loc["Destination Plate Barcode"] == None):
        #    mb.info(self, "Either 'Destination Plate Name' or 'Destination Plate Barcode' need to have a column assigned")
        #    return False
        #if self.rule_set["TransferFileColumns"].loc["Destination Well"] == None:
        #    mb.info(self, "No 'Destination Well' column assigned.")
        #    return False
        #if self.rule_set["TransferFileColumns"].loc["Destination Concentration"] == None:
        #    mb.info(self, "Needs at least a destination concentration or source concentration + transfer volume")
        #if (self.rule_set["TransferFileColumns"].loc["Destination Concentration"] == None and
        #    self.rule_set["TransferFileColumns"].loc["Source Concentration"] == None):
        #    mb.info(self, "Needs at least a destination concentration or source concentration + transfer volume")
        #    return False
        return True

    def CheckForDataFrame(self):
        """
        Checks whether rule_set exists and has been created properly.
        """
        if hasattr(self, "rule_set") == False:
            return False
        else:
            if len(self.rule_set) > 0:
                return True
            else:
                return False

    ####  #   # #     #####     ####  ###  #   # # #   #  ####
    #   # #   # #     #        #     #   # #   # # ##  # #
    ####  #   # #     ###       ###  ##### #   # # ##### #  ##
    #   # #   # #     #            # #   #  # #  # #  ## #   #
    #   #  ###  ##### #####    ####  #   #   #   # #   #  ####

    # Simplebook page saving functions ##############################################################################################################

    def fun_Dummy(self):
        return "ForwardBackward"
    
    def save_metadata(self):
        return "ForwardBackward"
    
    def save_replicates(self):
        return "ForwardBackward"
    
    def save_normalisation(self):
        return "ForwardBackward"

    def save_function(self):
        return "ForwardBackward"

def CreateBlankRuleSet():
    rule_set = {"SubtractBackground":True,
                "UseAsBackground":"Control",
                "BackgroundBackup":True,
                "ControlName":"Control",
                "NormaliseData":"True",
                "NormalisedValue":"Ratio",
                "MaxDatapoints":16,
                "ReplicatesSamePlate":True,
                "ReplicatesAcrossPlates":False,
                "ReplicateErrorCalculation":True,
                "ReplicateErrorType":"StandardDeviation",
                "DataFit":True,
                "DataFitModel":{"Name":"Custom",
                                "Equation":"ybot + (ytop - ybot)/(1 + (i/x)**h)",
                                "Parameters":["ybot","ytop","i","h"],
                                "Free":True,
                                "Constrained":False,
                                "Constraints":{"ybot":[],
                                               "ytop":[],
                                               "i":[],
                                               "h":[]
                                               }
                                }
                }

    return rule_set


class ExamplePlot(wx.Panel):
    """
    Custom class using wxPython class wx.Panel.

    Functions:

    Draw -> Draws the actual plot. Is used everytime data from a new
            sample is displayed or changes have been made
    """
    def __init__(self,parent,PanelSize):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(350/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.ax = self.figure.add_subplot()
        self.ax.set_title("Preview")

        self.XData = []
        self.YData = []
        self.XFit = []
        self.YFit = []
        self.XLogscale = False

    def Draw(self):
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        
        self.ax.scatter(self.XData, self.YData, marker="o", label="Data", color="blue")
        if len(self.YFit) > 0:
            self.ax.plot(self.XData, self.YFit, label="Fit", color="red")
            
        if self.XLogscale == True:
            self.ax.set_xscale("log")

        self.ax.legend()

        self.canvas.draw()


class GridContextMenu(wx.Menu):
    def __init__(self, parent, rightclick):
        super(GridContextMenu, self).__init__()
        """
        Context menu to cut, copy, paste, clear and fill down from capillaries grid.
        """
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        row = rightclick.GetRow()
        col = rightclick.GetCol()

        self.parent = parent
        self.grid = rightclick.GetEventObject()

        self.mi_Cut = wx.MenuItem(self, wx.ID_ANY, u"Cut", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Cut.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Cut.ico"))
        self.Append(self.mi_Cut)
        self.Bind(wx.EVT_MENU, lambda event: self.Cut(event,  row, col), self.mi_Cut)

        self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Copy.ico"))
        self.Append(self.mi_Copy)
        self.Bind(wx.EVT_MENU, lambda event: self.Copy(event,  row, col), self.mi_Copy)

        self.mi_Paste = wx.MenuItem(self, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Paste.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Paste.ico"))
        self.Append(self.mi_Paste)
        self.Bind(wx.EVT_MENU, lambda event: self.Paste(event,  row, col), self.mi_Paste)

        self.mi_Clear = wx.MenuItem(self, wx.ID_ANY, u"Clear", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Clear.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Clear.ico"))
        self.Append(self.mi_Clear)
        self.Bind(wx.EVT_MENU, lambda event: self.Clear(event,  row, col), self.mi_Clear)

        self.AppendSeparator()

        self.mi_FillDown = wx.MenuItem(self, wx.ID_ANY, u"Fill down", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_FillDown.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\FillDown.ico"))
        self.Append(self.mi_FillDown)
        self.Bind(wx.EVT_MENU, lambda event: self.FillDown(event, row, col), self.mi_FillDown)


    def FillDown(self, event, row, col):
        filler = self.grid.GetCellValue(row,col)
        for i in range(row,self.grid.GetNumberRows(),1):
            self.grid.SetCellValue(i, col, filler)

    def Copy(self, event, row, col):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)

    def Cut(self, event, row, col):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)

    def Paste(self, event, row, col):
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if j <= 5:
                    self.grid.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))

    def Clear(self, event, row, col):
        self.grid.SetCellValue(row, col, "")
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GetGridSelection(self):
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grid.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grid.GetSelectionBlockBottomRight()
        lst_Selection = []
        for i in range(len(lst_TopLeftBlock)):
            # Nuber of columns:
            int_Columns = lst_BotRightBlock[i][1] - lst_TopLeftBlock[i][1] + 1 # add 1 because if just one cell/column is selected, subtracting the coordinates will be 0!
            # Nuber of rows:
            int_Rows = lst_BotRightBlock[i][0] - lst_TopLeftBlock[i][0] + 1 # add 1 because if just one cell/row is selected, subtracting the coordinates will be 0!
            # Get all cells:
            for x in range(int_Columns):
                for y in range(int_Rows):
                    new = [lst_TopLeftBlock[i][0]+y,lst_TopLeftBlock[i][1]+x]
                    if lst_Selection.count(new) == 0:
                        lst_Selection.append(new)
        return lst_Selection

class ParameterContextMenu(wx.Menu):
    def __init__(self, parent, rightclick):
        super(ParameterContextMenu, self).__init__()
        """
        Context menu to cut, copy, paste, clear and fill down from capillaries grid.
        """
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.listbox = rightclick.GetEventObject()
        self.parent = parent
        row = self.listbox.HitTest(rightclick.GetPosition())
        

        self.mi_Delete = wx.MenuItem(self, wx.ID_ANY, u"Delete", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_Delete.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Clear.ico"))
        self.Append(self.mi_Delete)
        self.Bind(wx.EVT_MENU, lambda event: self.Delete(event,  row), self.mi_Delete)

        self.mi_Rename = wx.MenuItem(self, wx.ID_ANY, u"Rename", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_Rename.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Clear.ico"))
        self.Append(self.mi_Rename)
        self.Bind(wx.EVT_MENU, lambda event: self.Rename(event,  row), self.mi_Rename)

    def Delete(self, event, row):
        """
        Deletes clicked on parameter: Writes all parameters except clicked
        on into new list, clears listbox, inserts new lists, reassings
        colours and re-linters function.
        """
        # CBA right now to look up how to do it "properly", it's nearly 23h.
        lst_Reset = []
        for line in range(self.listbox.GetCount()):
            if not line == row:
                lst_Reset.append(self.listbox.GetString(line))
        self.listbox.Clear()
        if len(lst_Reset) > 0:
            self.listbox.InsertItems(lst_Reset,0)
        self.parent.AssignParameterColours()
        self.parent.UpdateParameters()
        self.parent.FunctionLinter(event = None)
        
    def Rename(self, event, row):
        """
        Handles renaming of parameters. Calls dialog and, if True gets returned,
        renames parameter at specified row before destroying the dialog.
        """
        dlg_TheRenamer = dlg_Rename(parent = self.parent,
                                    parameter = self.listbox.GetString(row))
        bol_Rename = dlg_TheRenamer.ShowModal()
        if bol_Rename == True:
            str_Rename = dlg_TheRenamer.txt_Parameter.GetValue()
            self.listbox.SetString(row,str_Rename)
            self.parent.AssignParameterColours()
            self.parent.UpdateParameters()
            self.parent.FunctionLinter(event = None)
        dlg_TheRenamer.Destroy()
        