"""
Main module for BBQ.

Classes:
    frm_Main
    BBQ

Functions:
    main

"""

# The following code taken from the wxPython Wiki:                           
# https://wiki.wxpython.org/How%20to%20create%20a%20splash%20screen%20while%20loading%20%28Phoenix%29


import os
import sys
import wx
import wx.lib.agw.advancedsplash as AS
SHOW_SPLASH = True

#import logging
#filename = os.path.join(r"C:\users", os.getlogin(), "desktop", "bbq.log")
#logging.basicConfig(filename=filename, encoding='utf-8', level=logging.DEBUG)
#logging.info("First imports done.")

# Test to see if we need to show a splash screen.
# If the splash is enabled (and we are not the application fork),
# then show a splash screen and relaunch the same application
# except as the application fork.

if __name__ == "__main__":
    AppFN = sys.argv[0]
    if SHOW_SPLASH and (len(sys.argv) == 1) and AppFN.endswith(".exe"):
        #logging.info("Will show splash screen")
        App = wx.App()

        # Get the Path of the splash screen
        real_path = os.path.realpath(__file__)

        frame = AS.AdvancedSplash(None,
                                  bitmap = wx.Bitmap(os.path.dirname(real_path)
                                           + r"\other\splash.png",wx.BITMAP_TYPE_PNG),
                                  timeout = 5000,
                                  agwStyle = AS.AS_TIMEOUT|AS.AS_CENTER_ON_PARENT|AS.AS_SHADOW_BITMAP,
                                  shadowcolour = wx.RED)

        os.spawnl(os.P_NOWAIT,
                  AppFN,
                  '"%s"' % AppFN.replace('"', r'\"'),
                  "NO_SPLASH")

        App.MainLoop()
        sys.exit()
    #else:
    #    logging.info("Will NOT show splash screen")

#########################################################################################
# BBQ actual starts here ################################################################
#########################################################################################

#logging.info("Start second batch of imports")
import importlib
import multiprocessing
import numpy as np
import pandas as pd
import zipfile as zf
import json as js
#from pathlib import Path
import shutil
import threading
import datetime
import csv
import wx.adv
import wx.xrc
import wx.aui
# required to open bbq_manual.pdf -> via system's standard PDF viewer
import subprocess
import ast

# Import my custom libraries
import lib_messageboxes as msg
import lib_colourscheme as cs
import lib_dbconnection as dbc
import lib_progressdialog as prog
from lib_custombuttons import CustomBitmapButton, DBConnButton
from lib_datafunctions import import_string_to_list
# Import panels for notebook
import lib_tools as tools
import lib_editor as we # Workflow Editor
import panel_Home as Home
#logging.info("Finish second batch of imports")

####################################################################################
##                                                                                ##
##    ##    ##   ####   ##  ##  ##    ######  #####    ####   ##    ##  ######    ##
##    ###  ###  ##  ##  ##  ### ##    ##      ##  ##  ##  ##  ###  ###  ##        ##
##    ########  ######  ##  ######    ####    #####   ######  ########  ####      ##
##    ## ## ##  ##  ##  ##  ## ###    ##      ##  ##  ##  ##  ## ## ##  ##        ##
##    ##    ##  ##  ##  ##  ##  ##    ##      ##  ##  ##  ##  ##    ##  ######    ##
##                                                                                ##
####################################################################################

