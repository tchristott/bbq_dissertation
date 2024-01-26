# Import my own libraries
import lib_platefunctions as pf
import lib_datafunctions as df
import lib_fittingfunctions as ff
import lib_customplots as cp
import lib_colourscheme as cs
import lib_messageboxes as msg
import lib_tabs as tab
import lib_tooltip as tt
from lib_custombuttons import CustomBitmapButton, IconTabButton

# Import libraries for GUI
import wx
import wx.xrc

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backend_bases import MouseButton
from matplotlib.figure import Figure

# Import other libraries
import os
import pandas as pd
import numpy as np
import threading
from datetime import datetime
import threading
import json as js

##############################################################################################
##                                                                                          ##
##    #####   ##  ##  ##               ####   ##  ##  ##      ##  ##   #####  ##   #####    ##
##    ##  ##  ### ##  ##              ##  ##  ### ##  ##      ##  ##  ##      ##  ##        ##
##    #####   ## ###  ##              ######  ## ###  ##       ####    ####   ##   ####     ##
##    ##      ##  ##  ##              ##  ##  ##  ##  ##        ##        ##  ##      ##    ##
##    ##      ##  ##  ######  ######  ##  ##  ##  ##  ######    ##    #####   ##  #####     ##
##                                                                                          ##
##############################################################################################