class frm_Main (wx.Frame):

    """
    Main application window.
    Based on wx.Frame class
    """

    def __init__(self, parent, titlebar = True):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
        """
        #logging.info("Initialising main wx.Frame")
        wx.Frame.__init__ (self, parent, id = wx.ID_ANY, title = u"BBQ",
                           pos = wx.DefaultPosition, size = wx.Size(1380,768),
                           style = wx.TAB_TRAVERSAL|wx.RESIZE_BORDER)

        # Delete BBQ's temp directory if for any reason BBQ was previously
        # exited incorrectly and it still exists.
        self.HomePath = os.path.expanduser("~")
        #logging.info("Homepath: " + self.HomePath )
        self.delete_temp_directory()
        #logging.info("Deleted Temp Directory")

        # Set default colours
        self.clr_Dark = cs.BgUltraDark
        self.clr_Medium = cs.BgMediumDark
        self.clr_HeaderText = cs.White

        # Set useful paths (locations of image files)
        self.dir_Path = os.path.dirname(os.path.realpath(__file__))
        #logging.info("Found path of bbq.py file")
        self.str_ButtonPath = self.dir_Path + r"\buttons"
        self.str_MenuButtonPath = self.str_ButtonPath + r"\sidebar"
        self.str_TitleButtonsPath = self.str_ButtonPath + r"\titlebar"
        self.str_OtherPath = self.dir_Path + r"\other"
        self.version = {}
        version_path = self.dir_Path + r"\bbq.ver"
        version_file = open(version_path, mode= "r")
        self.version["build"] = version_file.readline().rstrip()
        self.version["date"] = version_file.readline().rstrip()
        self.version["time"] = version_file.readline().rstrip()
        
        # Set Application Icon and Taskbar Icon
        self.BBQIcon = wx.Icon(self.dir_Path + r"\bbq.ico", wx.BITMAP_TYPE_ANY)
        self.SetIcon(self.BBQIcon)
        self.icn_Taskbar = wx.adv.TaskBarIcon()
        self.icn_Taskbar.SetIcon(self.BBQIcon,
                                 tooltip="BBQ - Biochemical and Biophysical assay data analysis")

        # Find all assays:
        self.assays, self.assay_categories = self.find_assays()

        self.ProjectTab = None
        self.db_connection = None
        
        # Required for window dragging:
        # Functions for window dragging taken from wxPython documentation:
        # https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
        self.delta = wx.Point(0,0)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        # Unused other than for window size changing by dragging bottom right corner
        if titlebar == True:
            self.m_statusBar1 = self.CreateStatusBar(1, wx.STB_SIZEGRIP, wx.ID_ANY)

        self.szr_Main = wx.BoxSizer(wx.HORIZONTAL)


         #### # ####  #####   ####   ###  ####    #   # ##### #   # #   #
        #     # #   # #       #   # #   # #   #   ## ## #     ##  # #   #
         ###  # #   # ###     ####  ##### ####    ##### ###   ##### #   #
            # # #   # #       #   # #   # #   #   # # # #     #  ## #   #
        ####  # ####  #####   ####  #   # #   #   #   # ##### #   #  ###  ###############

        self.pnl_Menu = wx.Panel(self)
        self.pnl_Menu.SetForegroundColour(self.clr_HeaderText)
        self.pnl_Menu.SetBackgroundColour(self.clr_Dark)
        self.szr_Menu = wx.BoxSizer(wx.VERTICAL)
        self.szr_Menu.Add((0, 150), 0, wx.EXPAND, 0)
        self.dic_SidebarButtonGroup = {}
        self.dic_Tabnames = {}
        # Home Button
        self.btn_Home = CustomBitmapButton(self.pnl_Menu,
                                           name = u"Home",
                                           index = 0,
                                           size = (150,50),
                                           pathaddendum = u"sidebar")
        self.dic_SidebarButtonGroup["Home"] = self.btn_Home
        self.btn_Home.IsCurrent(True)
        self.dic_Tabnames["Home"] = self.set_home_text
        self.szr_Menu.Add(self.btn_Home, 0, wx.ALL, 0)
        # New Button
        self.btn_New = CustomBitmapButton(self.pnl_Menu,
                                          name = u"New",
                                          index = 1,
                                          size = (150,50),
                                          pathaddendum = u"sidebar")
        self.dic_SidebarButtonGroup["New"] = self.btn_New
        self.dic_Tabnames["New"] = u"New Project"
        self.szr_Menu.Add(self.btn_New, 0, wx.ALL, 0)
        # Open Button
        self.btn_Open = CustomBitmapButton(self.pnl_Menu,
                                           name = u"Open",
                                           index = 2,
                                           size = (150,50),
                                           pathaddendum = u"sidebar")
        self.dic_SidebarButtonGroup["Open"] = self.btn_Open
        self.szr_Menu.Add(self.btn_Open, 0, wx.ALL, 0)
        # ToolsButton
        self.btn_Tools = CustomBitmapButton(self.pnl_Menu,
                                            name = u"Tools",
                                            index = 3,
                                            size = (150,50),
                                            pathaddendum = u"sidebar")
        self.dic_SidebarButtonGroup["Tools"] = self.btn_Tools
        self.dic_Tabnames["Tools"] = u"Tools"
        self.szr_Menu.Add(self.btn_Tools, 0, wx.ALL, 0)
        # Divider
        self.m_staticline5 = wx.StaticLine(self.pnl_Menu, style = wx.LI_HORIZONTAL)
        self.szr_Menu.Add(self.m_staticline5, 0, wx.EXPAND|wx.ALL, 5)
        # Btn Current
        self.btn_Current = CustomBitmapButton(self.pnl_Menu,
                                              name = u"Current",
                                              index = 4,
                                              size = (150,50),
                                              pathaddendum = u"sidebar")
        self.btn_Current.Enable(False)
        self.dic_SidebarButtonGroup["Current"] = self.btn_Current
        self.dic_Tabnames["Current"] = self.WriteProjectTabTitle
        self.szr_Menu.Add(self.btn_Current, 0, wx.ALL, 0)
        self.szr_Menu.Add((150,-1), -1, wx.ALL,0)
        # Database Connection
        self.btn_DBConnect = DBConnButton(self.pnl_Menu)
        self.btn_DBConnect.is_connected(False)
        self.szr_Menu.Add(self.btn_DBConnect, 0, wx.ALL, 0)
        # Help
        self.btn_Help = CustomBitmapButton(self.pnl_Menu,
                                           name = u"Help",
                                           index = 5,
                                           size = (150,50),
                                           pathaddendum = u"sidebar")
        self.btn_Help.Enable(True)
        self.szr_Menu.Add(self.btn_Help, 0, wx.ALL, 0)
        # Version
        self.lbl_Version = wx.StaticText(self.pnl_Menu,
                                         label = "Build: " + self.version["build"]
                                         + "\n" + self.version["date"]
                                         + "\n" + self.version["time"])
        self.szr_Menu.Add(self.lbl_Version, 0, wx.EXPAND, 0)
        self.pnl_Menu.SetSizer(self.szr_Menu)
        self.pnl_Menu.Layout()
        self.szr_Menu.Fit(self.pnl_Menu)
        self.szr_Main.Add(self.pnl_Menu, 0, wx.EXPAND |wx.ALL, 0)
        # END OF SIDE BAR MENU ##########################################################

        # WorkPane
        self.szr_WorkPane = wx.BoxSizer(wx.VERTICAL)

        ##### # ##### #     #####  ####   ###  ####
          #   #   #   #     #      #   # #   # #   #
          #   #   #   #     ###    ####  ##### ####
          #   #   #   #     #      #   # #   # #   #
          #   #   #   ##### #####  ####  #   # #   # ####################################
        if titlebar == True:
            self.szr_Titlebar = wx.BoxSizer(wx.HORIZONTAL)
            self.pnl_Titlebar = wx.Panel(self)
            self.pnl_Titlebar.SetBackgroundColour(cs.BgMediumDark)
            self.szr_InsideTitleBar = wx.BoxSizer(wx.HORIZONTAL)
            self.pnl_TitleBarText = wx.Panel(self.pnl_Titlebar)
            #self.szr_TitleBarText = wx.BoxSizer(wx.HORIZONTAL)
            #self.lbl_TitleBarText = wx.StaticText(self.pnl_TitleBarText, label = wx.EmptyString)
            #self.lbl_TitleBarText.Wrap(-1)
            #self.szr_TitleBarText.Add(self.lbl_TitleBarText, 1, wx.ALL, 5)
            #self.pnl_TitleBarText.SetSizer(self.szr_TitleBarText)
            self.pnl_TitleBarText.Layout()
            self.szr_InsideTitleBar.Add(self.pnl_TitleBarText, 1, wx.ALL|wx.EXPAND, 0)
            # btn_Minimise
            self.btn_Minimise = wx.BitmapButton(self.pnl_Titlebar,
                                                style = wx.BU_AUTODRAW|wx.BORDER_NONE)
            self.btn_Minimise.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                                + r"\btn_minimise.png",
                                                wx.BITMAP_TYPE_ANY))
            self.btn_Minimise.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_minimise_pressed.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.btn_Minimise.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_minimise_mouseover.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.btn_Minimise.SetMaxSize(wx.Size(46,34))
            self.szr_InsideTitleBar.Add(self.btn_Minimise, 0, wx.ALL, 0)
            # btn_Cascade
            self.btn_Cascade = wx.BitmapButton(self.pnl_Titlebar,
                                            style = wx.BU_AUTODRAW|wx.BORDER_NONE)
            self.btn_Cascade.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                                + r"\btn_cascade.png",
                                                wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_cascade_pressed.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_cascade_mouseover.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetMaxSize(wx.Size(46,34))
            self.szr_InsideTitleBar.Add(self.btn_Cascade, 0, wx.ALL, 0)
            # btn_Close
            self.btn_Close = wx.BitmapButton(self.pnl_Titlebar,
                                            style = wx.BU_AUTODRAW|wx.BORDER_NONE)
            self.btn_Close.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                            + r"\btn_close.png",
                                            wx.BITMAP_TYPE_ANY))
            self.btn_Close.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                    + r"\btn_close_pressed.png",
                                                    wx.BITMAP_TYPE_ANY))
            self.btn_Close.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                    + r"\btn_close_mouseover.png",
                                                    wx.BITMAP_TYPE_ANY))
            self.btn_Close.SetMaxSize(wx.Size(46,34))
            self.szr_InsideTitleBar.Add(self.btn_Close, 0, wx.ALL, 0)
            self.pnl_Titlebar.SetSizer(self.szr_InsideTitleBar)
            self.pnl_Titlebar.Layout()
            self.szr_InsideTitleBar.Fit(self.pnl_Titlebar)
            self.szr_Titlebar.Add(self.pnl_Titlebar, 1, wx.EXPAND |wx.ALL, 0)
            self.szr_WorkPane.Add(self.szr_Titlebar, 0, wx.EXPAND, 0)
            # END OF TITLE BAR ##############################################################

        #   # #####  ###  ####  ##### ####   ####
        #   # #     #   # #   # #     #   # #
        ##### ###   ##### #   # ###   ####   ###
        #   # #     #   # #   # #     #   #     #
        #   # ##### #   # ####  ##### #   # ####  #######################################
        #
        # Full name of assay or other title (e.g. "Tools" tab, "Settings" tab
        # (once implemented)) will be shown
        #
        self.szr_Header = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Header = wx.Panel(self, size = wx.Size(-1,70))
        self.pnl_Header.SetBackgroundColour(self.clr_Medium)
        self.pnl_Header.SetForegroundColour(self.clr_HeaderText)
        self.szr_Banner = wx.BoxSizer(wx.VERTICAL)
        self.szr_Banner.Add((0, -1), 0, wx.EXPAND, 5)
        self.lbl_Banner = wx.StaticText(self.pnl_Header, label = self.set_home_text())
        self.lbl_Banner.Wrap(-1)
        self.lbl_Banner.SetFont(wx.Font(25, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                        wx.FONTWEIGHT_NORMAL, False, wx.EmptyString))
        self.szr_Banner.Add(self.lbl_Banner, 0, wx.ALL, 15)
        self.pnl_Header.SetSizer(self.szr_Banner)
        self.pnl_Header.Layout()
        self.szr_Banner.Fit(self.pnl_Header)
        self.szr_Header.Add(self.pnl_Header, 1, wx.EXPAND, 0)
        self.szr_WorkPane.Add(self.szr_Header, 0, wx.EXPAND, 0)
        # END OF HEADER #################################################################

        #####  ###  ####   ####
          #   #   # #   # #
          #   ##### ####   ###
          #   #   # #   #     #
          #   #   # ####  ####  #########################################################

        self.szr_Book = wx.BoxSizer(wx.VERTICAL)
        self.sbk_WorkArea = wx.Simplebook(self)
        # Dictionary to hole page indices
        self.dic_WorkAreaPageIndices = {}

        self.str_Assays = os.path.join(self.dir_Path,"assays.csv")
        self.str_Pinned = os.path.join(self.HomePath,"bbq_pinned.csv")
        if os.path.isfile(self.str_Pinned) == True:
            csv_Pinned = list(csv.reader(open(self.str_Pinned,"r")))
            for assay in self.assays.index:
                if assay in csv_Pinned[0]:
                    self.assays.loc[assay,"Pinned"] = True
                else:
                    self.assays.loc[assay,"Pinned"] = False

        # "Home" Tab ####################################################################
        self.sbk_WorkArea.AddPage(page = Home.HomeScreen(self.sbk_WorkArea, self),
                                  text = u"Home")
        self.dic_WorkAreaPageIndices["Home"] = self.sbk_WorkArea.GetPageCount() - 1
        self.tab_Home = self.sbk_WorkArea.GetChildren()[0]

        # "New Project" tab #############################################################
        self.sbk_WorkArea.AddPage(page = Home.pnl_Projects(self.sbk_WorkArea, self),
                                  text = u"New")
        self.dic_WorkAreaPageIndices["New"] = self.sbk_WorkArea.GetPageCount() - 1

        # "Tools" tab ###################################################################
        self.pnl_Tools = wx.Panel(self.sbk_WorkArea)
        self.pnl_Tools.SetBackgroundColour(self.clr_Medium)
        self.pnl_Tools.SetForegroundColour(self.clr_HeaderText)
        self.szr_Tools = wx.BoxSizer(wx.VERTICAL)
        self.sbk_Tools = wx.Simplebook(self.pnl_Tools, size = wx.Size(-1,-1))
        self.szr_Tools.Add(self.sbk_Tools, 1, wx.EXPAND, 10)
        # Sub-tab for the buttons
        self.pnl_ToolSelection = wx.Panel(self.sbk_Tools)
        self.pnl_ToolSelection.SetBackgroundColour(self.clr_Medium)
        self.pnl_ToolSelection.SetForegroundColour(self.clr_HeaderText)
        self.szr_ToolSelection = wx.BoxSizer(wx.VERTICAL)
        self.szr_ToolsTransferFile = wx.BoxSizer(wx.VERTICAL)
        self.btn_WorkflowEditor = CustomBitmapButton(self.pnl_ToolSelection,
                                                     name = u"WorkflowEditor",
                                                     index = 0,
                                                     size = (260,50))
        self.szr_ToolsTransferFile.Add(self.btn_WorkflowEditor, 0, wx.ALL, 5)
        self.btn_CreateTransferFile = CustomBitmapButton(self.pnl_ToolSelection,
                                                         name = u"CreateTransfer",
                                                         index = 0,
                                                         size = (260,50))
        self.szr_ToolsTransferFile.Add(self.btn_CreateTransferFile, 0, wx.ALL, 5)
        self.btn_TransferFileProcessor = CustomBitmapButton(self.pnl_ToolSelection,
                                                            name = u"ProcessTransfer",
                                                            index = 0,
                                                            size = (260,50))
        self.szr_ToolsTransferFile.Add(self.btn_TransferFileProcessor, 0, wx.ALL, 5)
        self.btn_NanoDropReporter = CustomBitmapButton(self.pnl_ToolSelection,
                                                            name = u"NanoDropReporter",
                                                            index = 0,
                                                            size = (260,50))
        self.szr_ToolsTransferFile.Add(self.btn_NanoDropReporter, 0, wx.ALL, 5)
        self.szr_ToolSelection.Add(self.szr_ToolsTransferFile, 0, wx.ALL, 5)
        self.pnl_ToolSelection.SetSizer(self.szr_ToolSelection)
        self.pnl_ToolSelection.Layout()
        self.szr_ToolSelection.Fit(self.pnl_ToolSelection)
        self.sbk_Tools.ShowNewPage(self.pnl_ToolSelection)
        self.sbk_Tools.SetSelection(0)
        self.ActiveTool = None
        self.pnl_Tools.SetSizer(self.szr_Tools)
        self.pnl_Tools.Layout()
        self.szr_Tools.Fit(self.pnl_Tools)
        self.sbk_WorkArea.AddPage(page = self.pnl_Tools,
                                  text = u"Tools")
        self.dic_WorkAreaPageIndices["Tools"] = self.sbk_WorkArea.GetPageCount() - 1

        # Add notebook to szr_WorkPane
        self.szr_Book.Add(self.sbk_WorkArea, 1, wx.EXPAND|wx.ALL, 0)
        self.szr_WorkPane.Add(self.szr_Book, 1, wx.EXPAND, 0)

        self.szr_Main.Add(self.szr_WorkPane, 1, wx.EXPAND, 5)

        self.sbk_WorkArea.SetSelection(self.dic_WorkAreaPageIndices["Home"])

        # Finalising
        self.SetSizer(self.szr_Main)
        self.Layout()
        self.Centre(wx.BOTH)


        ###  # #  # ###  # #  #  ###
        #  # # ## # #  # # ## # #   
        ###  # # ## #  # # # ## # ##
        #  # # #  # #  # # #  # #  #
        ###  # #  # ###  # #  #  ##  ####################################################

        # Title bar
        if titlebar == True:
            self.btn_Close.Bind(wx.EVT_BUTTON, self.OnBtnClose)
            self.btn_Minimise.Bind(wx.EVT_BUTTON, self.OnBtnMinimise)
            self.btn_Cascade.Bind(wx.EVT_BUTTON, self.OnBtnCascade)
            self.pnl_TitleBarText.Bind(wx.EVT_LEFT_DCLICK, self.OnBtnCascade)

        # Side Panel Menu
        self.btn_Home.Bind(wx.EVT_BUTTON, self.on_sidebar_button)
        self.btn_New.Bind(wx.EVT_BUTTON, self.on_sidebar_button)
        self.btn_Open.Bind(wx.EVT_BUTTON, self.on_btn_open)
        self.btn_Tools.Bind(wx.EVT_BUTTON, self.on_sidebar_button)
        self.btn_Current.Bind(wx.EVT_BUTTON, self.on_sidebar_button)
        self.btn_DBConnect.Bind(wx.EVT_BUTTON, self.toggle_db_connection)
        self.btn_Help.Bind(wx.EVT_BUTTON, self.on_btn_help)

        # Tools Tab
        self.btn_WorkflowEditor.Bind(wx.EVT_BUTTON, self.launch_editor)
        self.btn_CreateTransferFile.Bind(wx.EVT_BUTTON, self.ToolTransferFileMaker)
        self.btn_TransferFileProcessor.Bind(wx.EVT_BUTTON, self.ToolTransferFileProcessor)
        self.btn_NanoDropReporter.Bind(wx.EVT_BUTTON, self.ToolNanoDropReporter)

        # New Project buttons
        # Dynamically bound

        # Closing
        self.Bind(wx.EVT_CLOSE, self.OnBtnClose)

        self.Show()
        #logging.info("Main bits of UI have been built.")

    def __del__(self):
        pass

    ##### #   # ##### #   # #####    #   #  ###  #   # ####  #     ##### ####   ####
    #     #   # #     ##  #   #      #   # #   # ##  # #   # #     #     #   # #
    ###   #   # ###   #####   #      ##### ##### ##### #   # #     ###   ####   ###
    #      # #  #     #  ##   #      #   # #   # #  ## #   # #     #     #   #     #
    #####   #   ##### #   #   #      #   # #   # #   # ####  ##### ##### #   # ####  ####

    def OnBtnClose(self, event):
        """
        Event handler.
        Performs checks before closing program, then deletes
        temp directory, then closes program.
        """
        if self.sbk_WorkArea.GetPageCount() > 3:
            # If more than four pages are in simplebook, then
            # an analysis is open/in progress.
            bol_AllowCancel = msg.query_close_program()
        else:
            bol_AllowCancel = True
        if bol_AllowCancel == True:
            # Clean up, then exit
            if not self.db_connection is None:
                self.db_connection.close()
            self.delete_temp_directory()
            self.icn_Taskbar.RemoveIcon()
            wx.Exit()

    def OnBtnMinimise(self, event):
        """
        Event handler. Minimises window
        """
        self.Iconize(True)

    def OnBtnCascade(self,event):
        """
        Event handler.  Toggles between maximised and cascading window.
        Image files for button get changed to reflect this. Follows
        standard Windows design.
        """
        if self.IsMaximized() == False:
            # Change button
            self.btn_Cascade.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                                 + r"\btn_cascade.png",
                                                 wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_cascade_pressed.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_cascade_mouseover.png",
                                                        wx.BITMAP_TYPE_ANY))
            # Maximize
            self.SetWindowStyle(wx.DEFAULT_FRAME_STYLE)
            self.Maximize(True)
            self.SetWindowStyle(wx.RESIZE_BORDER)
            # Unbind functions for window dragging
            self.pnl_TitleBarText.Unbind(wx.EVT_LEFT_DOWN)
            self.Unbind(wx.EVT_LEFT_UP)
            self.Unbind(wx.EVT_MOTION)
        else:
            # Change button
            self.btn_Cascade.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                                 + r"\btn_maximize.png",
                                                 wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_maximize_pressed.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_maximize_mouseover.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.SetWindowStyle(wx.TAB_TRAVERSAL)
            self.Maximize(False)
            # Bind functions for window dragging:
            self.pnl_TitleBarText.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
            self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
            self.Bind(wx.EVT_MOTION, self.on_mouse_move)
            self.dragging = False

    # The following three function are taken from a tutorial on the wxPython Wiki:
    # https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
    # They have been modified if and where appropriate.

    def on_mouse_move(self, event):
        """
        Event handler to drag the window.
        """
        if self.dragging == True:
            if event.Dragging() and event.LeftIsDown():
                x,y = self.ClientToScreen(event.GetPosition())
                newPos = (x - self.delta[0], y - self.delta[1])
                self.Move(newPos)

    def on_left_down(self, event):
        """
        Event handler to capture mouse and get window position for
        window dragging.
        """
        # Important change from tutorial code: Added offset for dx.
        # It is not the whole frame that has the function bound to it,
        # only the pnl_TitleBarText. Since the menu panel next to it 
        # s 150px wide, this offset needs to be accounted for.
        self.CaptureMouse()
        x, y = self.ClientToScreen(event.GetPosition())
        originx, originy = self.GetPosition()
        dx = x - originx + 150 # Offset for menu panel width.
        dy = y - originy
        self.delta = [dx, dy]
        self.dragging = True

    def on_left_up(self, event):
        """
        Releases capture if left mouse button is released.
        """
        if self.HasCapture():
            self.ReleaseMouse()
        self.dragging = False
    
    def on_sidebar_button(self, event, button = None):
        """
        Event handler.
        Changes selection of sbk_WorkArea simplebood, deactivates
        all other buttons in sidebar menu, and Disables/Enables button
        for current project, if there is one.

        Arguments:
            event -> wx event.
            button -> string. Optional. If function is not called from
                      an event, provide the type of button ("Home",
                      "New", etc.) the pressing of which is simulated.
        """

        # Dictionary dic_SidebarButtonGroup must be populated with all
        # buttons on the sidebar menu. 
        # Dictionary dic_Tabnames must be populated with the names to be displayed.
        # button is included as keyword argument in case you might want to use
        # this function other than as an event handler.
        if button == None:
            button = event.GetEventObject().name
        self.sbk_WorkArea.ChangeSelection(self.dic_WorkAreaPageIndices[button])
        # There might be a method or a string in the dictionary:
        try: self.lbl_Banner.SetLabel(self.dic_Tabnames[button]())
        except: self.lbl_Banner.SetLabel(self.dic_Tabnames[button])
        self.sbk_WorkArea.Update()
        for key in self.dic_SidebarButtonGroup.keys():
            if not self.dic_SidebarButtonGroup[key].name == button:
                self.dic_SidebarButtonGroup[key].IsCurrent(False)
            else:
                self.dic_SidebarButtonGroup[key].IsCurrent(True)
        if not self.ProjectTab == None:
            self.btn_Current.Enable(True)
        else:
            self.btn_Current.Enable(False)

    def on_btn_open(self, event):
        """
        Event handler for opening a saved project.
        """
        if self.ActiveProject() == True:
            return None
        with wx.FileDialog(self, "Open BBQ file", wildcard="BBQ files (*.bbq)|*.bbq",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return None     # the user changed their mind
            # Proceed loading the file chosen by the user
            self.open_project(fileDialog.GetPath(), fileDialog.GetFilename())

    def on_btn_help(self, event):
        """
        Event handler to display user manual.
        """
        pdfpath = os.path.join(self.dir_Path, "bbq_manual.pdf")
        subprocess.Popen([pdfpath], shell=True)

    def launch_editor(self, event):
        """
        Event handler to launch workflow editor
        """
        self.sbk_Tools.ShowNewPage(we.WorkflowEditor(self.sbk_Tools, self))
        self.ActiveTool = self.sbk_Tools.GetPageCount()-1
        self.sbk_Tools.SetSelection(self.ActiveTool)
        self.lbl_Banner.SetLabel("Workflow Editor")

    def ToolTransferFileMaker(self, event):
        """
        Event handler to launch tool Transfer File Maker
        """
        self.sbk_Tools.ShowNewPage(tools.panel_TransferFileMaker(self.sbk_Tools, self))
        self.ActiveTool = self.sbk_Tools.GetPageCount()-1
        self.sbk_Tools.SetSelection(self.ActiveTool)
        self.lbl_Banner.SetLabel("Transfer file maker")

    def ToolTransferFileProcessor(self, event):
        """
        Event handler to launch tool Transfer File Processor
        """
        self.sbk_Tools.ShowNewPage(tools.panel_TransferFileProcessor(self.sbk_Tools, self))
        self.ActiveTool = self.sbk_Tools.GetPageCount()-1
        self.sbk_Tools.SetSelection(self.ActiveTool)
        self.lbl_Banner.SetLabel("Process a transfer file")

    def ToolNanoDropReporter(self, event):
        """
        Event handler to launch tool NanoDrop Reporter
        """
        self.sbk_Tools.ShowNewPage(tools.panel_NanoDropReporter(self.sbk_Tools, self))
        self.ActiveTool = self.sbk_Tools.GetPageCount()-1
        self.sbk_Tools.SetSelection(self.ActiveTool)
        self.lbl_Banner.SetLabel("Process NanoDrop report")

    def CloseActiveTool(self, event):
        """
        Event handler. Closes currently active tool.
        """
        self.sbk_Tools.SetSelection(0)
        pages = self.sbk_Tools.GetChildren()
        panel = pages[self.ActiveTool]
        del(panel)
        self.ActiveTool = None
        self.lbl_Banner.SetLabel("Tools")

    def Cancel(self, event):
        """
        Cancels a project by deleting the corresponding project tab.
        """
        self.Freeze()
        if msg.query_discard_changes() == True:
            self.ProjectTab.ButtonBar.EnableButtons(False)
            self.sbk_WorkArea.DeletePage(self.ProjectTab.Index)
            self.ProjectTab = None
            self.on_sidebar_button(None, button="Home")
            self.sbk_WorkArea.SetSelection(self.dic_WorkAreaPageIndices["Home"])
        self.Thaw()

    # END OF EVENT HANDLERS #############################################################

    def set_home_text(self):
        """
        Sets the welcome text on top of the home panel based on the time of day.
        """
        #return "Good morning"
        hour = int(str(datetime.datetime.now())[10:13])
        if hour < 7:
            return "It's a bit early, isn't it?"
        elif hour >= 7 and hour < 12:
            return "Good morning"
        elif hour >= 12 and hour < 13:
            return "Lunchtime?"
        elif hour >= 13 and hour < 17:
            return "Good afternoon"
        elif hour >= 17 and hour < 20:
            return "Good evening"
        elif hour >= 20:
            return "It's a bit late, isn't it?"

    def WriteProjectTabTitle(self):
        """
        Returns title of project tab.
        """
        if self.ProjectTab is not None:
            return self.ProjectTab.title
        else:
            return "Fnord"

    def AnalyseData(self, event = None, tabname = None):
        """
        Freezes the main window and creates the progress dialog.
        Then calls the process_data() function of the current project
        panel as a new thread. The process_data() function unfreezes
        the main window once the analysis is complete.
        """
        if self.ProjectTab is not None:
        #if tabname is None and event is not None:
        #    ProjectTab = event.GetEventObject().parent.tabname
        #else:
        #    ProjectTab = tabname
            self.Freeze() # Thawing is handled when dlg_Progess gets closed
            self.dlg_progress = prog.ProgressDialog(self)
            self.dlg_progress.Show()
            self.dlg_progress.btn_Close.Enable(False)
            self.thd_Analysis = threading.Thread(target=self.ProjectTab.process_data,
                                                 args=(self.dlg_progress,),
                                                 daemon=True)
            self.thd_Analysis.start()

        else:
            return None

    def delete_temp_directory(self):
        """
        Checks whether the temporary directory exists.
        If so, it gets deleted so that we're not running
        into problems with it existing and being unable to
        be overwritten later.
        """
        # Check whether temporary directory exists. if so, delete it.
        str_TempDir = os.path.join(self.HomePath,"bbqtempdir")
        if os.path.isdir(str_TempDir) == True:
            shutil.rmtree(str_TempDir)

     ###  ####  ##### #   #    ###  #   # ####     ####  ###  #   # #####
    #   # #   # #     ##  #   #   # ##  # #   #   #     #   # #   # #
    #   # ####  ###   #####   ##### ##### #   #    ###  ##### #   # ###
    #   # #     #     #  ##   #   # #  ## #   #       # #   #  # #  #
     ###  #     ##### #   #   #   # #   # ####    ####  #   #   #   ##### ###############

    def open_project(self, str_FilePath, str_FileName):
        """
        Opens saved project.

        Arguments:
            str_FilePath -> string. Full path of project file.
            str_FileName -> string. File name only of project file.
        """

        self.Freeze()
         # Check whether temporary directory exists. if so, delete and make fresh
        str_TempDir = os.path.join(self.HomePath,"bbqtempdir")
        if os.path.isdir(str_TempDir) == True:
            shutil.rmtree(str_TempDir)
        os.mkdir(str_TempDir)
        # Extract saved file to temporary directory
        with zf.ZipFile(str_FilePath, "r") as zip:
            zip.extractall(str_TempDir)
        # Read details.csv
        dfr_Details = pd.read_csv(str_TempDir + r"\details.csv", sep = ",",
                                  header=0, index_col=0, engine="python")
        # Ensure backwards compatibility for details. Previously, was
        # just a list, from version 1.0.8 onwards a full dataframe
        if dfr_Details.index[0] == 0: # we are dealing with the old list style!
            dfr_Details.set_index(pd.Index(["AssayType","AssayCategory","PurificationID",
                                            "ProteinConcentration","PeptideID",
                                            "PeptideConcentration","Solvent",
                                            "SolventConcentration","Buffer","ELN",
                                            "AssayVolume","DataFileExtension",
                                            "SampleSource","Device","Date"]),
                                            inplace=True)
            dfr_Details = dfr_Details.rename(columns={"AssayDetails":"Value"})
            if dfr_Details.iloc[1,0] == "single_dose":
                dfr_Details.loc["Shorthand","Value"] = "EPSD"
            elif dfr_Details.iloc[1,0] == "dose_response":
                dfr_Details.loc["Shorthand","Value"] = "EPDR"
            elif dfr_Details.iloc[1,0] == "dose_response_time_course":
                dfr_Details.loc["Shorthand","Value"] = "DRTC"
            elif dfr_Details.iloc[1,0] == "thermal_shift":
                if dfr_Details.iloc[0,0] == "nanoDSF":
                    dfr_Details.loc["Shorthand","Value"] = "NDSF"
                else:
                    dfr_Details.loc["Shorthand","Value"] = "DSF"
            elif dfr_Details.iloc[1,0] == "rate":
                dfr_Details.loc["Shorthand","Value"] = "RATE"
        # Convert to dictionary.
        try: 
            details = dfr_Details.Value.to_dict()
        except:
            details = dfr_Details[dfr_Details.columns[0]].to_dict()
        # Ensure all numbers are numbers! (integers = integers, floats = floats)
        for key in details.keys():
            # Convert strings to numbers
            if type(details[key]) == str and details[key].count("-") < 2:
                if details[key].isdigit():
                    # destinguish between integers and floating point numbers:
                    if details[key].find(".") > 0:
                        details[key] = float(details[key])
                    else:
                        details[key] = int(details[key])
            if str(details[key])[0] == "{":
                details[key] = ast.literal_eval(details[key])

        # start new project based on details["Shorthand"] (was =lst_Details[0])
        self.new_project(None, details["Shorthand"])
        # Hand over loaded data to populate tab
        self.ProjectTab.populate_from_file(str_TempDir, details)
        # Display file name on header
        self.ProjectTab.ButtonBar.lbl_Filename.SetLabel(str_FilePath)
        # Update py files:
        int_Slash = str(str_FilePath).rfind(chr(92))+1
        str_FileName = str_FilePath[int_Slash:]
        self.tab_Home.UpdateRecent(str_FilePath,
                                   str_FileName,
                                   details["AssayCategory"],
                                   details["Shorthand"])
        self.Thaw()

    def save_file(self, event = None, tabname = None, saveas = False):
        """
        Saves current project to .bbq archive.

        Arguments:
            event -> wx event
            tabname -> string. part of wx app that holds the actual
                       project data.
            saveas -> boolean. Sets behaviour to typical "save as"
                      option, i.e. prompting user to select new
                      location and file name.
        """
        
        if tabname == None:
            tabname = self.ProjectTab
        # Make sure an analysis has been performed and the dataframe has been constructed properly
        if tabname.assay_data.shape[0] > 0:
            # Check if the project has been saved previously or "save as" has been selected.
            # If so, show file dialog:
            if tabname.bol_PreviouslySaved == False or saveas == True:
                with wx.FileDialog(tabname, "Save project file",
                                   wildcard = "BBQ files (*.bbq)|*.bbq",
                                   style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT) as fileDialog:
                    # Exit via returning nothing if the user changed their mind
                    if fileDialog.ShowModal() == wx.ID_CANCEL:
                        return
                    str_SaveFilePath = fileDialog.GetPath()
                    # Prevent duplication of file extension
                    if str_SaveFilePath.find(".bbq") == -1:
                        str_SaveFilePath = str_SaveFilePath + ".bbq"
                    # Update file path property
                    tabname.paths["SaveFile"] = str_SaveFilePath
                    # Get file name:
                    str_FileName = fileDialog.GetFilename()
                    if str_FileName.find(".bbq") == -1:
                        str_FileName = str_FileName + ".bbq"
            else:
                str_FileName = tabname.paths["SaveFile"]
                int_Slash = str(str_FileName).rfind(chr(92))+1
                str_FileName = str_FileName[int_Slash:]
            # Make sure assay detail variables are updated
            tabname.save_details(bol_FromTabChange = False)
            # Prep boolean variables as list to hand over
            lst_Boolean = [tabname.bol_AssayDetailsChanged, tabname.bol_AssayDetailsCompleted,
                           tabname.bol_DataFilesAssigned, tabname.bol_DataFilesUpdated,
                           tabname.bol_DataAnalysed, tabname.bol_ELNPlotsDrawn,
                           tabname.bol_ExportPopulated, tabname.bol_ResultsDrawn,
                           tabname.bol_ReviewsDrawn, tabname.bol_TransferLoaded,
                           tabname.bol_GlobalLayout, tabname.bol_PlateID,
                           tabname.bol_PlateMapPopulated]
            # Prep file paths to hand over
            dfr_Paths = pd.DataFrame([tabname.paths["TransferPath"],
                                      tabname.paths["Data"]],
                                     columns=["Path"])
            # Hand everything over
            saved = self.write_to_archive(tabname.paths["SaveFile"], 
                                          tabname.assay_data,
                                          tabname.details,
                                          lst_Boolean,
                                          dfr_Paths)
            if saved == True:
                self.ProjectTab.ButtonBar.lbl_Filename.SetLabel(tabname.paths["SaveFile"])
                # Let the program know that the file has been saved previously
                # -> Affects behaviour of "Save" button.
                tabname.bol_PreviouslySaved = True
                # Add file to recent files list
                self.tab_Home.UpdateRecent(tabname.paths["SaveFile"],
                                           str_FileName,
                                           tabname.details["AssayCategory"],
                                           tabname.details["Shorthand"])
                msg.info_save_success()
            else:
                msg.warn_permission_denied()
        else:
            msg.warn_save_error_no_analysis()

    def write_to_archive(self, str_SaveFilePath, assay_data,
                         details, lst_Boolean, dfr_Paths):
        """
        Writes the dataframes and lists into csv files and
        packages them into a zip archive.
        
        Arguments:
            str_SaveFilePath -> string. path of saved file
            assay_data -> pandas dataframe holding all assay data
            details -> dictionary. Meta data of experiment
            lst_Boolean -> list. Boolean variables defining the
                           state/behaviour of the project (e.g. has a
                           certain tab been populated, has the file
                           been saved before...)
            dfr_Paths -> pandas dataframe. Paths of all files provided
                         by the user.

        Returns True on succesful save.
        """
        # Separated from main  saving function to simplify code for human readability.
        
        try:
            zip_BBQ = zf.ZipFile(str_SaveFilePath, "w")
        except:
            return False

        str_TempDir = os.path.join(self.HomePath,"bbqtempdir")
        # Check whether temporary directory exists. if so, delete and make fresh
        if os.path.isdir(str_TempDir) == True:
            shutil.rmtree(str_TempDir)
            os.mkdir(str_TempDir)
        else:
            os.mkdir(str_TempDir)
        # Paths
        dfr_Paths.to_csv(str_TempDir + r"\paths.csv")
        # .write(name_of_file_to_write, arcname=name_to_give_file_in_archive, other arguments)
        # file names contain path. for arcname, use relative paths inside archive.
        zip_BBQ.write(str_TempDir + r"\paths.csv", arcname="paths.csv")
        # Assay details
        dfr_Details = pd.DataFrame.from_dict(details, orient = "index")
        dfr_Details.columns = ["Value"]
        dfr_Details.to_csv(str_TempDir + r"\details.csv")
        zip_BBQ.write(str_TempDir + r"\details.csv", arcname="details.csv")
        # Boolean status variables
        dfr_Boolean = pd.DataFrame(lst_Boolean,columns=["BooleanVariables"])
        dfr_Boolean.to_csv(str_TempDir + r"\boolean.csv")
        zip_BBQ.write(str_TempDir + r"\boolean.csv", arcname="boolean.csv")
        # Make dataframe with fields of dataframe that do not hold other dataframes
        if details["AssayType"] == "nanoDSF":
            str_WellsOrCapillaries = "Capillaries"
        else:
            str_WellsOrCapillaries = "Wells"
        dfr_Meta = assay_data[["Destination",
                               str_WellsOrCapillaries,
                               "DataFile",
                               "PlateID"]]
        dfr_Meta.to_csv(str_TempDir + r"\meta.csv")
        zip_BBQ.write(str_TempDir + r"\meta.csv", arcname="meta.csv")
        # Save all the fields that hold dataframes in separate folders
        # (one folder per plate/set of capillaries)
        for plate in assay_data.index:
            str_Subdirectory = os.path.join(str_TempDir,
                                            assay_data.loc[plate,"Destination"])
            os.mkdir(str_Subdirectory)
            str_Subdirectory_relative = assay_data.loc[plate,"Destination"] + chr(92)
            # Samples
            assay_data.loc[plate,"Samples"].to_csv(str_Subdirectory + r"\samples.csv")
            zip_BBQ.write(str_Subdirectory + r"\samples.csv",
                          arcname=str_Subdirectory_relative+"samples.csv")
            # Raw data
            assay_data.loc[plate,"RawData"].to_csv(str_Subdirectory + r"\rawdata.csv")
            zip_BBQ.write(str_Subdirectory + r"\rawdata.csv",
                          arcname=str_Subdirectory_relative+"rawdata.csv")
            # Processed data
            assay_data.loc[plate,"Processed"].to_csv(str_Subdirectory + r"\processed.csv")
            zip_BBQ.write(str_Subdirectory + r"\processed.csv",
                          arcname=str_Subdirectory_relative+"processed.csv")
            # Plate layouts
            dfr_Layout = assay_data.loc[plate,"Layout"]
            dfr_Layout.to_csv(str_Subdirectory + r"\layout.csv")
            zip_BBQ.write(str_Subdirectory + r"\layout.csv",
                          arcname=str_Subdirectory_relative+"layout.csv")
            # List of reference wells
            assay_data.loc[plate,"References"].to_csv(str_Subdirectory + r"\references.csv")
            zip_BBQ.write(str_Subdirectory + r"\references.csv",
                          arcname=str_Subdirectory_relative+"references.csv")
        zip_BBQ.close()
        # Remove all the temporary files
        shutil.rmtree(str_TempDir)
        return True

    def find_assays(self):
        """
        Scans assay directory and lists all valid assay workflow definitions.
        Returns:
            - pandas dataframe with metadata for assay, index is assay
              shorthand codes:
                    - full assay name
                    - assay subdirectory
                    - categories in assay (if subcategories exist)
                    - is assay pinned to faviourites.
            - dictionaries referencing assay workflow's .py file.
        """
        # Initialise lists
        directories = []
        lst_Shorthand = []
        full_name = []
        main_category = []
        sec_category = []
        main_category = []
        pinned = []
        modules = []
        as_categories = {}
        # Read all elements in assay path and check which ones are files
        for element in os.listdir(os.path.join(self.dir_Path,"assays")):
            if "as_" in element:
                str_Subdirectory = os.path.join(self.dir_Path,"assays",element)
                if os.path.isdir(str_Subdirectory) == True:
                    json_path = os.path.join(str_Subdirectory,"assay.json")
                    if os.path.exists(json_path) == True:
                        assay_json = js.load(open(json_path, "r"))
                        assay_meta = assay_json["Meta"]
                        directories.append(str_Subdirectory)
                        shorthand = assay_meta["Shorthand"]
                        lst_Shorthand.append(shorthand) # Shorthand is in row 0
                        full_name.append(assay_meta["FullName"]) # Full name is in row 1
                        main_cat = assay_meta["MainCategory"]
                        main_category.append(main_cat)
                        sec_category.append(assay_meta["SecondaryCategory"])
                        pinned.append(False)
                        # Import assay module
                        module = f"assays.as_{shorthand}.{shorthand}"
                        modules.append(importlib.import_module(module))
                        if main_cat in as_categories.keys():
                            sec_cat = assay_meta["SecondaryCategory"]
                            if sec_cat not in as_categories[main_cat].keys():
                                as_categories[main_cat]["SecondaryCategory"].append(sec_cat)
                        else:
                            as_categories[main_cat] = {} 
                            as_categories[main_cat]["SecondaryCategory"] = [assay_meta["SecondaryCategory"]]

        assays = pd.DataFrame(index=lst_Shorthand,
                                  data={"FullName":full_name,
                                        "Subdirectory":directories,
                                        "MainCategory":main_category,
                                        "SecondaryCategory":sec_category,
                                        "Pinned":pinned,
                                        "Module":modules})

        return assays, as_categories

    # New Analyses
    def ActiveProject(self):
        """
        Performs check to see if there is an active project before
        starting a new one. Prompts user to confirm cancelling the
        project, if there is one,

        Returns True if there is a project.
        """
        if not self.ProjectTab == None:
            message = wx.MessageBox(
                    "You cannot start a new project before closing the current one. "
                    + "Do you want to close it?",
                    caption = "No can do!",
                    style = wx.YES_NO|wx.ICON_WARNING)
            # User clicked "Yes" -> message returns 2
            if message == 2:
                self.Freeze()
                # Double check by asking the user if they want to discard any changes
                if msg.query_discard_changes() == True:
                    # Delete corresponding page in simplebook and re-set buttons
                    self.ProjectTab.ButtonBar.EnableButtons(False)
                    self.sbk_WorkArea.DeletePage(self.ProjectTab.Index)
                    self.ProjectTab = None
                    self.sbk_WorkArea.SetSelection(self.dic_WorkAreaPageIndices["New"])
                    bol_Cancelled = True
                else:
                    bol_Cancelled = False
                self.Thaw()
            # User clicked "No" -> message returns 8
            elif message == 8:
                bol_Cancelled = False
            if bol_Cancelled == True:
                return False
            else:
                return True
        else:
            return False

    def new_project(self, event, shorthand = None):
        """
        Starts a new Assay project.
        
        Arguments:
            event -> wx event. If called as an event handler,
                     button will have the assay type as shorthand
                     assigned to it's name property.
            shorthand -> string. If not called as an event handler,
                         provide shorthand code for assay type here.
        """
        if shorthand == None:
            shorthand = event.GetEventObject().name
        self.sbk_WorkArea.Update()
        if self.ActiveProject() == False:
            self.Freeze()
            self.sbk_WorkArea.ShowNewPage(self.assays.loc[shorthand,"Module"].pnl_Project(self))
            self.dic_WorkAreaPageIndices["Current"] = self.sbk_WorkArea.GetPageCount() - 1
            self.lbl_Banner.SetLabel(shorthand)
            self.ProjectTab = self.sbk_WorkArea.GetChildren()[self.dic_WorkAreaPageIndices["Current"]]
            self.ProjectTab.Index = self.dic_WorkAreaPageIndices["Current"]
            self.ProjectTab.ButtonBar.lbl_Filename.SetLabel(u"(No filename, yet)")
            self.ProjectTab.ButtonBar.EnableButtons(True)
            self.btn_Current.Enable()
            self.on_sidebar_button(None, button = "Current")
            self.Thaw()

    def toggle_db_connection(self, event = None):

        self.db_comment = ""

        if self.db_connection is None:
            db_dialog = dbc.DBCredentials(self)
            db_dialog.ShowModal()
            db_dialog.Destroy()
            if self.db_comment == "success":
                wx.MessageBox(
                        message = u"BBQ is now connected to the SCARAB database.",
                        caption = u"Connected",
                        style = wx.OK|wx.ICON_INFORMATION)
                self.btn_DBConnect.is_connected(True)
            elif self.db_comment == "cancel":
                self.db_comment = ""
                wx.MessageBox(
                        message = u"Database connection cancelled by user.",
                        caption = u"Cancelled",
                        style = wx.OK|wx.ICON_INFORMATION)
                return None
            else:
                wx.MessageBox(
                        u"Connection failed due to errors. Please contact BBQ and SCARAB support:\n"
                        + self.db_comment,
                        caption = "Connection Failed",
                        style = wx.OK|wx.ICON_WARNING)
                self.db_comment = ""
                self.btn_DBConnect.is_connected(False)
                return None
        else:
            disconnect = wx.MessageBox(
                    message = u"Do you want to disconnect from the SCARAB database?",
                    caption = "Disconnect?",
                    style = wx.YES_NO|wx.ICON_QUESTION)
            if disconnect == wx.YES:
                self.db_connection.close()
                self.db_connection = None
                wx.MessageBox(message = u"BBQ is now disconnected from the SCARAB database.",
                              caption = u"Disconnected",
                              style = wx.OK|wx.ICON_INFORMATION)
                self.db_comment = ""
                self.btn_DBConnect.is_connected(False)
            else:
                return None
        

##################################################################
##                                                              ##
##    ##    ##   ####   ##  ##  ##     ####   #####   #####     ##
##    ###  ###  ##  ##  ##  ### ##    ##  ##  ##  ##  ##  ##    ##
##    ########  ######  ##  ######    ######  #####   #####     ##
##    ## ## ##  ##  ##  ##  ## ###    ##  ##  ##      ##        ##
##    ##    ##  ##  ##  ##  ##  ##    ##  ##  ##      ##        ##
##                                                              ##
##################################################################

class BBQ(wx.App):
    """
    Main app
    """

    def OnInit(self):

        #logging.info("Initialising instance of BBQ (wx.APP)")

        titlebar = True

        self.SetAppName("BBQ")
        #logging.info("Create main frame")
        self.frame = frm_Main(None, titlebar)
        #logging.info("Show main frame")
        self.frame.Show(True)
        self.frame.SetWindowStyle(wx.DEFAULT_FRAME_STYLE)
        self.frame.Maximize(True)

        if titlebar == True:
        #    logging.info("Titlebar = True")
            self.frame.SetWindowStyle(wx.RESIZE_BORDER)
        else:
        #    logging.info("Titlebar = False")
            # Set useful paths (locations of image files)
            #real_path = os.path.realpath(__file__)
            filepath = os.path.dirname(os.path.realpath(__file__))
            # Set Application Icon and Taskbar Icon
            self.frame.SetIcon(wx.Icon(filepath + r"\bbq.ico", wx.BITMAP_TYPE_ANY))

        return True

##########################################################################
##                                                                      ##
##    ##    ##   ####   ##  ##  ##    ##       ####    ####   #####     ##
##    ###  ###  ##  ##  ##  ### ##    ##      ##  ##  ##  ##  ##  ##    ##
##    ########  ######  ##  ######    ##      ##  ##  ##  ##  #####     ##
##    ## ## ##  ##  ##  ##  ## ###    ##      ##  ##  ##  ##  ##        ##
##    ##    ##  ##  ##  ##  ##  ##    ######   ####    ####   ##        ##
##                                                                      ##
##########################################################################

def main():
    #logging.info("Call BBQ app instance")
    app = BBQ(False)
    #logging.info("Go into main loop")
    app.MainLoop()
    #logging.info("We're in the main loop")

if __name__ == "__main__":
    # Uncomment the following line to catch user warnings as errors
    # for debugging purposes
    #warnings.simplefilter('error', "SettingWithCopyWarning")
    multiprocessing.freeze_support() # this line is required to stop the issue
                                     # where the multiprocessing just opens several
                                     # instances of frozen executable without doing
                                     # anything with the processes.
    #logging.info("Starting main function")
    main()