class pnl_Workflow (wx.Panel):

    def __init__(self, parent, assay):
        wx.Panel.__init__ (self, parent.sbk_WorkArea,
                           id = wx.ID_ANY,
                           pos = wx.DefaultPosition,
                           size = wx.Size(1000,750),
                           style = wx.TAB_TRAVERSAL,
                           name = "pnl_Project")

        self.SetBackgroundColour(cs.BgUltraLight)
        clr_Tabs = cs.BgUltraLight
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.parent = parent

        # Initialise instance wide variables with default values
        self.assay = assay
        self.title = self.assay["Meta"]["DisplayTitle"]
        self.Index = None
        self.int_Samples = np.nan
        self.get_details = {} # dictionary with functions to retrieve detail values
        self.set_details = {} # dictionary with functions to assign detaul values
        self.wdg_details = {} # dictionary with widgets of details
        self.default_details = self.assay["DefaultDetails"].copy()
        self.details = self.default_details.copy()
        self.details["Version"] = self.parent.version["build"]
        if self.assay["Database"]["UseDB"] == True:
            self.db_columnnames = {}
            for table in self.assay["Database"]["DBTables"]:
                colnames = self.assay["Database"]["DBTables"][table]["ColumnNames"]
                self.db_columnnames[table] = pd.DataFrame(data = colnames)
        if "RawDataRules" in self.assay.keys():
            self.rawdata_rules = self.assay["RawDataRules"].copy()
        if "TransferRules" in self.assay.keys():
            self.transfer_rules = self.assay["TransferRules"].copy()

        self.paths = {}
        self.paths["SaveFile"] = ""
        self.paths["Data"] = ""
        self.paths["TransferPath"] = ""

        self.dfr_Upload = pd.DataFrame()
        self.verified = False
        self.uploaded = False

        self.bol_AssayDetailsCompleted = False
        self.bol_AssayDetailsChanged = False
        self.bol_LayoutDefined = False
        self.bol_TransferLoaded = False
        self.bol_DataFilesAssigned = False
        self.bol_DataFilesUpdated = False
        self.bol_DataAnalysed = False
        self.bol_ReviewsDrawn = False
        self.bol_ResultsDrawn = False
        self.bol_ELNPlotsDrawn = False
        self.bol_ExportPopulated = False
        self.bol_PreviouslySaved = False
        self.bol_GlobalLayout = True
        self.bol_PlateID = False
        self.bol_PlateMapPopulated = False

        self.dfr_Layout = pd.DataFrame()

        self.str_NewConc = None

        self.szr_Main = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Tabs = wx.BoxSizer(wx.VERTICAL)
        # Button bar for saving, etc
        self.ButtonBar = tab.ButtonBar(self)
        self.szr_Tabs.Add(self.ButtonBar,0,wx.EXPAND,0)
        
        self.tabs_Analysis = tab.AssayStepsNotebook(self, size = wx.Size(1000,750))

         ##   ###  ###  ##  #   #    ###  #### #####  ##  # #     ###
        #  # #    #    #  # #   #    #  # #      #   #  # # #    #
        ####  ##   ##  ####  # #     #  # ###    #   #### # #     ##
        #  #    #    # #  #   #      #  # #      #   #  # # #       #
        #  # ###  ###  #  #   #      ###  ####   #   #  # # #### ###  ###################

        self.tab_Details = tab.AssayDetails_Flex(notebook = self.tabs_Analysis.sbk_Notebook,
                                                 workflow = self,
                                                 columns = self.assay["Tabs"]["Details"])
        self.tabs_Analysis.AddPage(self.tab_Details, u"Assay Details", True)

        ##### ###   ##  #  #  ### #### #### ###    # ###   ##  #####  ##
          #   #  # #  # ## # #    #    #    #  #   # #  # #  #   #   #  #
          #   ###  #### # ##  ##  ###  ###  ###   #  #  # ####   #   ####
          #   #  # #  # #  #    # #    #    #  # #   #  # #  #   #   #  #
          #   #  # #  # #  # ###  #    #### #  # #   ###  #  #   #   #  # ###############

        self.tab_Files = tab.FileSelection(self.tabs_Analysis.sbk_Notebook,
                                           tabname=self,
                                           whattopick=self.assay["DefaultDetails"]["FilePicker"],
                                           extension=self.assay["DefaultDetails"]["DataFileExtension"],
                                           normalise=True,
                                           layouts=False)
        self.tabs_Analysis.AddPage(self.tab_Files, u"Transfer and Data Files", True)

        ###  #### #   # # #### #       #    ###  #     ##  ##### ####  ###
        #  # #    #   # # #    #       #    #  # #    #  #   #   #    #
        ###  ###  #   # # ###  #   #   #    ###  #    ####   #   ###   ##
        #  # #     # #  # #     # # # #     #    #    #  #   #   #       #
        #  # ####   #   # ####   # # #      #    #### #  #   #   #### ###  ##############

        self.tab_Review = tab.Review(self.tabs_Analysis.sbk_Notebook,
                                     tabname = self,
                                     assaycategory = self.details["Shorthand"],
                                     plots = ["Heat Map"],
                                     sidebar = [""])
        self.tabs_Analysis.AddPage(self.tab_Review, u"Review Plates", False)

        ###  ####  ### #  # #  #####  ###
        #  # #    #    #  # #    #   #
        ###  ###   ##  #  # #    #    ##
        #  # #       # #  # #    #      #
        #  # #### ###   ##  #### #   ###  ###############################################

        # Start Building
        self.tab_Results = wx.Panel(self.tabs_Analysis.sbk_Notebook,
                                    style = wx.TAB_TRAVERSAL)
        self.tab_Results.SetBackgroundColour(clr_Tabs)
        self.szr_Results = wx.BoxSizer(wx.VERTICAL)

        self.bSizer12 = wx.BoxSizer(wx.HORIZONTAL)

        # Sample List
        self.szr_SampleList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SelectSample = wx.StaticText(self.tab_Results, label = u"Select a sample")
        self.lbl_SelectSample.Wrap(-1)
        self.szr_SampleList.Add(self.lbl_SelectSample, 0, wx.ALL, 5)
        # Make lbc_Samples dynamic (column title, column width, sortable by this col)
        self.lbc_Samples = tab.lbc_constructor(parent = self.tab_Results,
                                               columns = self.assay["Tabs"]["Results"]["SampleList"],
                                               background = clr_TextBoxes)
        self.szr_SampleList.Add(self.lbc_Samples, 1, wx.ALL|wx.EXPAND, 5)
        # Button to export results table
        self.btn_ExportResultsTable = CustomBitmapButton(self.tab_Results,
                                                         name = u"ExportToFile",
                                                         index = 5,
                                                         size = (104,25))
        self.szr_SampleList.Add(self.btn_ExportResultsTable, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.bSizer12.Add(self.szr_SampleList, 0, wx.EXPAND, 5)

        # Sizer for plot and plot export buttons
        self.szr_SimpleBook = wx.BoxSizer(wx.VERTICAL)
        self.szr_SimpleBookTabs = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_IndividualPlot = IconTabButton(self.tab_Results, u"Individual Plot", 0, self.AssayPath)
        self.btn_IndividualPlot.IsCurrent(True)
        self.szr_SimpleBookTabs.Add(self.btn_IndividualPlot, 0, wx.ALL,0)
        self.szr_SimpleBookTabs.Add((5,0), 0, wx.ALL,0)
        self.btn_SummaryPlot = IconTabButton(self.tab_Results, u"Summary Plot", 1, self.AssayPath)
        self.btn_SummaryPlot.IsEnabled(True)
        self.szr_SimpleBookTabs.Add(self.btn_SummaryPlot, 0, wx.ALL, 0)
        self.dic_PlotTabButtons = {0:self.btn_IndividualPlot,1:self.btn_SummaryPlot}
        self.szr_SimpleBook.Add(self.szr_SimpleBookTabs, 0, wx.ALL, 0)
        self.sbk_ResultPlots = wx.Simplebook(self.tab_Results, size = wx.Size(900,550))
        self.btn_IndividualPlot.Notebook = self.sbk_ResultPlots
        self.btn_IndividualPlot.Group = self.dic_PlotTabButtons
        self.btn_SummaryPlot.Notebook = self.sbk_ResultPlots
        self.btn_SummaryPlot.Group = self.dic_PlotTabButtons

        # First page in simplebook: Resultsplot =========================================
        self.pnl_IndividualPlot = wx.Panel(self.sbk_ResultPlots, size = wx.Size(900,550),
                                           style = wx.TAB_TRAVERSAL)
        self.pnl_IndividualPlot.SetBackgroundColour(clr_Tabs)
        self.szr_Plot = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_PlotActual = wx.BoxSizer(wx.VERTICAL)
        self.plt_DoseResponse = cp.CurvePlotPanel(self.pnl_IndividualPlot, (600,450), self)
        self.szr_PlotActual.Add(self.plt_DoseResponse, 0, wx.ALL, 5)
        self.szr_ExportPlotImage = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_FigToClipboard = CustomBitmapButton(self.pnl_IndividualPlot,
                                                     name = u"Clipboard",
                                                     index = 0,
                                                     size = (130,25))
        self.szr_ExportPlotImage.Add(self.btn_FigToClipboard, 0, wx.ALL, 5)
        self.btn_SaveFig = CustomBitmapButton(self.pnl_IndividualPlot,
                                              name = u"ExportToFile",
                                              index = 0,
                                              size = (104,25))
        self.szr_ExportPlotImage.Add(self.btn_SaveFig, 0, wx.ALL, 5)
        self.btn_SaveAll = CustomBitmapButton(self.pnl_IndividualPlot,
                                              name = u"ExportAll",
                                              index = 0,
                                              size = (100,25))
        self.szr_ExportPlotImage.Add(self.btn_SaveAll, 0, wx.ALL, 5)
        self.szr_PlotActual.Add(self.szr_ExportPlotImage, 0, wx.ALL,5)
        self.szr_Plot.Add(self.szr_PlotActual, 0, wx.ALL)
        # Sizer beside plot
        self.szr_PlotDetails = wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_Res_Display = wx.BoxSizer(wx.VERTICAL)
        self.szr_Res_Display.Add((0, 30), 1, wx.EXPAND, 5)
        self.lbl_Display = wx.StaticText(self.pnl_IndividualPlot, label = u"Show")
        self.lbl_Display.Wrap(-1)
        self.szr_Res_Display.Add(self.lbl_Display, 0, wx.ALL, 5)
        self.rad_Res_NormFree = wx.RadioButton(self.pnl_IndividualPlot,
                                               label = u"Normalised data (free fit)",
                                               style = wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_NormFree, 0, wx.ALL, 5)
        self.rad_Res_NormConst = wx.RadioButton(self.pnl_IndividualPlot, 
                                                label = u"Normalised data (constrained fit)",
                                                style = wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_NormConst, 0, wx.ALL, 5)
        self.rad_Res_Raw = wx.RadioButton(self.pnl_IndividualPlot,
                                          label = u"Raw signal",
                                          style = wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_Raw, 0, wx.ALL, 5)
        self.chk_Confidence = wx.CheckBox(self.pnl_IndividualPlot, 
                                          label = u"Show confidence interval")
        self.szr_Res_Display.Add(self.chk_Confidence, 0, wx.ALL, 5)
        self.chk_OutsideWarning = wx.CheckBox(self.pnl_IndividualPlot, 
                                              label = u"Show warning if points outside boundaries")
        self.chk_OutsideWarning.SetValue(True)
        self.szr_Res_Display.Add(self.chk_OutsideWarning, 0, wx.ALL, 5)
        self.m_staticline101 = wx.StaticLine(self.pnl_IndividualPlot,
                                             style = wx.LI_HORIZONTAL)
        self.szr_Res_Display.Add(self.m_staticline101, 0, wx.EXPAND|wx.ALL, 5)
        self.szr_PlotDetails.Add(self.szr_Res_Display, 0, wx.EXPAND, 5)
        # Details (fit plot? Parameters?)
        self.szr_Details = wx.BoxSizer(wx.VERTICAL)
        self.szr_Fit = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_Fit = wx.CheckBox(self.pnl_IndividualPlot, label= u"Fit this data")
        self.szr_Fit.Add(self.chk_Fit,0,wx.ALL,0)
        self.btn_FitToolTip = CustomBitmapButton(self.pnl_IndividualPlot,
                                                 name = u"InfoUltraLight",
                                                 index = 0,
                                                 size = (15,15),
                                                 tooltip=u"How is the curve fit calculated?")
        self.btn_FitToolTip.ImagePath = os.path.join(self.parent.str_OtherPath,
                                                     "SigmoidalDoseResponseToolTip.png")
        self.szr_Fit.Add(self.btn_FitToolTip,0,wx.ALL,0)
        self.szr_Details.Add(self.szr_Fit, 0, wx.ALL, 5)
        self.szr_Parameters = wx.FlexGridSizer(6, 2, 0, 0)
        # Parameters
        self.lbl_ICLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"IC50:")
        self.lbl_ICLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_ICLabel, 0, wx.ALL, 5)
        self.lbl_IC = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_IC.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_IC, 0, wx.ALL, 5)
        # Slope
        self.lbl_SlopeLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"Slope:")
        self.lbl_SlopeLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_SlopeLabel, 0, wx.ALL, 5)
        self.lbl_Slope = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_Slope.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_Slope, 0, wx.ALL, 5)
        # Top
        self.lbl_TopLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"Top:")
        self.lbl_TopLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_TopLabel, 0, wx.ALL, 5)
        self.lbl_Top = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_Top.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_Top, 0, wx.ALL, 5)
        # Bottom
        self.lbl_BottomLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"Bottom:")
        self.lbl_BottomLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_BottomLabel, 0, wx.ALL, 5)
        self.lbl_Bottom = wx.StaticText(self.pnl_IndividualPlot,label = u"TBA")
        self.lbl_Bottom.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_Bottom, 0, wx.ALL, 5)
        # Span
        self.lbl_SpanLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"Span:")
        self.lbl_SpanLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_SpanLabel, 0, wx.ALL, 5)
        self.lbl_Span = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_Span.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_Span, 0, wx.ALL, 5)
        # RSquare
        self.lbl_RSquareLabel = wx.StaticText(self.pnl_IndividualPlot,
                                              label = u"R" + chr(178) + u":")
        self.lbl_RSquareLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_RSquareLabel, 0, wx.ALL, 5)
        self.lbl_RSquare = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_RSquare.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_RSquare, 0, wx.ALL, 5)
        self.szr_Details.Add(self.szr_Parameters, 0, wx.ALL, 5)
        # Separator line
        self.m_staticline14 = wx.StaticLine(self.pnl_IndividualPlot,
                                            style = wx.LI_HORIZONTAL)
        self.szr_Details.Add(self.m_staticline14, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_PlotDetails.Add(self.szr_Details, 0, wx.EXPAND, 5)
        # Sizer with buttons for copying/exporting 
        self.szr_CopyCurveParameters = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_CopyCurveParameters = CustomBitmapButton(self.pnl_IndividualPlot,
                                                          name = u"Clipboard",
                                                          index = 0,
                                                          size = (130,25))
        self.szr_CopyCurveParameters.Add(self.btn_CopyCurveParameters, 0, wx.ALL, 5)
        self.szr_PlotDetails.Add(self.szr_CopyCurveParameters, 1, wx.ALIGN_RIGHT, 5)
        # Finish first page
        self.szr_Plot.Add(self.szr_PlotDetails, 0, wx.EXPAND, 5)
        self.pnl_IndividualPlot.SetSizer(self.szr_Plot)
        self.pnl_IndividualPlot.Layout()
        self.szr_Plot.Fit(self.pnl_IndividualPlot)
        self.sbk_ResultPlots.AddPage(self.pnl_IndividualPlot, u"Individual Plot",True)
        self.sbk_ResultPlots.SetSelection(0)
        # ===============================================================================
        
        # Second page in sbk_ResultPlots: Multiplot =====================================
        self.pnl_MultiPlotPanel = wx.Panel(self.sbk_ResultPlots, size = wx.Size(900,550),
                                           style = wx.TAB_TRAVERSAL)
        self.pnl_MultiPlotPanel.SetBackgroundColour(clr_Tabs)
        self.szr_MultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.plt_MultiPlot = DoseMultiPlotPanel(self.pnl_MultiPlotPanel,
                                                PanelSize = (600,550),
                                                tabname = self,
                                                summaryplot=True)
        self.szr_MultiPlot.Add(self.plt_MultiPlot, 0, wx.ALL, 5)
        # Sizer beside plot
        self.szr_MultiPlotRight =  wx.BoxSizer(wx.VERTICAL)
        self.szr_MultiPlotRight.Add((0, 30), 0, wx.ALL, 0)
        # Select what to show
        self.szr_MultiPlotShow = wx.FlexGridSizer(4, 2, 0, 0)
        self.lbl_MultiPlotShow = wx.StaticText(self.pnl_MultiPlotPanel, label = u"Show")
        self.lbl_MultiPlotShow.Wrap(-1)
        self.szr_MultiPlotShow.Add(self.lbl_MultiPlotShow, 0, wx.ALL, 5)
        self.szr_MultiPlotShow.Add((-1,-1), 0, wx.ALL, 5)
        self.rad_MultiPlotNorm = wx.RadioButton(self.pnl_MultiPlotPanel,
                                                label = u"Normalised data",
                                                style = wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotNorm, 0, wx.ALL, 5)
        self.chk_ErrorBars = wx.CheckBox(self.pnl_MultiPlotPanel, label = u"Error bars")
        self.szr_MultiPlotShow.Add(self.chk_ErrorBars, 0, wx.ALL, 5)
        self.rad_MultiPlotRaw = wx.RadioButton(self.pnl_MultiPlotPanel,
                                               label = u"Raw signal",
                                               style = wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotRaw, 0, wx.ALL, 5)
        self.chk_ExcludedPoints = wx.CheckBox(self.pnl_MultiPlotPanel, 
                                              label = u"Excluded points")
        self.szr_MultiPlotShow.Add(self.chk_ExcludedPoints, 0, wx.ALL, 5)
        self.szr_MultiPlotShow.Add((-1,-1), 0, wx.ALL, 5)
        self.chk_PreviewPlot = wx.CheckBox(self.pnl_MultiPlotPanel,
                                           label = u"Preview selected sample")
        self.chk_PreviewPlot.SetValue(True) 
        self.szr_MultiPlotShow.Add(self.chk_PreviewPlot, 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_MultiPlotShow, 0, wx.EXPAND, 5)
        # Separator line
        self.lin_MultiPlotShow = wx.StaticLine(self.pnl_MultiPlotPanel, 
                                               style = wx.LI_HORIZONTAL)
        self.szr_MultiPlotRight.Add(self.lin_MultiPlotShow, 0, wx.EXPAND|wx.ALL, 5)
        # FlexGridSizer
        self.szr_MultiPlotList = wx.FlexGridSizer(9, 4, 0, 0)
        self.szr_MultiPlotList.SetFlexibleDirection(wx.BOTH)
        self.szr_MultiPlotList.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)
        self.lst_ColourOptions = cs.TM_Hex_List
        self.lst_ColourBitmaps = []
        for pic in cs.TM_ColourChoiceIcons_List:
            self.lst_ColourBitmaps.append(wx.Bitmap(pic, wx.BITMAP_TYPE_ANY))
        # Column labels
        self.lbl_Column1 = wx.StaticText(self.pnl_MultiPlotPanel,
                                         label = u"Sample ID/Name")
        self.lbl_Column1.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column1, 0, wx.ALL, 3)
        self.lbl_Column2 = wx.StaticText(self.pnl_MultiPlotPanel, label = u"Colour")
        self.lbl_Column2.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column2, 0, wx.ALL, 3)
        self.lbl_Column3 = wx.StaticText(self.pnl_MultiPlotPanel, label = u" ")
        self.lbl_Column3.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column3, 0, wx.ALL, 3)
        self.lbl_Comlumn4 = wx.StaticText(self.pnl_MultiPlotPanel, label = u" ")
        self.lbl_Comlumn4.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Comlumn4, 0, wx.ALL, 3)
        # Fill up with 8 spaces for samples
        self.lst_MultiPlotLabels = []
        self.dic_MultiPlotLabels = {}
        self.lst_BitmapCombos = []
        self.dic_BitmapCombos = {}
        self.lst_AddButtons = []
        self.dic_AddButtons = {}
        self.lst_RemoveButtons = []
        self.dic_RemoveButtons = {}
        for i in range(8):
            #Label
            self.lst_MultiPlotLabels.append("self.lbl_Sample" + str(i))
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]] = wx.StaticText(
                                                                self.pnl_MultiPlotPanel,
                                                                label = u"no sample")
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]].Wrap(-1)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]].Enable(False)
            self.szr_MultiPlotList.Add(self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]],
                                       0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 3)
            # BitmapCombo
            self.lst_BitmapCombos.append("self.bmc_Sample" + str(i))
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]] = wx.adv.BitmapComboBox(
                                                                self.pnl_MultiPlotPanel,
                                                                value = u"Combo!",
                                                                size = wx.Size(100,25),
                                                                choices = self.lst_ColourOptions,
                                                                style = wx.CB_READONLY)
            for j in range(len(self.lst_ColourBitmaps)):
                self.dic_BitmapCombos[self.lst_BitmapCombos[i]].SetItemBitmap(j,self.lst_ColourBitmaps[j])
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].SetSelection(i)
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Index = i
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Enable(False)
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Bind(wx.EVT_COMBOBOX,
                                                                 self.mutliplot_select_colour)
            self.szr_MultiPlotList.Add(self.dic_BitmapCombos[self.lst_BitmapCombos[i]], 0, wx.ALL, 3)
            # "Add" button
            self.lst_AddButtons.append("self.btn_Add" + str(i))
            self.dic_AddButtons[self.lst_AddButtons[i]] = CustomBitmapButton(self.pnl_MultiPlotPanel,
                                                                             name = u"Plus",
                                                                             index = 0,
                                                                             size = (25,25))
            self.dic_AddButtons[self.lst_AddButtons[i]].Index = i
            self.dic_AddButtons[self.lst_AddButtons[i]].Bind(wx.EVT_BUTTON, self.add_graph)
            self.szr_MultiPlotList.Add(self.dic_AddButtons[self.lst_AddButtons[i]], 0, wx.ALL, 3)
            # "Remove" button
            self.lst_RemoveButtons.append("self.btn_Add" + str(i))
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]] = CustomBitmapButton(
                                                                    self.pnl_MultiPlotPanel,
                                                                    name = u"Minus",
                                                                    index = 0,
                                                                    size = (25,25))
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Index = i
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Enable(False)
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Bind(wx.EVT_BUTTON,
                                                                   self.remove_graph)
            self.szr_MultiPlotList.Add(self.dic_RemoveButtons[self.lst_RemoveButtons[i]], 0, wx.ALL, 3)
        self.szr_MultiPlotRight.Add(self.szr_MultiPlotList, 0, wx.ALL, 5)
        # Separator line
        self.lin_MultiPlotRight = wx.StaticLine(self.pnl_MultiPlotPanel,
                                                style = wx.LI_HORIZONTAL)
        self.szr_MultiPlotRight.Add(self.lin_MultiPlotRight, 0, wx.EXPAND|wx.ALL, 5)
        # Export
        self.szr_ExportMultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_Summaryplot_to_clipboard = CustomBitmapButton(self.pnl_MultiPlotPanel,
                                                             name = u"Clipboard",
                                                             index = 0,
                                                             size = (130,25))
        self.szr_ExportMultiPlot.Add(self.btn_Summaryplot_to_clipboard, 0, wx.ALL, 5)
        self.btn_Summaryplot_to_png = CustomBitmapButton(self.pnl_MultiPlotPanel,
                                                       name = u"ExportToFile",
                                                       index = 0,
                                                       size = (104,25))
        self.szr_ExportMultiPlot.Add(self.btn_Summaryplot_to_png, 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_ExportMultiPlot, 0, wx.ALL, 0)
        self.szr_MultiPlot.Add(self.szr_MultiPlotRight, 0, wx.EXPAND, 5)
        self.pnl_MultiPlotPanel.SetSizer(self.szr_MultiPlot)
        self.pnl_MultiPlotPanel.Layout()
        self.szr_MultiPlot.Fit(self.pnl_MultiPlotPanel)
        self.sbk_ResultPlots.AddPage(self.pnl_MultiPlotPanel, u"Summary Plot",True)
        self.sbk_ResultPlots.SetSelection(0)
        # ===============================================================================

        self.szr_SimpleBook.Add(self.sbk_ResultPlots, 0, wx.EXPAND, 5)        
        self.bSizer12.Add(self.szr_SimpleBook, 0, wx.ALL, 5)
        self.szr_Results.Add(self.bSizer12, 1, wx.EXPAND, 5)
        
        # Finalise
        self.tab_Results.SetSizer(self.szr_Results)
        self.tab_Results.Layout()
        self.szr_Results.Fit(self.tab_Results)
        self.tabs_Analysis.AddPage(self.tab_Results, u"Results", False)

        #### #    #  #   ###  #     ##  #####  ###
        #    #    ## #   #  # #    #  #   #   #
        ###  #    # ##   ###  #    #  #   #    ##
        #    #    #  #   #    #    #  #   #      #
        #### #### #  #   #    ####  ##    #   ###  ######################################
        
        self.tab_ELNPlots = tab.ELNPlots(self.tabs_Analysis.sbk_Notebook,
                                         tabname = self, shorthand = self.details["Shorthand"])
        self.tabs_Analysis.AddPage(self.tab_ELNPlots, u"Plots for ELN", False)

        #### #  # ###   ##  ###  #####
        #    #  # #  # #  # #  #   #
        ##    ##  ###  #  # ###    #
        #    #  # #    #  # #  #   #
        #### #  # #     ##  #  #   # ####################################################

        use_db = self.assay["Database"]["UseDB"]
        db_table = list(self.db_columnnames.keys())[0]
        db_dependencies = self.assay["Database"]["Dependencies"][db_table]
        self.lst_Headers = self.db_columnnames[db_table]["BBQ_NAME"].dropna().tolist()
        self.tab_Export = tab.ExportTable(notebook = self.tabs_Analysis.sbk_Notebook, 
                                          tabname = self,
                                          use_db = use_db,
                                          db_table = db_table,
                                          db_dependencies = db_dependencies)
        tab_label = self.assay["Database"]["DBTables"][db_table]["TabLabel"]
        self.tabs_Analysis.AddPage(self.tab_Export, tab_label, False)


        #################################################################################

        self.szr_Tabs.Add(self.tabs_Analysis, 1, wx.EXPAND|wx.ALL, 0)
        self.szr_Main.Add(self.szr_Tabs, 1, wx.EXPAND, 5)
        self.SetSizer(self.szr_Main)
        self.Layout()
        self.Centre(wx.BOTH)

        # Select first tab/index 0
        self.tabs_Analysis.SetSelection(0)

        ###  # #  # ###  # #  #  ###
        #  # # ## # #  # # ## # #  
        ###  # # ## #  # # # ## # ##
        #  # # #  # #  # # #  # #  #
        ###  # #  # ###  # #  #  ##  ####################################################

        # Highest level events:
        self.tabs_Analysis.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

        # Results Tab
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.EditSourceConcentration)
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_SELECTED, self.show_curve)
        self.lbc_Samples.Bind( wx.EVT_LIST_COL_CLICK, self.toggle_result_list_sort)
        self.btn_ExportResultsTable.Bind(wx.EVT_BUTTON, self.results_to_file)
        self.chk_Confidence.Bind(wx.EVT_CHECKBOX, self.show_confidence)
        self.chk_OutsideWarning.Bind(wx.EVT_CHECKBOX, self.toggle_outside_warning)
        self.chk_Fit.Bind(wx.EVT_CHECKBOX, self.toggle_fit)
        self.btn_FitToolTip.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.rad_Res_Raw.Bind(wx.EVT_RADIOBUTTON, self.RadRaw)
        self.rad_Res_NormConst.Bind(wx.EVT_RADIOBUTTON, self.RadNormConst)
        self.rad_Res_NormFree.Bind(wx.EVT_RADIOBUTTON, self.RadNormFree)
        self.btn_FigToClipboard.Bind(wx.EVT_BUTTON, self.plt_DoseResponse.plot_to_clipboard)
        self.btn_SaveFig.Bind(wx.EVT_BUTTON, self.plt_DoseResponse.plot_to_png)
        self.btn_SaveAll.Bind(wx.EVT_BUTTON, self.all_plots_to_png)
        self.btn_CopyCurveParameters.Bind(wx.EVT_BUTTON, self.CopyCurveParameters)
        self.rad_MultiPlotNorm.Bind(wx.EVT_RADIOBUTTON, self.MultiRadNorm)
        self.rad_MultiPlotRaw.Bind(wx.EVT_RADIOBUTTON, self.MultiRadRaw)
        self.chk_ErrorBars.Bind(wx.EVT_CHECKBOX, self.toggle_error_bars)
        self.chk_ExcludedPoints.Bind(wx.EVT_CHECKBOX, self.toggle_excluded_points)
        self.chk_PreviewPlot.Bind(wx.EVT_CHECKBOX, self.toggle_preview_plot)
        self.btn_Summaryplot_to_clipboard.Bind(wx.EVT_BUTTON, self.plt_MultiPlot.plot_to_clipboard)
        self.btn_Summaryplot_to_png.Bind(wx.EVT_BUTTON, self.plt_MultiPlot.plot_to_png)

    def __del__(self):
        pass

    ##    ##  ######  ######  ##  ##   ####   #####    #####
    ###  ###  ##        ##    ##  ##  ##  ##  ##  ##  ##
    ########  ####      ##    ######  ##  ##  ##  ##   ####
    ## ## ##  ##        ##    ##  ##  ##  ##  ##  ##      ##
    ##    ##  ######    ##    ##  ##   ####   #####   #####

    def change_tab(self, btn_Caller):
        """
        Gets called by tab buttons to see if we're allowd to change tabs.
        """
        int_OldTab = self.tabs_Analysis.GetSelection()
        int_NewTab = btn_Caller.Index
        if int_NewTab <= self.tabs_Analysis.GetPageCount(): 
            if int_OldTab == 0:
                self.save_details(bol_FromTabChange = True)
            # Assay details and files tabs are 0 and 1
            if int_NewTab > int_OldTab and int_NewTab > 1 and self.bol_DataAnalysed == False:
                msg.info_no_analysis()
                return False
            else:
                return True

    def OnTabChanged(self, event):
        """
        Event handler. Gets called when tabs in the SimpleBook change.
        Checks whether the tabs need populating.
        """
        int_NewTab = self.tabs_Analysis.GetSelection()
        if int_NewTab == 2:
            # going to review tab
            if self.bol_ReviewsDrawn == False:
                self.bol_ReviewsDrawn = self.tab_Review.populate()
        elif int_NewTab == 3:
            # going to results tab
            if self.bol_ResultsDrawn == False:
                self.populate_results_tab()
        elif int_NewTab == 4:
            # going to plots for ELN page tab
            if self.bol_ELNPlotsDrawn == False:
                self.tab_ELNPlots.populate(self.assay_data)
        elif int_NewTab == 5:
            # going to export tab
            if self.bol_ExportPopulated == False:
                self.bol_ExportPopulated = self.populate_export_tab()

    def save_file(self, event):
        self.parent.save_file(event = event, tabname = self, saveas = False)

    def save_file_as(self, event):
        self.parent.save_file(event = event, tabname = self, saveas = True)

    def populate_from_file(self, str_TempDir, details):
        """
        Gets called by main window to populate all tabs after loading a file.

        Arguments:
            str_TempDir -> string. Temporary directory
            details -> dictionary. Holds assay details
        """

        for key in details.keys():
            if pd.isna(details[key]) == True:
                details[key] = "NA"
        if details["Shorthand"] == "NDSF":
            str_WellsOrCapillaries = "Capillaries"
        else:
            str_WellsOrCapillaries = "Wells"
        # Read boolean.csv
        dfr_Boolean = pd.read_csv(str_TempDir + r"\boolean.csv", sep=",",
                                  header=0, index_col=0, engine="python")
        # Read in meta.csv. Find better name for file
        dfr_Meta = pd.read_csv(str_TempDir + r"\meta.csv", sep=",",
                               header=0, index_col=0, engine="python")
        # Ensure backwards compatibility by changing column titles (as of 1.2.0)
        dfr_Meta = tab.container_backwards(dfr_Meta)
        # Backwards compatibility: saved files prior to 1.1.7 did not have
        # "PlateID" column:
        if not "PlateID" in dfr_Meta.columns:
            dfr_Meta["PlateID"] = np.nan
        # Read paths.csv -> Contains references to file locations
        dfr_Paths = pd.read_csv(str_TempDir + r"\paths.csv", sep=",",
                                header=0, index_col=0, engine="python")
        # Create new dataframe to hold raw and analysed data with meta data from dfr_Meta
        lst_DataframeHeaders = ["Destination","Samples",
                                str_WellsOrCapillaries,"DataFile","RawData",
                                "Processed","PlateID","Layout","References"]
        self.assay_data = pd.DataFrame(index=range(len(dfr_Meta)),columns=lst_DataframeHeaders)
        # Go through each plate in the dataframe
        for row in dfr_Meta.index:
            # Load first fields into loaded dataframe
            self.assay_data.at[row,"Destination"] = dfr_Meta.loc[row,"Destination"]
            self.assay_data.at[row,str_WellsOrCapillaries] = dfr_Meta.loc[row,str_WellsOrCapillaries]
            self.assay_data.at[row,"DataFile"] = dfr_Meta.loc[row,"DataFile"]
            self.assay_data.at[row,"PlateID"] = dfr_Meta.loc[row,"PlateID"]
            str_Subdirectory = str_TempDir + chr(92) + dfr_Meta.iloc[row,0] # Unicode 92 is back slash
            # read samples
            dfr_Samples = pd.read_csv(str_Subdirectory + r"\samples.csv", sep=",",
                                      header=0, index_col=0, engine="python")
            for col in dfr_Samples.columns:
                if type(dfr_Samples.loc[0,col]) == str:
                    dfr_Samples[col] = dfr_Samples[col].apply(df.import_string_to_list)
            self.assay_data.at[row,"Samples"] = dfr_Samples
            # read in rawdata.csv. Do per plate
            dfr_RawData = pd.read_csv(str_Subdirectory + r"\rawdata.csv", sep=",",
                                      header=0, index_col=0, engine="python")
            for col in dfr_RawData.columns:
                if type(dfr_RawData.loc[0,col]) == str:
                    dfr_RawData[col] = dfr_RawData[col].apply(df.import_string_to_list)
            self.assay_data.at[row,"RawData"] = dfr_RawData
            # Read in processed data file/frame
            dfr_Processed = pd.read_csv(str_Subdirectory + r"\processed.csv", sep=",",
                                        header=0, index_col=0, engine="python")
            for col in dfr_Processed.columns:
                if type(dfr_Processed.loc[0,col]) == str:
                    dfr_Processed[col] = dfr_Processed[col].apply(df.import_string_to_list)
            self.assay_data.at[row,"Processed"] = dfr_Processed
            # Read in references (i.e. samples that are used to normalise
            # data against, e.g. solvent/buffer only for background/signal
            # baseline or known inhibitors that give 100% effect). Assumes
            # ONE each of solvent reference, buffer reference, control compound.
            dfr_References = pd.read_csv(str_Subdirectory + r"\references.csv", sep=",",
                                         header=0, index_col=0, engine="python")
            # Backwards compatiblity: was previously a list, so indices and
            # column names need updating:
            if dfr_References.columns[0] == "0":
                dfr_References = dfr_References.rename(columns={"0":0})
            if dfr_References.columns[0] == "References":
                dfr_References_Convert = pd.DataFrame(columns=[0],
                                                      index=["SolventMean",
                                                             "SolventMedian",
                                                             "SolventSEM",
                                                             "SolventSTDEV",
                                                             "SolventMAD",
                                                             "BufferMean",
                                                             "BufferMedian",
                                                             "BufferSEM",
                                                             "BufferSTDEV",
                                                             "BufferMAD",
                                                             "ControlMean",
                                                             "ControlMedian",
                                                             "ControlSEM",
                                                             "ControlSTDEV",
                                                             "ControlMAD",
                                                             "ZPrimeMean",
                                                             "ZPrimeMeadian"])
                # Solvent reference
                dfr_References_Convert.at["SolventMean",0] = dfr_References.iloc[0,0]
                dfr_References_Convert.at["SolventMedian",0] = np.nan
                dfr_References_Convert.at["SolventSEM",0] = dfr_References.iloc[1,0]
                dfr_References_Convert.at["SolventSTDEV",0] = np.nan
                dfr_References_Convert.at["SolventMAD",0] = np.nan
                # Buffer reference
                dfr_References_Convert.at["BufferMean",0] = dfr_References.iloc[4,0]
                dfr_References_Convert.at["BufferMedian",0] = np.nan
                dfr_References_Convert.at["BufferSEM",0] = dfr_References.iloc[5,0]
                dfr_References_Convert.at["BufferSTDEV",0] = np.nan
                dfr_References_Convert.at["BufferMAD",0] = np.nan
                # Control compound
                dfr_References_Convert.at["ControlMean",0] = dfr_References.iloc[2,0]
                dfr_References_Convert.at["ControlMedian",0] = np.nan
                dfr_References_Convert.at["ControlSEM",0] = dfr_References.iloc[3,0]
                dfr_References_Convert.at["ControlSTDEV",0] = np.nan
                dfr_References_Convert.at["ControlMAD",0] = np.nan
                # Quality metrics
                dfr_References_Convert.at["ZPrimeMean",0] = dfr_References.iloc[6,0]
                dfr_References_Convert.at["ZPrimeMedian",0] = dfr_References.iloc[7,0]
                # Overwrite
                dfr_References = dfr_References_Convert
            self.assay_data.at[row,"References"] = dfr_References
            # Read in layout
            dfr_Layout = pd.read_csv(str_Subdirectory + r"\layout.csv", sep=",", 
                                     header=0, index_col=0, engine="python")
            # Backwardscompatibility - layouts used to be saved as lists in a dataframe,
            # as of 1.1.7 saved as proper dataframe with well as indices. Therefore,
            # .shape[0] -> number of wells.
            int_PlateFormat = len(self.assay_data.loc[row,"RawData"])
            if dfr_Layout.shape[0] == 1:
                self.assay_data.at[row,"PlateID"] = dfr_Layout.loc[0,"PlateID"]
                lst_Welltype = dfr_Layout["WellType"].apply(df.import_string_to_list)
                lst_ProteinNumerical = dfr_Layout["ProteinNumerical"].apply(df.import_string_to_list)
                lst_ProteinID = dfr_Layout["PurificationID"].apply(df.import_string_to_list)
                lst_ProteinConcentration = dfr_Layout["Concentration"].apply(df.import_string_to_list)
                lst_ControlNumerical = [""] * int_PlateFormat
                lst_ControlID = [""] * int_PlateFormat
                lst_ControlConcentration = [""] * int_PlateFormat
                lst_ZPrime = [""] * int_PlateFormat
                lst_ReferenceNumerical = [""] * int_PlateFormat
                lst_ReferenceID = [""] * int_PlateFormat
                lst_ReferenceConcentration = [""] * int_PlateFormat
                lst_SampleNumerical = [""] * int_PlateFormat
                lst_SampleID = [""] * int_PlateFormat
                lst_SampleConcentration = [""] * int_PlateFormat
                self.assay_data.at[row,"Layout"] = pd.DataFrame(index=range(int_PlateFormat),
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
            else:
                self.assay_data.at[row,"Layout"] = dfr_Layout

        self.paths["Data"] = dfr_Paths.iloc[1,0]
        self.paths["TransferPath"] = dfr_Paths.iloc[0,0]

        # Assay Details
        self.details = tab.details_backwards(details,
                                             additions = {"Device":"pherastar",
                                                          "Substrate2ID":"EP000001a",
                                                          "Substrate2Conc":0,
                                                          "SampleSource":"echo"})
        if self.details["AssayType"] in self.wdg_details["AssayType"].get_choices():
            row = self.wdg_details["AssayType"].get_index(self.details["AssayType"])
            self.wdg_details["AssayType"].set_selection(row)
        self.set_details["PurificationID"](self.details["PurificationID"])
        self.set_details["ProteinConc"](str(self.details["ProteinConc"]))
        self.set_details["Solvent"](self.details["Solvent"])
        self.set_details["SolventConc"](str(self.details["SolventConc"]))
        self.set_details["Buffer"](self.details["Buffer"])
        self.set_details["ELN"](self.details["ELN"])
        self.set_details["Date"](self.details["Date"])

        # Update boolean variables
        self.bol_AssayDetailsChanged = False # dfr_Boolean.iloc[0,0]
        self.bol_AssayDetailsCompleted = dfr_Boolean.iloc[1,0]
        self.bol_DataFilesAssigned = dfr_Boolean.iloc[2,0]
        self.bol_DataFilesUpdated = False # dfr_Boolean.iloc[3,0]
        self.bol_DataAnalysed = dfr_Boolean.iloc[4,0]
        self.bol_ELNPlotsDrawn = dfr_Boolean.iloc[5,0]
        if self.bol_ELNPlotsDrawn == True:  # Does not apply to single shots, but we will leave it in in case I want to unify the different functions into one
            self.tab_ELNPlots.populate(self.assay_data)
        self.bol_ExportPopulated = dfr_Boolean.iloc[6,0]
        if self.bol_ExportPopulated == True:
            self.populate_export_tab(noreturn = True)
        self.bol_ResultsDrawn = dfr_Boolean.iloc[7,0]
        if self.bol_ResultsDrawn == True:
            self.populate_results_tab()
        self.bol_ReviewsDrawn = dfr_Boolean.iloc[8,0]
        if self.bol_ReviewsDrawn == True:
            self.tab_Review.populate(noreturn = True)
        self.bol_TransferLoaded = dfr_Boolean.iloc[9,0]
        self.bol_GlobalLayout = dfr_Boolean.iloc[10,0]
        self.bol_PlateID = dfr_Boolean.iloc[11,0]
        self.bol_PlateMapPopulated = dfr_Boolean.iloc[12,0]
        # And of course this has been previously saved since
        # we are loading it from a file
        self.bol_PreviouslySaved = True

        # Populate transfer/data file tab
        for plate in self.assay_data.index:
            self.tab_Files.lbc_Transfer.InsertItem(plate,self.assay_data.iloc[plate,0])
            self.tab_Files.lbc_Transfer.SetItem(plate,1,str(self.assay_data.iloc[plate,2]))
            self.tab_Files.lbc_Transfer.SetItem(plate,2,self.assay_data.iloc[plate,3])
        # If files have been moved, the original file paths saved
        # in the bbq file are no longer up to date!
        try:
            lst_DataFiles = os.listdir(dfr_Paths.iloc[1,0])
        except:
            lst_DataFiles = []
            dfr_Paths.iloc[0,0] = "Path not found"
            dfr_Paths.iloc[1,0] = "Path not found"
        self.paths["Data"] = dfr_Paths.iloc[1,0]
        # Go through directory, get each file with correct extension,
        # compare to list already assigned. If not assigned, add to
        # tab_Files.lbc_Data
        for i in range(len(lst_DataFiles)):
            if lst_DataFiles[i].find(self.details["DataFileExtension"]) != -1:
                bol_Found = False
                for j in range(self.tab_Files.lbc_Transfer.GetItemCount()):
                    if str(lst_DataFiles[i]) == self.tab_Files.lbc_Transfer.GetItemText(j,2):
                        bol_Found = True
                        break
                if bol_Found == False:
                    self.tab_Files.lbc_Data.InsertItem(i,str(lst_DataFiles[i]))
        # Add paths to filepickers
        self.tab_Files.fpk_Transfer.set_path(dfr_Paths.iloc[0,0])
        self.tab_Files.fpk_Data.set_path(dfr_Paths.iloc[1,0])
        self.tab_Files.update_plate_assignment()

        # recreate single dfr_Layout
        self.dfr_Layout = pd.DataFrame(index=range(self.assay_data.shape[0]), columns=["PlateID","Layout"])
        for plate in self.dfr_Layout.index:
            self.dfr_Layout.at[plate,"PlateID"] = self.assay_data.loc[plate,"PlateID"]
            self.dfr_Layout.at[plate,"Layout"] = self.assay_data.loc[plate,"Layout"]
        self.bol_LayoutDefined = True
        
        self.tabs_Analysis.EnableAll(True)

    def process_data(self, dlg_progress):
        """
        This is purely a wrapper function. Some modules might the
        default process_data() from lib_tabs, others might need their own.
        """

        # Ensure any default values in assay details are deliberate
        # (i.e. incidentally identical)
        proceed = tab.default_details(details = self.details,
                                      defaults = self.default_details)
        if not proceed == True:
            return None

        tab.process_data(self, dlg_progress)

    ####  ##### #####  ###  # #      ####
    #   # #       #   #   # # #     #
    #   # ###     #   ##### # #      ###
    #   # #       #   #   # # #         #
    ####  #####   #   #   # # ##### ####
    
    def save_details(self, bol_FromTabChange = False):
        """
        Saves assay details to dataframe. If the saving is triggered by
        a tab change, and the data has already been analysed, the user
        is asked if they want to re-analyse the data.

        Arguments:
            bol_TabChange -> boolean. Set to False if function is 
                             not called from a tab change in the
                             notbeook.
        """
        # Write values of fields into variables for later use
        details_new = self.details.copy()
        for dtl in details_new.keys():
            if dtl in self.get_details.keys():
                details_new[dtl] = self.get_details[dtl]()
        details_new["DataFileExtension"] = self.details["DataFileExtension"]
        details_new["Device"] = self.details["Device"]
        self.tab_Files.fpk_Data.wildcard = f"*{details_new['DataFileExtension']}"
        
        # Include checks so that user does not leave things empty
        # check whether details have been changed and if so, update variables:
        int_CheckSum = 0
        for key in self.details.keys():
            if not details_new[key] == self.details[key]:
                int_CheckSum += 1
        if int_CheckSum != 0:
            self.details = details_new.copy()
            self.bol_AssayDetailsChanged = True
        # Check that all fields have been filled out
        int_CheckSum = 0
        for key in self.details.keys():
            if self.details[key] == "":
                int_CheckSum += 1
        if int_CheckSum == 0:
            bol_Details = True
        else:
            bol_Details = False

        if bol_Details == True:
            self.bol_AssayDetailsCompleted = True
            # Update details in dfr_Database and export tab, if applicable
            if self.bol_ExportPopulated == True:
                for lst in range(self.tab_Export.grd_Database.GetNumberRows()):
                    # lbc_Database
                    self.tab_Export.grd_Database.SetCellValue(lst,0,self.details["AssayType"] + " IC50")
                    self.tab_Export.grd_Database.SetCellValue(lst,1,self.details["PurificationID"])
                    self.tab_Export.grd_Database.SetCellValue(lst,2,str(float(self.details["ProteinConc"])/1000))
                    self.tab_Export.grd_Database.SetCellValue(lst,3,self.details["PeptideID"])
                    # omitted
                    self.tab_Export.grd_Database.SetCellValue(lst,5,str(float(self.details["PeptideConc"])/1000))
                    self.tab_Export.grd_Database.SetCellValue(lst,6,self.details["Solvent"])
                    self.tab_Export.grd_Database.SetCellValue(lst,7,str(self.details["SolventConc"]))
                    self.tab_Export.grd_Database.SetCellValue(lst,8,self.details["Buffer"])
                    # dfr_Database
                    self.dfr_Database.iloc[lst,0] = self.details["AssayType"] + " IC50"
                    self.dfr_Database.iloc[lst,1] = self.details["PurificationID"]
                    self.dfr_Database.iloc[lst,2] = float(self.details["ProteinConc"])/1000
                    self.dfr_Database.iloc[lst,3] = self.details["PeptideID"]
                    # omitted
                    self.dfr_Database.iloc[lst,5] = float(self.details["PeptideConc"])/1000
                    self.dfr_Database.iloc[lst,6] = self.details["Solvent"]
                    self.dfr_Database.iloc[lst,7] = self.details["SolventConc"]
                    self.dfr_Database.iloc[lst,8] = self.details["Buffer"]
        else:
            msg.info_missing_details()
            #self.tabs_Analysis.SetSelection(0)

        # Data already analysed but assay details changed? Offer user chance to re-analyse
        if bol_FromTabChange == True:
            if self.bol_DataAnalysed == True and self.bol_AssayDetailsChanged == True:
                if msg.query_redo_analysis() == True:
                    self.parent.AnalyseData()

    ####  ##### #   # # ##### #     #
    #   # #     #   # # #     #     #
    ####  ###   #   # # ###   #     #
    #   # #      # #  # #     #  #  #
    #   # #####   #   # ####   ## ##

    def prep_heatmap(self, plate):
        """
        Prepares dataframe for heatmap plot on review tab.

        Arguments:
            plate -> integer. Datframe index of plate to be displayed
                     on plot.
        """
        wells = self.assay_data.loc[plate,"RawData"].index
        well_ids = []
        values = []
        sample_ids = []
        for well in wells:
            well_ids.append(pf.index_to_well(well+1,wells.size))
            values.append(self.assay_data.loc[plate,"RawData"].iloc[well,1])
            if self.assay_data.loc[plate,"Layout"].loc[well,"WellType"] == "r":
                sample_ids.append(self.assay_data.loc[plate,"Layout"].loc[well,"ReferenceID"])
            elif self.assay_data.loc[plate,"Layout"].loc[well,"WellType"] == "c":
                sample_ids.append(self.assay_data.loc[plate,"Layout"].loc[well,"ControlID"])
            else:
                sample_ids.append("")
        heatmap = pd.DataFrame(data={"Well":well_ids,"SampleID":sample_ids,"Value":values},
                               index=wells)
        # This is the bottleneck
        for smpl in self.assay_data.loc[plate,"Processed"].index:
            sample = self.assay_data.loc[plate,"Processed"].loc[smpl,"SampleID"]
            for conc in range(len(self.assay_data.loc[plate,"Processed"].loc[smpl,"Locations"])):
                for rep in range(len(self.assay_data.loc[plate,"Processed"].loc[smpl,"Locations"][conc])):
                    well = self.assay_data.loc[plate,"Processed"].loc[smpl,"Locations"][conc][rep]
                    heatmap.loc[int(well),"SampleID"] = sample
        return heatmap

    def qc_to_clipboard(self, event):
        """
        Event handler. Writes all the plate quality measures
        into a dataframe to save clipboard.
        """
        plate = self.tab_Review.dic_Plots["Heat Map"].plate
        pd.DataFrame({"BufferMean":[round(self.assay_data.loc[plate,"References"].loc["BufferMean",0],2)],
            "BufferSEM":[round(self.assay_data.loc[plate,"References"].loc["BufferSEM",0],2)],
            "SolventMean":[round(self.assay_data.loc[plate,"References"].loc["SolventMean",0],2)],
            "SolventSEM":[round(self.assay_data.loc[plate,"References"].loc["SolventSEM",0],2)],
            "ControlMean":[round(self.assay_data.loc[plate,"References"].loc["ControlMean",0],2)],
            "ControlSEM":[round(self.assay_data.loc[plate,"References"].loc["ControlSEM",0],2)],
            "BufferToControl":[round(self.assay_data.loc[plate,"References"].loc["BufferMean",0]/self.assay_data.loc[plate,"References"].loc["ControlMean",0],2)],
            "SolventToControl":[round(self.assay_data.loc[plate,"References"].loc["SolventMean",0]/self.assay_data.loc[plate,"References"].loc["ControlMean",0],2)],
            "ZPrimeMean":[round(self.assay_data.loc[plate,"References"].loc["ZPrimeMean",0],3)],
            "ZPrimeMedian":[round(self.assay_data.loc[plate,"References"].loc["ZPrimeMedian",0],3)]}).to_clipboard(header=True, index=False)
    
    ####  #####  #### #    # #     #####  ####
    #   # #     #     #    # #       #   #
    ####  ###    ###  #    # #       #    ###
    #   # #         # #    # #       #       #
    #   # ##### ####   ####  #####   #   ####

    def populate_results_tab(self):
        """
        Populates Results tab with results of analysis.
        """
        self.lbc_Samples.DeleteAllItems()
        tbl = self.prep_result_table()
        self.populate_result_table(tbl)
        
        self.plt_DoseResponse.data = self.assay_data.loc[0,"Processed"].loc[0]
        self.plt_DoseResponse.plate = 0
        self.plt_DoseResponse.sample = 0
        self.rad_Res_NormFree.SetValue(True)
        self.rad_Res_NormConst.SetValue(False)
        self.rad_Res_Raw.SetValue(False)
        if self.assay_data.loc[0,"Processed"].loc[0,"DoFitFree"] == True:
            self.chk_Fit.SetValue(True)
        else:
            self.chk_Fit.SetValue(False)
        self.lbc_Samples.Select(0) # This will trigger the drawing of the plo

        # Multiplot
        self.plt_MultiPlot.IDs[0] = self.assay_data.loc[0,"Processed"].loc[0,"SampleID"]
        self.plt_MultiPlot.Dose[0] = df.moles_to_micromoles(self.assay_data.loc[0,"Processed"].loc[0,"Concentrations"])
        self.plt_MultiPlot.RawPoints[0] = self.assay_data.loc[0,"Processed"].loc[0,"Raw"]
        self.plt_MultiPlot.RawSEM[0] = self.assay_data.loc[0,"Processed"].loc[0,"RawSEM"]
        self.plt_MultiPlot.RawExcluded[0] = self.assay_data.loc[0,"Processed"].loc[0,"RawExcluded"]
        self.plt_MultiPlot.RawFit[0] = self.assay_data.loc[0,"Processed"].loc[0,"RawFit"]
        self.plt_MultiPlot.NormPoints[0] = self.assay_data.loc[0,"Processed"].loc[0,"Norm"]
        self.plt_MultiPlot.NormSEM[0] = self.assay_data.loc[0,"Processed"].loc[0,"NormSEM"]
        self.plt_MultiPlot.NormExcluded[0] = self.assay_data.loc[0,"Processed"].loc[0,"NormExcluded"]
        if self.assay_data.loc[0,"Processed"].loc[0,"Show"] == 1:
            self.rad_MultiPlotNorm.SetValue(True)
            self.plt_MultiPlot.NormFit[0] = self.assay_data.loc[0,"Processed"].loc[0,"NormFitFree"]
        else:
            self.rad_MultiPlotNorm.SetValue(False)
            self.plt_MultiPlot.NormFit[0] = self.assay_data.loc[0,"Processed"].loc[0,"NormFitConst"]
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].SetLabel(self.assay_data.loc[0,"Processed"].loc[0,"SampleID"])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[0]].Enable(True)
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].SetSelection(0)
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].Enable(True)
        self.chk_ErrorBars.Value = True
        self.chk_ExcludedPoints.Value = True
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.draw()
        self.bol_ResultsDrawn = True

    def prep_result_table(self):
        """
        Creates a dataframe for the results table.
        Separate from the actual populating of the
        wx.ListCtrl so that sorting can take place.
        """
        plt = []
        wll = []
        sid = []
        src = []
        i50 = []
        plm = []
        err = []
        for plate in self.assay_data.index:
            plate_data = self.assay_data.loc[plate,"Processed"][self.assay_data.loc[plate,"Processed"]["SampleID"] != "Control"]
            plt.extend([plate + 1] * plate_data.shape[0])
            sid.extend(plate_data.SampleID.tolist())
            src.extend([x * 1000 for x in plate_data["SourceConcentration"].tolist()])
            i50.extend([round(x[3],2) for x in plate_data["NormFitFreePars"]])
            plm.extend([chr(177)] * plate_data.shape[0])
            err.extend([round(x[3],2) for x in plate_data["NormFitFreeCI"]])
        return pd.DataFrame(data = {"Plate":plt,
                                    "SampleID":sid,
                                    "SrcConc":src,
                                    "IC50":i50,
                                    "PlusMinus":plm,
                                    "CI":err}).fillna("ND")

    def populate_result_table(self, tbl):
        """
        Helper function. Populates the actual list control lbc_Samples
        using a list of wells. Use when sorting the lists contents before
        populating.

        Arguments:
            tbl -> pandas dataframe. Contents for lbc_Samples
        """
        for well in tbl.index:
            self.lbc_Samples.InsertItem(well,str(tbl.iloc[well,0]))
            for col in range(1,tbl.shape[1]):
                self.lbc_Samples.SetItem(well,col,str(tbl.iloc[well,col]))

    def toggle_result_list_sort(self, event):
        """
        Toggles sorting of the list ctrl
        """
        clk = event.GetColumn() #clicked column
        lbc = event.GetEventObject()
        # Check if clicked column is amond sortable columns
        keys = [*lbc.titles.keys()]
        if not lbc.titles[keys[clk]]["sortable"] == True:
            return None
        top = lbc.GetItemText(0,clk)
        bot = lbc.GetItemText(lbc.GetItemCount()-1,clk)
        arrow = ""

        tbl = {}
        for col in range(lbc.GetColumnCount()):
            tbl[col] = []
            for row in range(lbc.GetItemCount()):
                tbl[col].append(lbc.GetItemText(row,col))
        # turn to pandas dataframe for sorting
        tbl = pd.DataFrame(data = tbl)

        if top > bot:
            arrow = " " + chr(708)
            ascending = True
        else:
            arrow = " " + chr(709)
            ascending = False
        
        tbl = tbl.sort_values(by = tbl.columns[clk],
                              ascending = ascending,
                              ignore_index = True)

        lbc.ClearAll()
        for k in range(len(keys)):
            if k == clk:
                lbc.InsertColumn(k, f"{keys[k]} {arrow}")
            else:
                lbc.InsertColumn(k, f"{keys[k]}")
            lbc.SetColumnWidth(k, lbc.titles[keys[k]]["width"])
        self.populate_result_table(tbl)
        lbc.Refresh()

    def show_confidence(self, event):
        """
        Event handler. Toggle display of confidence intervals on graph.
        """
        self.plt_DoseResponse.Confidence = self.chk_Confidence.GetValue()
        self.plt_DoseResponse.draw()

    def toggle_fit(self,event):
        """
        Event handler. Change whether currently displayed should be fitted or not
        """
        # get indices
        lst,smpl,plate = self.get_plot_indices()
        self.assay_data.loc[plate,"Processed"].loc[smpl,"DoFit"] = self.chk_Fit.GetValue()
        self.assay_data.loc[plate,"Processed"].loc[smpl,"DoFitFree"] = self.chk_Fit.GetValue()
        self.assay_data.loc[plate,"Processed"].loc[smpl,"DoFitConst"] = self.chk_Fit.GetValue()
        if self.chk_Fit.GetValue() == False:
            self.assay_data.loc[plate,"Processed"].at[smpl,"RawFitPars"] = [np.nan] * 4
            self.assay_data.loc[plate,"Processed"].at[smpl,"NormFitFreePars"] = [np.nan] * 4
            self.assay_data.loc[plate,"Processed"].at[smpl,"RawFit"] = [np.nan] * len(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
            self.assay_data.loc[plate,"Processed"].at[smpl,"NormFitFree"] = [np.nan] * len(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
        else:
            df.recalculate_fit_sigmoidal(self, plate, smpl, do_return = False)
        if self.assay_data.loc[plate,"Processed"].loc[smpl,"DoFit"] == True:
            self.lbc_Samples.SetItem(lst,3,str(round(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitFreePars"][3],2)))
            self.lbc_Samples.SetItem(lst,4,chr(177))
            self.lbc_Samples.SetItem(lst,5,str(round(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitFreeCI"][3],2)))
        else:
            self.lbc_Samples.SetItem(lst,3,"ND")
            self.lbc_Samples.SetItem(lst,4,"")
            self.lbc_Samples.SetItem(lst,5,"")
        self.plt_DoseResponse.data = self.assay_data.loc[plate,"Processed"].loc[smpl]
        self.plt_DoseResponse.plate = plate
        self.plt_DoseResponse.sample = smpl
        self.plt_DoseResponse.draw()
        self.update_details(self.assay_data.loc[plate,"Processed"].loc[smpl], self.IntShow())
        self.UpdateSampleReporting("event")

    def show_curve(self,event):
        """
        Event handler. Show/Update the displayed curve based on selection on ListCtr.
        """
        self.Freeze()
        fnord,smpl,plate = self.get_plot_indices()
        if self.sbk_ResultPlots.GetSelection() == 0:
            int_Show = self.assay_data.loc[plate,"Processed"].loc[smpl,"Show"]
            if int_Show == 0:
                self.rad_Res_NormFree.SetValue(False)
                self.rad_Res_NormConst.SetValue(False)
                self.rad_Res_Raw.SetValue(True)
                str_DoFit = "DoFitRaw"
            elif int_Show == 1:
                self.rad_Res_NormFree.SetValue(True)
                self.rad_Res_NormConst.SetValue(False)
                self.rad_Res_Raw.SetValue(False)
                str_DoFit = "DoFitFree"
            elif int_Show == 2:
                self.rad_Res_NormFree.SetValue(False)
                self.rad_Res_NormConst.SetValue(True)
                self.rad_Res_Raw.SetValue(False)
                str_DoFit = "DoFitConst"
            self.plt_DoseResponse.data = self.assay_data.loc[plate,"Processed"].loc[smpl]
            self.plt_DoseResponse.plate = plate
            self.plt_DoseResponse.sample = smpl
            self.plt_DoseResponse.draw()
            if self.assay_data.loc[plate,"Processed"].loc[smpl,str_DoFit] == True:
                self.chk_Fit.SetValue(True)
            else:
                self.chk_Fit.SetValue(False)
            self.update_details(self.assay_data.loc[plate,"Processed"].loc[smpl], int_Show)
            if hasattr(self, "dfr_Database"):
                self.UpdateSampleReporting(None)

        # Add Preview to multiplot
        self.plt_MultiPlot.PreviewID = self.assay_data.loc[plate,"Processed"].loc[smpl,"SampleID"]
        self.plt_MultiPlot.PreviewDose = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
        self.plt_MultiPlot.PreviewRawPoints = self.assay_data.loc[plate,"Processed"].loc[smpl,"Raw"]
        self.plt_MultiPlot.PreviewRawSEM = self.assay_data.loc[plate,"Processed"].loc[smpl,"RawSEM"]
        self.plt_MultiPlot.PreviewRawExcluded = self.assay_data.loc[plate,"Processed"].loc[smpl,"RawExcluded"]
        self.plt_MultiPlot.PreviewRawFit = self.assay_data.loc[plate,"Processed"].loc[smpl,"RawFit"]
        self.plt_MultiPlot.PreviewNormPoints = self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"]
        self.plt_MultiPlot.PreviewNormSEM = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"]
        self.plt_MultiPlot.PreviewNormExcluded = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormExcluded"]
        if self.assay_data.loc[plate,"Processed"].loc[smpl,"Show"] == 1:
            self.plt_MultiPlot.PreviewNormFit = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitFree"]
        else:
            self.plt_MultiPlot.PreviewNormFit = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitConst"]
        self.plt_MultiPlot.draw()
        self.Thaw()

    def update_details(self, dfr_Input, int_Show):
        """
        Updates details of sample shown next to plot.

        Arguments:
            dfr_Input -> pandas dataframe. All data for the selected sample
            int_Show -> integer. Which dataset to show:
                        0: Raw data, free fit
                        1: Normalised data, free fit
                        2: Normalised data, constrained fit.
        """
        if int_Show == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
            str_RSquareKeyword = "RawFitR2"
        elif int_Show == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoFitFree"
            str_Confidence = "NormFitFreeCI"
            str_RSquareKeyword = "NormFitFreeR2"
        elif int_Show == 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoFitConst"
            str_Confidence = "NormFitConstCI"
            str_RSquareKeyword = "NormFitConstR2"
        if dfr_Input[str_DoFit] == True:
            str_IC50 = df.write_IC50(dfr_Input[str_Pars][3], dfr_Input[str_DoFit],dfr_Input[str_Confidence][3])
            if dfr_Input[str_Pars][1] < -20:
                str_BottomWarning = chr(9888) + " outside range"
            else:
                str_BottomWarning = ""
            str_YBot = str(round(dfr_Input[str_Pars][1],2)) + " " + str_BottomWarning
            if dfr_Input[str_Pars][0] > 120:
                str_TopWarning = chr(9888) + " outside range"
            else:
                str_TopWarning = ""
            str_YTop = str(round(dfr_Input[str_Pars][0],2)) + " " + str_TopWarning
            flt_Span = round(dfr_Input[str_Pars][0]-dfr_Input[str_Pars][1],1)
            if flt_Span > 120:
                str_SpanWarning = chr(9888) + " outside range"
            else:
                str_SpanWarning = ""
            str_Span = str(str(flt_Span) + str_SpanWarning)
            str_Hill = str(round(dfr_Input[str_Pars][2],2))
            str_RSquare = str(round(dfr_Input[str_RSquareKeyword],3))
            bol_Enable = True
        else:
            str_IC50 = "N.D."
            str_YBot = "N.D."
            str_YTop = "N.D."
            str_Span = "N.D."
            str_Hill = "N.D."
            str_RSquare = "N.D."
            bol_Enable = False
        self.Freeze()
        self.lbl_Bottom.SetLabel(str_YBot)
        self.lbl_Bottom.Enable(bol_Enable)
        self.lbl_Top.SetLabel(str_YTop)
        self.lbl_Top.Enable(bol_Enable)
        self.lbl_Span.SetLabel(str_Span)
        self.lbl_Span.Enable(bol_Enable)
        self.lbl_Slope.SetLabel(str_Hill)
        self.lbl_Slope.Enable(bol_Enable)
        self.lbl_IC.SetLabel(str_IC50)
        self.lbl_IC.Enable(bol_Enable)
        self.lbl_RSquare.SetLabel(str_RSquare)
        self.lbl_RSquare.Enable(bol_Enable)
        self.Thaw()

    def CopyCurveParameters(self, event):
        """
        Event handler. Copies parameters of currently displayed
        curve to clipboard.
        """
        if self.plt_DoseResponse.data["Show"] == 0:
            str_Type = "Raw data free fit"
            str_RawOrNorm = "Raw"
            str_FreeOrConstrained = ""
        elif self.plt_DoseResponse.data["Show"] == 1:
            str_Type = "Normalised data free fit"
            str_RawOrNorm = "Norm"
            str_FreeOrConstrained = "Free"
        elif self.plt_DoseResponse.data["Show"] == 2:
            str_Type = "Normalised data constrained fit"
            str_RawOrNorm = "Norm"
            str_FreeOrConstrained = "Const"
        flt_Top = round(self.plt_DoseResponse.data[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][0],2)
        flt_Bottom = round(self.plt_DoseResponse.data[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][1],2)
        flt_IC50 = round(self.plt_DoseResponse.data[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][3],3)
        flt_Slope = round(self.plt_DoseResponse.data[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][2],2)
        flt_RSquare = round(self.plt_DoseResponse.data[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"R2"],3)
        flt_Span = round(self.plt_DoseResponse.data[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][0]-self.plt_DoseResponse.data[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][1],2)
        pd.DataFrame(index=["Fit","IC50(uM)","Hill Slope","Top","Bottom","Span","RSquare"],
                     data=[str_Type,flt_IC50,flt_Slope,flt_Top,flt_Bottom,flt_Span,flt_RSquare],
                     columns=["Value"]).to_clipboard()

    def UpdateSampleReporting(self, event):
        """
        Updates what gets reported in lbc_Samples and lbc_Database.
        Only fitting results of normalised data will be reported.
        """
        lst,smpl,plate = self.get_plot_indices()
        int_Show = self.assay_data.loc[plate,"Processed"].loc[smpl,"Show"]
        if int_Show == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
        elif int_Show == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoFitFree"
            str_Confidence = "NormFitFreeCI"
        elif int_Show == 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoFitConst"
            str_Confidence = "NormFitConstCI"
        # Update lists
        if self.assay_data.loc[plate,"Processed"].loc[smpl,str_DoFit] == True:
            self.lbc_Samples.SetItem(lst,3,str(round(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3],2)))
            self.lbc_Samples.SetItem(lst,4,chr(177))
            self.lbc_Samples.SetItem(lst,5,str(round(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3],2)))
        if not "activity" in self.details["AssayCategory"]:
            self.UpdateDatabaseTable(lst, smpl, plate, int_Show)
        else:
            self.UpdateDatabaseTableActivity(lst, smpl, plate, int_Show)
        
    def UpdateDatabaseTable(self, lst, smpl, plate, int_Show):
        """
        Updates database table at the speciied position with the specified parameters.

        Arguments:
            lst -> integer. Position of the entry in the results table.
            smpl -> integer. Dataframe index of the sample.
            plate -> integer. Dataframe index of the plate the sample is on
            int_show -> integer. Determines which parameters will be shown
                        0: raw data fit
                        1: normalised, free fit
                        2: normalised, constrained fit
        """

        if int_Show == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
            str_R2 = "RawFitR2"
            str_Errors = "RawFitErrors"
        elif int_Show == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoFitFree"
            str_Confidence = "NormFitFreeCI"
            str_R2 = "NormFitFreeR2"
            str_Errors = "NormFitFreeErrors"
        elif int_Show == 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoFitConst"
            str_Confidence = "NormFitConstCI"
            str_R2 = "NormFitConstR2"
            str_Errors = "NormFitConstErrors"

        if self.bol_ExportPopulated == True:
            if self.assay_data.loc[plate,"Processed"].loc[smpl,str_DoFit] == True:
                # LIST
                self.tab_Export.grd_Database.SetCellValue(lst,13,str(np.log10(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3])/1000000))) # log IC50
                self.tab_Export.grd_Database.SetCellValue(lst,14,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Errors][3]))
                self.tab_Export.grd_Database.SetCellValue(lst,15,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3])) # IC50 in uM
                self.tab_Export.grd_Database.SetCellValue(lst,16,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] +
                    self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3]))
                self.tab_Export.grd_Database.SetCellValue(lst,17,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] -
                    self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3]))
                self.tab_Export.grd_Database.SetCellValue(lst,18,str(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][2]))) # Hill slope
                # omitted
                self.tab_Export.grd_Database.SetCellValue(lst,20,str(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][1]))) # Bottom of curve
                self.tab_Export.grd_Database.SetCellValue(lst,21,str(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][0]))) # Top of curve
                self.tab_Export.grd_Database.SetCellValue(lst,22,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_R2])) # Rsquared
                self.tab_Export.grd_Database.SetCellValue(lst,25,str(self.assay_data.loc[plate,"References"].loc["SolventMean",0])) # enzyme reference
                self.tab_Export.grd_Database.SetCellValue(lst,26,str(self.assay_data.loc[plate,"References"].loc["SolventSEM",0])) # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.tab_Export.grd_Database.SetCellValue(lst,27+intColumnOffset,str(lstConcentrations[j]))
                    self.tab_Export.grd_Database.SetCellValue(lst,28+intColumnOffset,str(self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"][j]))
                    self.tab_Export.grd_Database.SetCellValue(lst,29+intColumnOffset,str(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"][j]))
                # dfr_Database
                self.dfr_Database.iloc[lst,13] = np.log10(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3])/1000000) # log IC50
                self.dfr_Database.iloc[lst,14] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_Errors][3]
                self.dfr_Database.iloc[lst,15] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] # IC50 in uM
                self.dfr_Database.iloc[lst,16] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] + self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3]
                self.dfr_Database.iloc[lst,17] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] - self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3]
                self.dfr_Database.iloc[lst,18] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][2]) # Hill slope
                # omitted
                self.dfr_Database.iloc[lst,20] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][1]) # Bottom of curve
                self.dfr_Database.iloc[lst,21] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][0]) # Top of curve
                self.dfr_Database.iloc[lst,22] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_R2] # Rsquared
                self.dfr_Database.iloc[lst,25] = self.assay_data.loc[plate,"References"].loc["SolventMean",0] # enzyme reference
                self.dfr_Database.iloc[lst,26] = self.assay_data.loc[plate,"References"].loc["SolventSEM",0] # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[plate,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.dfr_Database.iloc[lst,27+intColumnOffset] = lstConcentrations[j]
                    self.dfr_Database.iloc[lst,28+intColumnOffset] = self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"][j]
                    self.dfr_Database.iloc[lst,29+intColumnOffset] = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"][j]
            else:
                # LIST
                self.lbc_Samples.SetItem(lst,3,"ND")
                self.lbc_Samples.SetItem(lst,4,"")
                self.lbc_Samples.SetItem(lst,5,"")
                self.tab_Export.grd_Database.SetCellValue(lst,13,"")
                self.tab_Export.grd_Database.SetCellValue(lst,14,"")
                self.tab_Export.grd_Database.SetCellValue(lst,15,"")
                self.tab_Export.grd_Database.SetCellValue(lst,16,"")
                self.tab_Export.grd_Database.SetCellValue(lst,17,"")
                self.tab_Export.grd_Database.SetCellValue(lst,18,"")
                # omitted
                self.tab_Export.grd_Database.SetCellValue(lst,20,"")
                self.tab_Export.grd_Database.SetCellValue(lst,21,"")
                self.tab_Export.grd_Database.SetCellValue(lst,22,"")
                self.tab_Export.grd_Database.SetCellValue(lst,25,str(self.assay_data.loc[plate,"References"].loc["SolventMean",0])) # enzyme reference
                self.tab_Export.grd_Database.SetCellValue(lst,26,str(self.assay_data.loc[plate,"References"].loc["SolventSEM",0])) # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.tab_Export.grd_Database.SetCellValue(lst,27+intColumnOffset,str(lstConcentrations[j]))
                    self.tab_Export.grd_Database.SetCellValue(lst,28+intColumnOffset,str(self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"][j]))
                    self.tab_Export.grd_Database.SetCellValue(lst,29+intColumnOffset,str(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"][j]))
                # dfr_Database
                self.dfr_Database.iloc[lst,13] = np.nan # log IC50
                self.dfr_Database.iloc[lst,14] = np.nan
                self.dfr_Database.iloc[lst,15] = np.nan # IC50 in uM
                self.dfr_Database.iloc[lst,16] = np.nan
                self.dfr_Database.iloc[lst,17] = np.nan
                self.dfr_Database.iloc[lst,18] = np.nan # Hill slope
                # omitted
                self.dfr_Database.iloc[lst,20] = np.nan # Bottom of curve
                self.dfr_Database.iloc[lst,21] = np.nan # Top of curve
                self.dfr_Database.iloc[lst,22] = np.nan # Rsquared
                self.dfr_Database.iloc[lst,25] = self.assay_data.loc[plate,"References"].loc["SolventMean",0] # enzyme reference
                self.dfr_Database.iloc[lst,26] = self.assay_data.loc[plate,"References"].loc["SolventSEM",0] # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.dfr_Database.iloc[lst,27+intColumnOffset] = lstConcentrations[j]
                    self.dfr_Database.iloc[lst,28+intColumnOffset] = self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"][j]
                    self.dfr_Database.iloc[lst,29+intColumnOffset] = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"][j]
        self.bol_ELNPlotsDrawn = False

    def UpdateDatabaseTableActivity(self, lst, smpl, plate, int_Show):
        """
        Updates database table at the speciied position with the specified parameters.

        Arguments:
            lst -> integer. Position of the entry in the results table.
            smpl -> integer. Dataframe index of the sample.
            plate -> integer. Dataframe index of the plate the sample is on
            int_show -> integer. Determines which parameters will be shown
                        0: raw data fit
                        1: normalised, free fit
                        2: normalised, constrained fit
        """

        if int_Show == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
            str_R2 = "RawFitR2"
            str_Errors = "RawFitErrors"
        elif int_Show == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoFitFree"
            str_Confidence = "NormFitFreeCI"
            str_R2 = "NormFitFreeR2"
            str_Errors = "NormFitFreeErrors"
        elif int_Show == 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoFitConst"
            str_Confidence = "NormFitConstCI"
            str_R2 = "NormFitConstR2"
            str_Errors = "NormFitConstErrors"

        if self.bol_ExportPopulated == True:
            if self.assay_data.loc[plate,"Processed"].loc[smpl,str_DoFit] == True:
                # LIST
                self.tab_Export.grd_Database.SetCellValue(lst,22,str(np.log10(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3])/1000000))) # log IC50
                self.tab_Export.grd_Database.SetCellValue(lst,23,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Errors][3]))
                self.tab_Export.grd_Database.SetCellValue(lst,24,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3])) # IC50 in uM
                self.tab_Export.grd_Database.SetCellValue(lst,25,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] +
                    self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3]))
                self.tab_Export.grd_Database.SetCellValue(lst,26,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] -
                    self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3]))
                self.tab_Export.grd_Database.SetCellValue(lst,27,str(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][2]))) # Hill slope
                self.tab_Export.grd_Database.SetCellValue(lst,28,str(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][1]))) # Bottom of curve
                self.tab_Export.grd_Database.SetCellValue(lst,29,str(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][0]))) # Top of curve
                self.tab_Export.grd_Database.SetCellValue(lst,30,str(self.assay_data.loc[plate,"Processed"].loc[smpl,str_R2])) # Rsquared
                self.tab_Export.grd_Database.SetCellValue(lst,16,str(self.assay_data.loc[plate,"References"].loc["SolventMean",0])) # enzyme reference
                self.tab_Export.grd_Database.SetCellValue(lst,17,str(self.assay_data.loc[plate,"References"].loc["SolventSEM",0])) # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.tab_Export.grd_Database.SetCellValue(lst,32+intColumnOffset,str(lstConcentrations[j]))
                    self.tab_Export.grd_Database.SetCellValue(lst,33+intColumnOffset,str(self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"][j]))
                    self.tab_Export.grd_Database.SetCellValue(lst,34+intColumnOffset,str(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"][j]))
                # dfr_Database
                self.dfr_Database.iloc[lst,22] = np.log10(float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3])/1000000) # log IC50
                self.dfr_Database.iloc[lst,23] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_Errors][3]
                self.dfr_Database.iloc[lst,24] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] # IC50 in uM
                self.dfr_Database.iloc[lst,25] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] + self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3]
                self.dfr_Database.iloc[lst,26] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][3] - self.assay_data.loc[plate,"Processed"].loc[smpl,str_Confidence][3]
                self.dfr_Database.iloc[lst,27] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][2]) # Hill slope
                self.dfr_Database.iloc[lst,28] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][1]) # Bottom of curve
                self.dfr_Database.iloc[lst,29] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,str_Pars][0]) # Top of curve
                self.dfr_Database.iloc[lst,30] = self.assay_data.loc[plate,"Processed"].loc[smpl,str_R2] # Rsquared
                self.dfr_Database.iloc[lst,16] = self.assay_data.loc[plate,"References"].loc["SolventMean",0] # enzyme reference
                self.dfr_Database.iloc[lst,17] = self.assay_data.loc[plate,"References"].loc["SolventSEM",0] # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[plate,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.dfr_Database.iloc[lst,32+intColumnOffset] = lstConcentrations[j]
                    self.dfr_Database.iloc[lst,33+intColumnOffset] = self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"][j]
                    self.dfr_Database.iloc[lst,34+intColumnOffset] = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"][j]
            else:
                # LIST
                self.lbc_Samples.SetItem(lst,3,"ND")
                self.lbc_Samples.SetItem(lst,4,"")
                self.lbc_Samples.SetItem(lst,5,"")
                self.tab_Export.grd_Database.SetCellValue(lst,22,"")
                self.tab_Export.grd_Database.SetCellValue(lst,23,"")
                self.tab_Export.grd_Database.SetCellValue(lst,24,"")
                self.tab_Export.grd_Database.SetCellValue(lst,25,"")
                self.tab_Export.grd_Database.SetCellValue(lst,26,"")
                self.tab_Export.grd_Database.SetCellValue(lst,27,"")
                self.tab_Export.grd_Database.SetCellValue(lst,28,"")
                self.tab_Export.grd_Database.SetCellValue(lst,29,"")
                self.tab_Export.grd_Database.SetCellValue(lst,30,"")
                self.tab_Export.grd_Database.SetCellValue(lst,16,str(self.assay_data.loc[plate,"References"].loc["SolventMean",0])) # enzyme reference
                self.tab_Export.grd_Database.SetCellValue(lst,17,str(self.assay_data.loc[plate,"References"].loc["SolventSEM",0])) # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.tab_Export.grd_Database.SetCellValue(lst,32+intColumnOffset,str(lstConcentrations[j]))
                    self.tab_Export.grd_Database.SetCellValue(lst,33+intColumnOffset,str(self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"][j]))
                    self.tab_Export.grd_Database.SetCellValue(lst,34+intColumnOffset,str(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"][j]))
                # dfr_Database
                self.dfr_Database.iloc[lst,22] = np.nan # log IC50
                self.dfr_Database.iloc[lst,23] = np.nan
                self.dfr_Database.iloc[lst,24] = np.nan # IC50 in uM
                self.dfr_Database.iloc[lst,25] = np.nan
                self.dfr_Database.iloc[lst,26] = np.nan
                self.dfr_Database.iloc[lst,27] = np.nan # Hill slope
                self.dfr_Database.iloc[lst,28] = np.nan # Bottom of curve
                self.dfr_Database.iloc[lst,29] = np.nan # Top of curve
                self.dfr_Database.iloc[lst,30] = np.nan # Rsquared
                self.dfr_Database.iloc[lst,16] = self.assay_data.loc[plate,"References"].loc["SolventMean",0] # enzyme reference
                self.dfr_Database.iloc[lst,17] = self.assay_data.loc[plate,"References"].loc["SolventSEM",0] # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.dfr_Database.iloc[lst,32+intColumnOffset] = lstConcentrations[j]
                    self.dfr_Database.iloc[lst,33+intColumnOffset] = self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"][j]
                    self.dfr_Database.iloc[lst,34+intColumnOffset] = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"][j]
            self.bol_ELNPlotsDrawn = False

    def EditSourceConcentration(self,event):
        """
        Event handler. Gets called from the source concentration
        edit dialog.
        """
        focus = self.lbc_Samples.GetFocusedItem()
        str_OldConc = self.lbc_Samples.GetItemText(focus,2)
        dlg_ChangeSourceConc = dlg_SourceChange(self,str_OldConc)
        bol_Update = dlg_ChangeSourceConc.ShowModal()
        dlg_ChangeSourceConc.Destroy()
        if self.str_NewConc == None:
            return None
        if bol_Update == True:
            if self.str_NewConc != str_OldConc:
                # Get which plate it is
                plate = int(self.lbc_Samples.GetItemText(focus,0))-1 # Human plate numbering vs computer indexing!
                # Get which sample it is
                str_Sample = self.lbc_Samples.GetItemText(focus,1)
                dfr_Plate = self.assay_data.loc[plate,"Processed"]
                smpl = dfr_Plate[dfr_Plate["SampleID"] == str_Sample].index.tolist()[0]
                self.assay_data.loc[plate,"Processed"].loc[smpl,"SourceConcentration"] = float(self.str_NewConc)/1000
                for conc in range(len(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])):
                    self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"][conc] = df.change_concentrations(float(str_OldConc),float(self.str_NewConc),
                        self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"][conc],
                        self.assay_data.loc[plate,"Processed"].loc[smpl,"AssayVolume"])
                if self.assay_data.loc[plate,"Processed"].loc[smpl,"DoFit"] == True:
                    df.recalculate_fit_sigmoidal(self, plate, smpl, do_return = False)
                self.plt_DoseResponse.data = self.assay_data.loc[plate,"Processed"].loc[smpl]
                self.plt_DoseResponse.plate = plate
                self.plt_DoseResponse.sample = smpl
                self.plt_DoseResponse.draw()
                self.lbc_Samples.SetItem(focus,2,self.str_NewConc)
                if self.IntShow() == 2:
                    if self.assay_data.loc[plate,"Processed"].loc[smpl,"DoFit"] == True:
                        self.lbc_Samples.SetItem(focus,3,str(round(self.assay_data.loc[plate,"Processed"].loc[smpl,"RawFitFreePars"][3],2)))
                        self.lbc_Samples.SetItem(focus,4,chr(177))
                        self.lbc_Samples.SetItem(focus,5,str(round(self.assay_data.loc[plate,"Processed"].loc[smpl,"RawFitFreeCI"][3],2)))
                    else:
                        self.lbc_Samples.SetItem(focus,3,"ND")
                        self.lbc_Samples.SetItem(focus,4,"")
                        self.lbc_Samples.SetItem(focus,5,"")
                else:
                    if self.assay_data.loc[plate,"Processed"].loc[smpl,"DoFit"] == True:
                        self.lbc_Samples.SetItem(focus,3,str(round(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitFreePars"][3],2)))
                        self.lbc_Samples.SetItem(focus,4,chr(177))
                        self.lbc_Samples.SetItem(focus,5,str(round(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitFreeCI"][3],2)))
                    else:
                        self.lbc_Samples.SetItem(focus,3,"ND")
                        self.lbc_Samples.SetItem(focus,4,"")
                        self.lbc_Samples.SetItem(focus,5,"")
                self.update_details(self.assay_data.loc[plate,"Processed"].loc[smpl],self.assay_data.loc[plate,"Processed"].loc[smpl,"Show"])
                self.UpdateSampleReporting(None)
        self.str_NewConc = None

    def results_to_file(self,event):
        """
        Event handler. Copies results table to clipboard.
        """
        dfr_ResultsTable = pd.DataFrame(columns=["Plate","SampleID",
                                                 "SourceConcentration[mM]",
                                                 "TopConcentration[uM]",
                                                 "IC50[uM]"],
                                        index=range(self.lbc_Samples.GetItemCount()))
        count = 0
        for plate in self.assay_data.index:
            for smpl in self.assay_data.loc[plate,"Processed"].index:
                dfr_ResultsTable.loc[count,"Plate"] = plate+1
                dfr_ResultsTable.loc[count,"SampleID"] = self.assay_data.loc[plate,"Processed"].loc[smpl,"SampleID"]
                dfr_ResultsTable.loc[count,"SourceConcentration[mM]"] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,"SourceConcentration"]) * 1000
                dfr_ResultsTable.loc[count,"TopConcentration[uM]"] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"][0]) * 1000000
                dfr_ResultsTable.loc[count,"IC50[uM]"] = float(self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitFreePars"][3]) * 1000000
                count += 1
        # Export as csv:
        fdlg = wx.FileDialog(self,
                             message = "Save summary table as as",
                             wildcard="Comma separated files (*.csv)|*.csv",
                             style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .png. If so, remove
            if str_SavePath[-1:-4] == ".csv":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            dfr_ResultsTable.to_csv(str_SavePath)

    def get_plot_indices(self):
        """
        Gets the indices of the selected ploton lbc_Samples 
        iside of self.assay_data

        Returns:
            lst -> integer. Index of selected sample
            df -> integer. Index in plate's subdataframe
            plate -> integer. Index of the plate's subdataframe
                     within self.assay_data
        """
        # Get list index of selected sample
        lst = self.lbc_Samples.GetFirstSelected()
        # Get plate index
        plate = int(self.lbc_Samples.GetItemText(lst,0))-1 # Human plate numbering vs computer indexing!
        # get index on plate of selected sample
        dfr_Sample = self.assay_data.loc[plate,"Processed"]
        df = dfr_Sample[dfr_Sample["SampleID"] == self.lbc_Samples.GetItemText(lst,1)].index.tolist()[0]
        return lst, df, plate

    def IntShow(self):
        """
        Determines which dataset to show and returns corresponding
        integer:
            0: Raw data, free fit
            1: Normalised data, free fit
            2: Normalised data, constrained fit
        """
        if self.rad_Res_NormFree.Value == True:
            return 1
        elif self.rad_Res_NormConst.Value == True:
            return 2
        else:
            return 0

    def RadRaw(self, event):
        """
        Event handler for selecting rad_Res_Raw
        radio button.
        """
        self.rad_Res_Raw.SetValue(True)
        self.rad_Res_NormFree.SetValue(False)
        self.rad_Res_NormConst.SetValue(False)

        fnord,smpl,plate = self.get_plot_indices()
        self.assay_data.loc[plate,"Processed"].loc[smpl,"Show"] = self.IntShow()

        self.show_curve(event)

    def RadNormFree(self, event):
        """
        Event handler for selecting rad_Res_NormFree
        radio button.
        """
        self.rad_Res_Raw.SetValue(False)
        self.rad_Res_NormFree.SetValue(True)
        self.rad_Res_NormConst.SetValue(False)

        fnord,smpl,plate = self.get_plot_indices()
        self.assay_data.loc[plate,"Processed"].loc[smpl,"Show"] = self.IntShow()

        self.show_curve(event)

    def RadNormConst(self, event):
        """
        Event handler for selecting rad_Res_NormConst
        radio button.
        """
        self.rad_Res_Raw.SetValue(False)
        self.rad_Res_NormFree.SetValue(False)
        self.rad_Res_NormConst.SetValue(True)

        fnord,smpl,plate = self.get_plot_indices()
        self.assay_data.loc[plate,"Processed"].loc[smpl,"Show"] = self.IntShow()

        self.show_curve(event)

    def all_plots_to_png(self, event):
        """
        Event handler. Saves dose response curve plots for all
        samples as separate PNG files.
        """
        with wx.DirDialog(self,
                          message="Select a directory to save plots") as dlg_Directory:

            if dlg_Directory.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            str_SaveDirPath = dlg_Directory.GetPath()
        # Pick directory here. If no directory picked, self.Thaw() and end function.
        self.dlg_progress = wx.ProgressDialog(title = u"Processing",
                                              message = u"Saving plots.",
                                              maximum = 100,
                                              parent = self,
                                              style = wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)
        thd_SavingPlots = threading.Thread(target=self.all_plots_to_png_thread,
                                           args=(str_SaveDirPath,),
                                           daemon=True)
        thd_SavingPlots.start()

    def all_plots_to_png_thread(self, str_SaveDirPath):
        """
        Thread to write all plots to PNG.
        """
        self.Freeze()
        int_Samples = 0
        for plate in self.assay_data.index:
            int_Samples += len(self.assay_data.loc[plate,"Processed"])
        self.dlg_progress.SetRange(int_Samples)
        count = 0
        for plate in self.assay_data.index:
            for smpl in self.assay_data.loc[plate,"Processed"].index:
                #DO STUFF TO MAKE PLOT
                tempplot = cp.CurvePlotPanel(self.tab_Results, (600,450), self)
                tempplot.data = self.assay_data.loc[plate,"Processed"].loc[smpl]
                tempplot.draw()
                sampleid = self.assay_data.loc[plate,"Processed"].loc[smpl,"SampleID"]
                savepath = os.path.join(str_SaveDirPath, sampleid + ".png")
                tempplot.figure.savefig(savepath, dpi=None, facecolor="w", edgecolor="w",
                                        orientation="portrait", format=None,
                                        transparent=False, bbox_inches=None,
                                        pad_inches=0.1)
                tempplot.Destroy()
                self.dlg_progress.Update(count)
                count += 1
        self.Thaw()
        self.dlg_PlotsProgress.Destroy()
    
    def toggle_error_bars(self, event):
        """
        Event handler. Toggles error bars on plot.
        """
        self.plt_MultiPlot.ErrorBars = event.GetEventObject().GetValue()
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.draw()

    def toggle_outside_warning(self, event):
        """
        Event handler. Toggles warning about datapoints outside
        boundaires for plot.
        """
        self.plt_DoseResponse.outside_warning = event.GetEventObject().GetValue()
        self.plt_DoseResponse.draw()

    def toggle_excluded_points(self, event):
        """
        Event handler. Toggles excluded points on plot.
        """
        self.plt_MultiPlot.ExcludedPoints = self.chk_ExcludedPoints.Value
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.draw()
    
    def toggle_preview_plot(self, event):
        """
        Event handler. Toggles preview of currently selected
        sample on multiplot.
        """
        self.plt_MultiPlot.Preview = self.chk_PreviewPlot.GetValue()
        self.plt_MultiPlot.draw()

    def MultiPlotNormalised(self):
        """
        Event handlers. Switches between displaying raw data and
        normalised data on multiplot.
        """
        if self.rad_MultiPlotRaw.GetValue() == True:
            return False
        else:
            return True

    def mutliplot_select_colour(self, event):
        """
        Event handler. Changes colour of graph on multiplot.
        """
        clr = event.GetEventObject().GetSelection()
        self.plt_MultiPlot.Colours[event.GetEventObject().Index] = self.plt_MultiPlot.ColourChoices[clr]
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.draw()

    def add_graph(self, event):
        """
        Event handler. Adds selected graph to multiplot.
        """
        fnord,smpl,plate = self.get_plot_indices()
        graph = event.GetEventObject().Index
        self.plt_MultiPlot.IDs[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"SampleID"]
        self.plt_MultiPlot.Dose[graph] = df.moles_to_micromoles(self.assay_data.loc[plate,"Processed"].loc[smpl,"Concentrations"])
        self.plt_MultiPlot.RawPoints[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"Raw"]
        self.plt_MultiPlot.RawSEM[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"RawSEM"]
        self.plt_MultiPlot.RawExcluded[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"RawExcluded"]
        self.plt_MultiPlot.RawFit[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"RawFit"]
        self.plt_MultiPlot.NormPoints[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"Norm"]
        self.plt_MultiPlot.NormSEM[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormSEM"]
        self.plt_MultiPlot.NormExcluded[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormExcluded"]
        if self.assay_data.loc[plate,"Processed"].loc[smpl,"Show"] == 1:
            self.plt_MultiPlot.NormFit[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitFree"]
        else:
            self.plt_MultiPlot.NormFit[graph] = self.assay_data.loc[plate,"Processed"].loc[smpl,"NormFitConst"]
        self.dic_BitmapCombos[self.lst_BitmapCombos[graph]].Enable(True)
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[graph]].SetLabel(self.assay_data.loc[plate,"Processed"].loc[smpl,"SampleID"])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[graph]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[graph]].Enable(True)
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.draw()

    def remove_graph(self, event):
        """
        Event handler. Removes a graph from multiplot.
        """
        # First, test that at least one graph will remain on the plot:
        checksum = 0
        for i in range(len(self.plt_MultiPlot.IDs)):
            if self.plt_MultiPlot.IDs[i] != "":
                checksum += 1
        if checksum > 1:
            graph = event.GetEventObject().Index
            self.plt_MultiPlot.IDs[graph] = ""
            self.plt_MultiPlot.RawPoints[graph] = []
            self.plt_MultiPlot.RawFit[graph] = []
            self.plt_MultiPlot.NormPoints[graph] = []
            self.plt_MultiPlot.NormFit[graph] = []
            self.dic_BitmapCombos[self.lst_BitmapCombos[graph]].Enable(False)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[graph]].SetLabel("no sample")
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[graph]].Enable(False)
            self.dic_RemoveButtons[self.lst_RemoveButtons[graph]].Enable(False)
            self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
            self.plt_MultiPlot.draw()
        else:
            wx.MessageBox(message = "Cannot remove this graph.\n"
                                    + "At least one graph must be displayed.",
                          caption = "No can do",
                          style = wx.OK|wx.ICON_INFORMATION)

    def MultiRadNorm(self, event):
        """
        Event handler for selecting rad_MultiPlotNorm
        radio button.
        """
        if self.rad_MultiPlotNorm.GetValue() == True:
            self.rad_MultiPlotRaw.SetValue(False)
        else:
            self.rad_MultiPlotRaw.SetValue(True)
        self.plt_MultiPlot.Normalised = True
        self.plt_MultiPlot.draw()

    def MultiRadRaw(self, event):
        """
        Event handler for selecting rad_MultiPlotRaw
        radio button.
        """
        if self.rad_MultiPlotRaw.GetValue() == True:
            self.rad_MultiPlotNorm.SetValue(False)
        else:
            self.rad_MultiPlotNorm.SetValue(True)
        self.plt_MultiPlot.Normalised = False
        self.plt_MultiPlot.draw()

    def FitToolTip(self, event):
        """
        Event handler. Displays explanatory note for
        sigmoidal dose response fitting.
        """
        try: self.dlg_InfoToolTip.Destroy()
        except: None
        self.dlg_InfoToolTip = tt.dlg_InfoToolTip(self,
                                                 self.parent.str_OtherPath,
                                                 "SigmoidalDoseResponseToolTip.png")
        self.dlg_InfoToolTip.Show()

    ##### #   # ####   ###  ####  #####
    #      # #  #   # #   # #   #   #
    ###     #   ####  #   # ####    #
    #      # #  #     #   # #   #   #
    ##### #   # #      ###  #   #   #

    def populate_export_tab(self, noreturn = False):
        populated = self.tab_Export.populate(dbf_function = db_dataframe,
                                             noreturn = noreturn,
                                             kwargs = {"details":self.details,
                                                       "colnames":self.lst_Headers,
                                                       "assay_data":self.assay_data})
        if not noreturn == False:
            return populated

    def db_df_verify(self, tab_export, conn, db_table, db_dependencies, uploadafter):
        """
        Wrapper function to make db_df_verify accessible from
        outside the module.
        
        Arguments:
            tab_export -> instance of tab_Export
            conn -> database connection
            db_table => name of the database table
            db_dependencies -> nested dictionary, contains information to verify
                dependencies of database tables (e.g. how to retrieve FKEYS)
            uploadafter -> boolean. Whether to trigger the
                           upload of the data after verification
        """
        self.verified = db_df_verify(self, conn, db_table, db_dependencies)
        if uploadafter == False:
            tab_export.dlg_progress.Destroy()
        tab_export.verified(self.verified, db_table, db_dependencies, uploadafter)

    def db_upload(self, tab_export, conn, db_table):
        """
        Wrapper function to make db_upload accessible from
        outside the module
        """
        upload = db_upload(self, conn, db_table)
        if type(upload) == str:
            self.uploaded = False
        else:
            self.uploaded = True
        if hasattr(tab_export, "dlg_progress"):
            tab_export.dlg_progress.Destroy()
        tab_export.uploaded(upload)