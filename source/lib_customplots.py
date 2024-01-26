# Library of custom(ised) plot classes that include added functionality for the userinterface.
# built on https://stackoverflow.com/questions/10737459/embedding-a-matplotlib-figure-inside-a-wxpython-panel

import os

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.figure import Figure
from matplotlib.backend_bases import MouseButton
from matplotlib import patches

# Import for copying to clipboard
from PIL import Image

import lib_datafunctions as df
import lib_platefunctions as pf
import lib_fittingfunctions as ff
import lib_messageboxes as msg
import lib_tooltip as tt
import lib_colourscheme as cs
import lib_custombuttons as btn

import pandas as pd
import numpy as np
import os

import wx
from wx.core import SetCursor

##############################################################################
##                                                                          ##
##    ##   #####  ######  ######          #####   ##       ####   ######    ##
##    ##  ##      ##      ##  ##          ##  ##  ##      ##  ##    ##      ##
##    ##  ##      #####   ##  ##  ######  #####   ##      ##  ##    ##      ##
##    ##  ##          ##  ##  ##          ##      ##      ##  ##    ##      ##
##    ##   ####   #####   ######          ##      ######   ####     ##      ##
##                                                                          ##
##############################################################################

class CurvePlotPanel(wx.Panel):
    """
        Custom class using wxPython class wx.Panel.
        This holds the plot of datapoints and fitted curve.
        It also included all the functions required to make
        it an interactive plot, namely
        
        Methods
            draw
            destroy_tooltip
            on_right_click
            on_mouse_move
            on_pick
            include_exclude
            plot_to_clipboard
            plot_to_png
            data_to_clipboard
    """

    def __init__(self,parent,PanelSize,tabname,summaryplot = False):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.tabname = tabname
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(350/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.axes = self.figure.add_subplot()
        self.Confidence = False
        self.data = None
        self.plate = None
        self.sample = None
        self.SummaryPlot = summaryplot
        self.outside_warning = True
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def draw(self,virtualonly=False):
        """
        Draws the plot.

        Arguments:
            virtualonly -> boolean. Set to True if the plot is only
                           drawn "virtually" to be written to PNG
                           or copied to clipboard.
        """
        self.SampleID = self.data["SampleID"]
        # Convert dose to micromoles
        self.dose = df.moles_to_micromoles(self.data["Concentrations"])
        self.figure.clear() # clear and re-draw function
        self.axes = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.11, right=0.99,
                                    top=self.Top , bottom=self.Bottom)
        # Actual Plot
        if self.data["Show"] == 0:
            str_Show = "Raw"
            str_Fit = ""
        elif self.data["Show"] == 1:
            str_Show = "Norm"
            str_Fit = "Free"
        elif self.data["Show"] == 2:
            str_Show = "Norm"
            str_Fit = "Const"
        # Get in/excluded points into a list w/o nan, using the dataframe
        # column with nan values produced a runtime warning with current
        # numpy version (date:2022-05-04)!
        plotting  = self.include_exclude(str_Show)
        self.dic_Doses = {"Data":plotting["dose_incl"],"Excluded":plotting["dose_excl"]}
        if len(plotting["dose_incl"]) > 0:
            self.axes.errorbar(plotting["dose_incl"], plotting["resp_incl"],
                             yerr=plotting["sem_incl"], fmt="none",
                             color=cs.TMBlue_Hex, elinewidth=0.3, capsize=2)
            self.axes.scatter(plotting["dose_incl"], plotting["resp_incl"],
                            marker="o", label="Data",
                            color=cs.TMBlue_Hex, picker=5)
        if len(plotting["dose_excl"]) > 0:
            self.axes.errorbar(plotting["dose_excl"], plotting["resp_excl"],
                             yerr=plotting["sem_excl"], fmt="none",
                             color=cs.TMBlue_Hex, elinewidth=0.3, capsize=2)
            self.axes.scatter(plotting["dose_excl"], plotting["resp_excl"],
                            marker="o", label="Excluded",
                            color=cs.WhiteHex, picker=5, edgecolors=cs.TMBlue_Hex,
                            linewidths=0.8)
        if self.data["DoFit"+str_Fit] == True:
            self.axes.plot(self.dose, self.data[str_Show+"Fit"+str_Fit],
                         label="Fit", color=cs.TMRose_Hex)
            if self.Confidence == True:
                upper, lower = ff.draw_sigmoidal_fit_error(self.data["Concentrations"],
                    self.data[str_Show+"Fit"+str_Fit+"Pars"],
                    self.data[str_Show+"Fit"+str_Fit+"CI"]) # Plot 95%CI of fit
                self.axes.fill_between(self.dose, upper, lower, color="red", alpha=0.15)
        self.axes.set_title(self.SampleID)
        self.axes.set_xlabel("Concentration (" + chr(181) +"M)")
        self.axes.set_xscale("log")
        # Set Y axis label and scale according to what's being displayed
        if str_Show == "Norm":
            self.normalised = True
            self.axes.set_ylabel("Per-cent inhibition")
            self.axes.set_ylim([-20,120])
            self.axes.axhline(y=0, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=0
            self.axes.axhline(y=100, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=100
            self.axes.ticklabel_format(axis="y", style="plain")
            if self.outside_warning == True:
                outside = self.points_outside(120, 20)
                if outside > 0:
                    # these are matplotlib.patch.Patch properties
                    props = dict(boxstyle='square', facecolor='wheat', alpha=0.5)
                    # place a text box in upper left in axes coords
                    if outside > 1:
                        note = str(outside) + u" datapoints lie outside boundaries."
                    else:
                        note = u"1 datapoint lies outside boundaries."
                    self.axes.text(0.05, 0.95,
                                   note,
                                   transform=self.axes.transAxes,
                                   fontsize=12,
                                   verticalalignment='top',
                                   bbox=props)
        else:
            self.normalised = False
            self.axes.set_ylabel("Signal in AU")
            self.axes.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
        self.axes.legend()
        # Test if the summary graph needs to be redrawn, too.
        # Does not apply if the plot is just used virtually for exporting of image file
        if virtualonly == False:
            for i in range(len(self.tabname.plt_MultiPlot.IDs)):
                if self.tabname.plt_MultiPlot.IDs[i] == self.SampleID:
                    self.tabname.plt_MultiPlot.Dose[i] = self.dose
                    self.tabname.plt_MultiPlot.RawPoints[i] = self.data["Raw"]
                    self.tabname.plt_MultiPlot.RawFit[i] = self.data["RawFit"]
                    self.tabname.plt_MultiPlot.NormPoints[i] = self.data["Norm"]
                    if str_Fit == "":
                        self.tabname.plt_MultiPlot.NormFit[i] = self.data["NormFit"+"Free"]
                    else:
                        self.tabname.plt_MultiPlot.NormFit[i] = self.data["NormFit"+str_Fit]
                    self.tabname.plt_MultiPlot.Normalised = self.tabname.MultiPlotNormalised()
                    self.tabname.plt_MultiPlot.draw()
                    break
            # Bind/connect events
            self.canvas.mpl_connect("pick_event", self.on_pick)
            self.canvas.mpl_connect("button_press_event", self.on_right_click)
            self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
            self.canvas.mpl_connect("axes_leave_event", self.destroy_tooltip)
            self.canvas.mpl_connect("figure_leave_event", self.destroy_tooltip)
            self.Bind(wx.EVT_KILL_FOCUS, self.destroy_tooltip)
        # Draw the plot!
        self.canvas.draw()

    def destroy_tooltip(self, event):
        """
        Event handler for mouse leaving the axes or figure. Destroys the tooltip.
        """
        try: self.tltp.Destroy()
        except: None

    def on_right_click(self, event):
        """
        Event handler. Shows tooltip on right click.
        """
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(PlotContextMenu(self))

    def on_mouse_move(self, event):
        """
        Custom function I wrote to get tool tips working with matplotlib
        backend plots in wxPython.
        The way this works is as follows:
            - x and y coordinates of the mouse get handed to the function
              from a "motion_notify_event" from the plot.
            - The function pulls the plot data from the global dataframe
              (by looking up the sample ID)
            - Coordinates get then compared to the x and y coordinates
              of the graph (for loop going through the datapoints).
            - If the mouse coordinates are within a certain range of a
              datapoint (remember to take scale of axes into account),
              wx.Dialog dlg_ToolTip gets called. Before each call, the
              function will try to destry it (the neccessary "except:"
              just goes to None). If the mouse coordinates are not within
              range of a datapoint, the function will also try to destroy
              the dialog. This way, it is ensured that the dialog gets
              always closed when the mouse moves away from a
              datapoint.
        """
        if event.inaxes:
            try: self.tltp.Destroy()
            except: None
            # Get coordinates on plot
            x, y = event.xdata, event.ydata
            lst_YLimits = self.axes.get_ylim()
            within = (lst_YLimits[1] - lst_YLimits[0])/100 * 2
            if self.normalised == True:
                str_YData = "Norm"
                str_Unit = " " + chr(37)
            else:
                str_YData = "Raw"
                str_Unit = ""
            for i in range(len(self.data.loc["Concentrations"])):
                # For the x axis (log scale), we have to adjust relative
                if (x >= (self.data.Concentrations[i]*1000000*0.9) and
                    x <= (self.data.Concentrations[i]*1000000*1.1)):
                    # for the y axis, we have to adjust absolute
                    if (y >= (self.data.loc[str_YData][i] - within) and
                        y <= (self.data.loc[str_YData][i] + within)):
                        str_Tooltip = ("x: "
                                      + str(self.data.Concentrations[i])
                                      + " M\ny: " + str(self.data.loc[str_YData][i])
                                      + str_Unit)
                        self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                        self.tltp.Show()
                        self.SetFocus()
                        break
    
    # Function for clicking on points
    def on_pick(self, event):
        """
        Event handler.
        Includes or excludes the selected datapoint from the fit.
        """
        # check if event gives valid result:
        N = len(event.ind)
        if not N: return True
        # Get selected datapoint:
        # Get index of point in picked series
        picked = event.ind[0]
        # Get picked series (included or excluded)
        flt_PickedConc =  self.dic_Doses[event.artist.get_label()][picked]
        # Find concentration, if matches, get index of datapoint:
        for idx in range(len(self.dose)):
            if self.dose[idx] == flt_PickedConc:
                dp = idx
            
        refit = df.recalculate_fit_sigmoidal(self.tabname, self.plate, self.sample, dp, do_return = True)

        if refit is None:
            wx.MessageBox("You are trying to remove too many points. Attempting to fit with less than five points will not produce a reliable fit.",
                    "Not enough points left",
                    wx.OK|wx.ICON_INFORMATION)
        else:
            # dataset gets pushed back into assay_data frame in recalculate_fit_sigmoidal function.
            self.data = refit
            self.draw()
            self.tabname.update_details(self.data, self.data["Show"])
            self.tabname.UpdateSampleReporting(None)

    def points_outside(self, upper, lower):
        """
        Tests to see if there are points outside the boundaries for
        normalised datasets
        """
        outside = 0
        for val in self.data["Norm"]:
            if val > 120:
                outside += 1
            elif val < -20:
                outside += 1
        return outside
        

    def include_exclude(self, str_Show):
        """
        Prepares value lists for plotting that are free of np.nan
        values.

        Arguments:
            str_Show ->string. Determines which dataset is shown.
        """
        # Ensure we have a list of ALL responses, included or excluded
        response_all = []
        for idx in range(len(self.data[str_Show])):
            if not pd.isna(self.data[str_Show][idx]) == True:
                response_all.append(self.data[str_Show][idx])
            else:
                response_all.append(self.data[str_Show+"Excluded"][idx])

        # Prepare lists that only contain excluded or included
        # points, no np.nan values.
        dose_incl = []
        resp_incl = []
        sem_incl = []
        dose_excl = []
        resp_excl = []
        sem_excl = []
        for point in range(len(self.data[str_Show])):
            if not pd.isna(self.data[str_Show][point]) == True:
                dose_incl.append(self.dose[point])
                resp_incl.append(response_all[point])
                sem_incl.append(self.data[str_Show+"SEM"][point])
            else:
                dose_excl.append(self.dose[point])
                resp_excl.append(response_all[point])
                sem_excl.append(self.data[str_Show+"SEM"][point])

        #return dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl

        return {"dose_incl":dose_incl, "resp_incl":resp_incl, "sem_incl":sem_incl,
                "dose_excl":dose_excl, "resp_excl":resp_excl, "sem_excl":sem_excl}

    def plot_to_clipboard(self, event = None):
        """
        Event handler.
        Calls shared function to copy plot image to clipboard.
        """
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        """
        Event handler.
        Calls shared function to copy plot image to clipboard.
        """
        shared_plot_to_png(self)

    def data_to_clipboard(self, event = None):
        """
        Event handler.
        Writes plotted data to pandas dataframe and from there
        to clipboard.
        """
        pd.DataFrame({"Concentration[uM]":self.data["Concentrations"],
                      "NormalisedMean":self.data["Norm"],
                      "NormalisedSEM":self.data["NormSEM"],
                      "FreeFit":self.data["NormFitFree"],
                      "ConstrainedFit":self.data["NormFitConst"]}
                      ).to_clipboard(header=True, index=False)


############################################################################
##                                                                        ##
##    ##  ##  ######   ####   ######          ##    ##   ####   #####     ##
##    ##  ##  ##      ##  ##    ##            ########  ##  ##  ##  ##    ##
##    ######  ######  ######    ##    ######  ## ## ##  ######  #####     ##
##    ##  ##  ##      ##  ##    ##            ##    ##  ##  ##  ##        ##
##    ##  ##  ######  ##  ##    ##            ##    ##  ##  ##  ##        ##
##                                                                        ##
############################################################################

class HeatmapPanel(wx.Panel):
    """
    
    Methods:
        draw
        on_right_click
        destroy_tooltip
        on_mouse_move
        on_click
        plot_to_clipboard
        plot_to_png
        data_to_clipboard
        minor_ticks
        qc_to_clipboard
        
    
    """
    def __init__(self, parent, size, tabname, title = u"Plate Raw Data",
                 titlepos = 1.075, titlefontsize = 14,
                 xlabel = u"Replicate 1", ylabel = u"Value", detailplot = False,
                 summaryplot = False, buttons = False):
        wx.Panel.__init__(self, parent,size=size)#wx.Size(600,450))
        self.tabname = tabname
        self.detailplot = detailplot
        self.ylabel = ylabel
        self.figure = Figure(figsize=(size[0]/100,size[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.axes = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.05, right=0.9, top=0.85 , bottom=0.05)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.title = title
        self.titlePosition = titlepos
        self.titleFontSize = titlefontsize
        self.cycle = 0
        self.plate = 0
        self.PairedHeatmaps = []
        self.SummaryPlot = summaryplot
        self.data = None
        self.vmax = None
        self.vmin = None

        # Arranging GUI elements
        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Plot = wx.BoxSizer(wx.VERTICAL)
        # Plot and buttons
        self.szr_Plot.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        if buttons == True:
            self.szr_ExportButtons = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_ToClipboard = btn.CustomBitmapButton(self, u"Clipboard", 0, (130,25))
            self.btn_ToClipboard.Bind(wx.EVT_BUTTON, self.plot_to_clipboard)
            self.szr_ExportButtons.Add(self.btn_ToClipboard, 0, wx.ALL, 5)
            self.btn_ToPNG = btn.CustomBitmapButton(self, u"ExportToFile", 0, (104,25))
            self.btn_ToPNG.Bind(wx.EVT_BUTTON, self.plot_to_png)
            self.szr_ExportButtons.Add(self.btn_ToPNG, 0, wx.ALL, 5)
            self.szr_Plot.Add(self.szr_ExportButtons, 0, wx.EXPAND, 0)
        self.szr_Surround.Add(self.szr_Plot, 0, wx.ALL, 0)
        # Data Quality
        self.szr_DataQuality = wx.BoxSizer(wx.VERTICAL)
        self.szr_DataQuality.Add((0, 35), 0, wx.EXPAND, 5)
        self.szr_Wells = wx.FlexGridSizer(8,3,0,0)
        self.lbl_DisplayPlot = wx.StaticText(self, wx.ID_ANY, u"Plate details:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DisplayPlot, 0, wx.ALL, 5)
        self.lbl_SEM = wx.StaticText(self, wx.ID_ANY, chr(177)+u"SEM", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SEM, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_BufferWellsLabel = wx.StaticText(self, wx.ID_ANY, u"Buffer only wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BufferWellsLabel, 0, wx.ALL, 5)
        self.lbl_BufferWells = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BufferWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_SolventWellsLabel = wx.StaticText(self, wx.ID_ANY, u"Solvent wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SolventWellsLabel, 0, wx.ALL, 5)
        self.lbl_SolventWells = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SolventWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_ControlWellsLabel = wx.StaticText(self, wx.ID_ANY, u"Control compound wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ControlWellsLabel, 0, wx.ALL, 5)
        self.lbl_ControlWells = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ControlWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_BCLabel = wx.StaticText(self, wx.ID_ANY, u"Buffer to control: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BCLabel, 0, wx.ALL, 5)
        self.lbl_BC = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BC, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_DCLabel = wx.StaticText(self, wx.ID_ANY, u"Solvent to control: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DCLabel, 0, wx.ALL, 5)
        self.lbl_DC = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DC, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_ZPrimeMeanLabel = wx.StaticText(self, wx.ID_ANY, u"Z"+chr(39)+u" (mean): ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMeanLabel, 0, wx.ALL, 5)
        self.lbl_ZPrimeMean = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMean, 0, wx.ALL, 5)
        self.btn_ZPrimeMean = btn.InfoButton(self, u"UltraLight", tooltip=u"How is Z' calculated?")
        self.btn_ZPrimeMean.ImagePath = os.path.join(self.tabname.parent.str_OtherPath, "ZPrimeMeanToolTip.png")
        self.btn_ZPrimeMean.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.szr_Wells.Add(self.btn_ZPrimeMean, 0, wx.ALL, 5)
        self.lbl_ZPrimeMedianLabel = wx.StaticText(self, wx.ID_ANY, u"Z"+chr(39)+u" (median): ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMedianLabel, 0, wx.ALL, 5)
        self.lbl_ZPrimeMedian = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMedian, 0, wx.ALL, 5)
        self.btn_ZPrimeMedian = btn.InfoButton(self, u"UltraLight", tooltip=u"How is Z'(median) calculated?")
        self.btn_ZPrimeMedian.ImagePath = os.path.join(self.tabname.parent.str_OtherPath, "ZPrimeMedianToolTip.png")
        self.btn_ZPrimeMedian.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.szr_Wells.Add(self.btn_ZPrimeMedian, 0, wx.ALL, 5)
        self.szr_DataQuality.Add(self.szr_Wells,0,wx.ALL,0)
        self.lin_BelowDetails = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_DataQuality.Add(self.lin_BelowDetails, 0, wx.EXPAND|wx.ALL, 5)
        self.btn_qc_to_clipboard = btn.CustomBitmapButton(self, u"Clipboard", 0, (130,25))
        self.szr_DataQuality.Add(self.btn_qc_to_clipboard, 0, wx.ALL|wx.ALIGN_RIGHT, 5)
    
        self.btn_qc_to_clipboard.Bind(wx.EVT_BUTTON, self.qc_to_clipboard)

        self.szr_Surround.Add(self.szr_DataQuality, 0, wx.ALL, 0)

        
        self.SetSizer(self.szr_Surround)
        self.Fit()

    def draw(self):
        """
        "Value" is whatever gets shown. Can be raw data, Tm, deltaTm, reaction rate, etc.
        """
        self.figure.clear()
        self.axes = self.figure.add_subplot()

        # Title, axes, grid
        self.axes.set_title(self.title, fontsize=self.titleFontSize, y=self.titlePosition)
        self.axes.grid(which="minor", color="black", linestyle="-", linewidth=1)
        # Rows and columns
        self.Plateformat = self.data.shape[0] # Save plateformat as property of plot
        self.int_Rows = pf.plate_rows(self.Plateformat)
        self.int_Columns = pf.plate_columns(self.Plateformat)
        self.lst_Rows = []
        for r in range(self.int_Rows):
            if r < 26:
                self.lst_Rows.append(chr(65+r))
            else:
                self.lst_Rows.append("A" + chr(65+(r-25)))
        self.lst_Major_X = [int(x) for x in range(self.int_Columns)]
        self.lst_Major_Y = [int(y) for y in range(self.int_Rows)]
        self.lst_Columns = [str(c) for c in range(1,self.int_Columns+1)]
        
        if self.Plateformat <= 96:
            self.int_FontSize = 8
        elif self.Plateformat == 384:
            self.int_FontSize = 5
        elif self.Plateformat == 1536:
            self.int_FontSize = 3

        self.SampleIDs = self.data["SampleID"].to_list()

        # Transpose plate data into format required for heatmap:
        self.PlateData = [[]] * self.int_Rows
        lst_PlateData = self.data["Value"].to_list()
        for row in range(self.int_Rows):
            start = row*self.int_Columns
            stop = (row+1)*self.int_Columns
            self.PlateData[row] = lst_PlateData[start:stop]
        # Determine vmax and vmin for heatbar, if not given:
        if self.vmax == None:
            self.vmax = np.nanmax(lst_PlateData)
        if self.vmin == None:
            self.vmin = np.nanmin(lst_PlateData)
        # create heatmap
        im = self.axes.imshow(self.PlateData,
                              cmap="PuOr",
                              picker=True,
                              vmax=self.vmax,
                              vmin=self.vmin)

        # X axis (numbers)
        self.axes.xaxis.set_units(None)
        self.axes.set_xticks(self.lst_Major_X) # Major ticks
        self.axes.set_xticks(self.minor_ticks(self.lst_Major_X), minor=True) # Minor ticks
        self.axes.set_xticklabels(self.lst_Columns)
        self.axes.tick_params(axis="x", labelsize=self.int_FontSize)
        # Y axis (letters)
        self.axes.yaxis.set_units(None)
        self.axes.set_yticks(self.lst_Major_Y) # Major ticks
        self.axes.set_yticks(self.minor_ticks(self.lst_Major_Y), minor=True) # Minor ticks
        self.axes.set_yticklabels(self.lst_Rows)
        self.axes.tick_params(axis="y", labelsize=self.int_FontSize)
        self.axes.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
        self.axes.tick_params(which="minor", bottom=False, left=False)

        # Colour bar
        # Change size of colorbar: https://matplotlib.org/mpl_toolkits/axes_grid/users/overview.html#axesdivider
        divider = make_axes_locatable(self.axes)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cbar = self.axes.figure.colorbar(im, cax=cax)
        cbar.ax.set_ylabel(self.ylabel, rotation=-90, va="bottom")
        cbar.ax.tick_params(labelsize=8)
        # Add event handlers
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self.on_right_click)
        self.canvas.mpl_connect("axes_leave_event", self.destroy_tooltip)
        self.canvas.mpl_connect("figure_leave_event", self.destroy_tooltip)
        self.Bind(wx.EVT_KILL_FOCUS, self.destroy_tooltip)
        if self.detailplot == True:    
            self.canvas.mpl_connect("pick_event", self.on_click)
        self.canvas.draw()
        self.Backup = self.canvas.copy_from_bbox(self.figure.bbox)
        self.dic_Highlights = {}
        self.dic_WellMarker = {}

    def on_right_click(self, event):
        """
        Event handler. Opens context menu on right click.
        """
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(PlotContextMenu(self))

    def destroy_tooltip(self, event):
        try: self.tltp.Destroy()
        except: None
        for i in range(self.int_Highlights):
            try: self.dic_Highlights[i].remove
            except: None
        for heatmap in self.PairedHeatmaps:
            for key in heatmap.dic_Highlights.keys():
                try: heatmap.dic_Highlights[key].remove()
                except: None
            heatmap.canvas.blit()
            heatmap.canvas.restore_region(heatmap.Backup)

        self.canvas.blit()
        self.canvas.restore_region(self.Backup)

        if len(self.dic_WellMarker) > 0:
            for key in self.dic_WellMarker.keys():
                self.axes.add_patch(self.dic_WellMarker[key])
                self.axes.draw_artist(self.dic_WellMarker[key])

    def on_mouse_move(self, event):
        """
        Custom function I wrote to get tool tips working with matplotlib
        backend plots in wxPython.
        The way this works is as follows:
            - x and y coordinates of the mouse get handed to the function from
              a "motion_notify_event" from the plot.
            - The function pulls the plot data from the global dataframe (by
              looking up the sample ID)
            - Coordinates get then compared to the x and y coordinates of the
              graph (for loop going through the datapoints).
            - If the mouse coordinates are within a certain range of a datapoint
              (remember to take scale of axes into account), wx.Dialog dlg_ToolTip
              gets called. Before each call, the function will try to destry it
              (the neccessary "except:" just goes to None). If the mouse
              coordinates are not within range of a datapoint, the function will
              also try to destroy the dialog. This way, it is ensured that the
              dialog gets always closed when the mouse moves away from a datapoint.
        """
        # Destroy previous tooltip and highlight
        self.dic_Highlights = {}
        self.int_Highlights = 0
        self.destroy_tooltip(None)
        if event.inaxes:
            # Get coordinates on plot
            int_Columns = pf.plate_columns(self.Plateformat)
            int_Rows = pf.plate_rows(self.Plateformat)
            x, y = int(round(event.xdata,0)), int(round(event.ydata,0))
            if x < 0 or y < 0:
                # Mouse is outside the heatmap, e.g. the colour bar or legend.
                return None
            if x < int_Columns and y < int_Rows:
                well = x + (int_Columns * y)
                str_Tooltip = pf.index_to_well(well+1, self.Plateformat) # index_to_well takes the well index to base 1, not 0!
                if hasattr(self.tabname, "dfr_Layout"):
                    layout = self.tabname.dfr_Layout.loc[0,"Layout"]
                    str_WellType = layout.loc[well,"WellType"]
                    if str_WellType == "s":
                        str_Sample = str(self.data.loc[well,"SampleID"])
                        if len(str_Sample) > 40:
                            str_Sample = str_Sample[:40] + "..."
                        str_Tooltip += f": {str_Sample} (Sample)"
                    elif str_WellType == "r":
                        ref = layout.loc[well,"ReferenceID"]
                        str_Tooltip += f" (Reference: {ref})"
                    elif str_WellType == "c":
                        ctrl = layout.loc[well,"ControlID"]
                        str_Tooltip += f" (Control compound: {ctrl})"
                    else:
                        str_Tooltip += ""
                if not pd.isna(self.PlateData[y][x]):
                    str_Tooltip += "\n" + "Value: " + str(round(self.PlateData[y][x],2))
                self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                self.tltp.Show()

                lst_Wells = []
                self.int_Highlights = 0
                if not self.SampleIDs[well] == "":
                    for idx in range(len(self.SampleIDs)):
                        if self.SampleIDs[well] == self.SampleIDs[idx]:
                            lst_Wells.append(pf.index_to_row_col(idx,int_Rows,int_Columns))
                            self.int_Highlights += 1
                # Highlight well(s):
                # Ensure the original well is always on the list, even if there are no sample IDs
                tpl_Well = pf.index_to_row_col(well,int_Rows,int_Columns)
                if not tpl_Well in lst_Wells:
                    lst_Wells.append(tpl_Well)
                    self.int_Highlights += 1
                for i in range(self.int_Highlights):
                    self.dic_Highlights[i] = patches.Rectangle((lst_Wells[i][1]-0.5,lst_Wells[i][0]-0.5),1,1,ec="white",fill=False)
                    self.axes.add_patch(self.dic_Highlights[i])
                    self.axes.draw_artist(self.dic_Highlights[i])
                self.canvas.blit()
                # Add wells on paired heatmaps:
                for heatmap in self.PairedHeatmaps:
                    heatmap.dic_Highlights = {}
                    for i in range(self.int_Highlights):
                        heatmap.dic_Highlights[i] = patches.Rectangle((lst_Wells[i][1]-0.5,lst_Wells[i][0]-0.5),1,1,ec="white",fill=False)
                        heatmap.axes.add_patch(heatmap.dic_Highlights[i])
                        heatmap.axes.draw_artist(heatmap.dic_Highlights[i])
                    heatmap.canvas.blit()

                self.SetFocus()

    def on_click(self, event):
        if self.detailplot == True:
            x = int(round(event.mouseevent.xdata,0))
            y = int(round(event.mouseevent.ydata,0))
            self.tabname.update_detail_plot(self.tabname, x, y)
            try:
                self.dic_WellMarker[0].remove()
                self.canvas.blit()
                self.canvas.restore_region(self.Backup)
            except:
                None
            self.dic_WellMarker = {}
            self.dic_WellMarker[0] = patches.Rectangle((x-0.5,y-0.5),1,1,ec="yellow",fill=False,linewidth=1)
            self.axes.add_patch(self.dic_WellMarker[0])
            self.axes.draw_artist(self.dic_WellMarker[0])
            self.canvas.blit()

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)
    
    def data_to_clipboard(self, event = None):
        dfr_Clipboard = pd.DataFrame(columns=self.lst_Columns, index=self.lst_Rows)
        for row in range(len(self.PlateData)):
            for col in range(len(self.PlateData[row])):
                dfr_Clipboard.iloc[row,col] = self.PlateData[row][col]
        dfr_Clipboard.to_clipboard(header=True, index=True)

    def qc_to_clipboard(self, event = None):
        idx_Plate = self.plate
        pd.DataFrame({"BufferMean":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["BufferMean",0],2)],
            "BufferSEM":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["BufferSEM",0],2)],
            "SolventMean":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["SolventMean",0],2)],
            "SolventSEM":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["SolventSEM",0],2)],
            "ControlMean":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "ControlSEM":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["ControlSEM",0],2)],
            "BufferToControl":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["BufferMean",0]/self.tabname.assay_data.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "SolventToControl":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["SolventMean",0]/self.tabname.assay_data.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "ZPrimeMean":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["ZPrimeMean",0],3)],
            "ZPrimeMedian":[round(self.tabname.assay_data.loc[idx_Plate,"References"].loc["ZPrimeMedian",0],3)]}).to_clipboard(header=True, index=False)

    def minor_ticks(self, lst_Major):
        lst_Minor = []
        for tick in lst_Major:
            lst_Minor.append(tick + 0.5)
        return lst_Minor

##################################################################
##                                                              ##
##     #####   #####   ####   ######  ######  ######  #####     ##
##    ##      ##      ##  ##    ##      ##    ##      ##  ##    ##
##     ####   ##      ######    ##      ##    ####    #####     ##
##        ##  ##      ##  ##    ##      ##    ##      ##  ##    ##
##    #####    #####  ##  ##    ##      ##    ######  ##  ##    ##
##                                                              ##
##################################################################

class ScatterPlotPanel(wx.Panel):
    def __init__(self, parent, size, tabname, title,
                 titlepos = 1.075, titlefontsize = 14,
                 xlabel = "", ylabel = "", detailplot = False,
                 summaryplot = False, buttons = False,
                 threshold = 80, lines = [], limits = []):
        wx.Panel.__init__(self, parent,size=size)
        self.tabname = tabname
        self.detailplot = detailplot
        self.threshold = threshold
        self.lines = lines
        self.limits = limits
        self.ylabel = ylabel
        self.figure = Figure(figsize=(size[0]/100,size[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.axes = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.10, right=0.99, top=0.90 , bottom=0.15)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.title = title

        # Arranging GUI elements
        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Plot = wx.BoxSizer(wx.VERTICAL)
        # Plot and buttons
        self.szr_Plot.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        if buttons == True:
            self.szr_ExportButtons = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_ToClipboard = btn.CustomBitmapButton(self, u"Clipboard", 0, (130,25))
            self.btn_ToClipboard.Bind(wx.EVT_BUTTON, self.plot_to_clipboard)
            self.szr_ExportButtons.Add(self.btn_ToClipboard, 0, wx.ALL, 5)
            self.btn_ToPNG = btn.CustomBitmapButton(self, u"ExportToFile", 0, (104,25))
            self.btn_ToPNG.Bind(wx.EVT_BUTTON, self.plot_to_png)
            self.szr_ExportButtons.Add(self.btn_ToPNG, 0, wx.ALL, 5)
            self.szr_Plot.Add(self.szr_ExportButtons, 0, wx.EXPAND, 0)
        self.szr_Surround.Add(self.szr_Plot, 0, wx.ALL, 0)
        self.data = None

    def draw(self):
        # Initialise - some redundancy with init because this function is reused when re-drawing the graph for a new dtaset
        self.lst_SampleIDs = self.data["SampleID"].tolist()
        self.int_Samples = self.data.shape[0]
        self.lst_Value = self.data["Value"].tolist()
        self.lst_ValueSEM = self.data["ValueSEM"].tolist()
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(self.title)
        # Need to process input for above and below threshold
        self.lst_BelowThreshold = []
        self.lst_AboveThreshold = []
        self.lst_Below_SEM = []
        self.lst_Above_SEM = []
        for i in range(self.int_Samples):
            if float(self.lst_Value[i]) > self.threshold:
                self.lst_AboveThreshold.append(self.lst_Value[i])
                self.lst_Above_SEM.append(self.lst_ValueSEM[i])
                self.lst_BelowThreshold.append(np.nan)
                self.lst_Below_SEM.append(0)
            else:
                self.lst_AboveThreshold.append(np.nan)
                self.lst_Above_SEM.append(0)
                self.lst_BelowThreshold.append(self.lst_Value[i])
                self.lst_Below_SEM.append(self.lst_ValueSEM[i])
        self.axes.set_xlabel("Compounds")
        if len(self.lst_AboveThreshold) > 0:
            self.axes.scatter(range(self.int_Samples), self.lst_AboveThreshold, marker="o", label="Above threshold", color="#aa4499", s=10, picker=3)
            if sum(self.lst_Above_SEM) > 0:
                self.axes.errorbar(range(self.int_Samples), self.lst_AboveThreshold, yerr=self.lst_Above_SEM, fmt="none", color="#aa4499", elinewidth=0.3, capsize=2)
        if len(self.lst_BelowThreshold) > 0:
            self.axes.scatter(range(self.int_Samples), self.lst_BelowThreshold, marker="o", label="Below threshold", color="#44b59a", s=10, picker=3)
            if sum(self.lst_Below_SEM) > 0:
                self.axes.errorbar(range(self.int_Samples), self.lst_BelowThreshold, yerr=self.lst_Below_SEM, fmt="none", color="#44b59a", elinewidth=0.3, capsize=2)
        if len(self.lines) > 0:
            self.axes.axhline(y=self.lines[0], xmin=0, xmax=1, linestyle="--", color="black", linewidth=0.5) # horizontal line
            self.axes.axhline(y=self.lines[1], xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line
        self.axes.set_ylabel(self.ylabel)
        if len(self.limits) > 0:
            self.axes.set_ylim(self.limits)
        self.axes.legend()
        # Connect event handlers
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self.on_right_click)
        self.canvas.mpl_connect("axes_leave_event", self.destroy_tooltip)
        self.canvas.mpl_connect("figure_leave_event", self.destroy_tooltip)
        self.Bind(wx.EVT_KILL_FOCUS, self.destroy_tooltip)
        if self.detailplot == True:
            self.canvas.mpl_connect("pick_event", self.on_click)
        self.canvas.draw()

    def on_right_click(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(PlotContextMenu(self))

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

    def destroy_tooltip(self, event):
        try: self.tltp.Destroy()
        except: None

    def on_mouse_move(self, event):
        """
        Custom function I wrote to get tool tips working with matplotlib backend plots in wxPython.
        First implementation in panel_Dose (dose response)
        The way this works is as follows:
            - x and y coordinates of the mouse get handed to the function from a "motion_notify_event" from the plot.
            - The function pulls the plot data from the global dataframe (by looking up the sample ID)
            - Coordinates get then compared to the x and y coordinates of the graph (for loop going through the datapoints).
            - If the mouse coordinates are within a certain range of a datapoint (remember to take scale of axes into account),
              wx.Dialog dlg_ToolTip gets called. Before each call, the function will try to destry it (the neccessary "except:"
              just goes to None). If the mouse coordinates are not within range of a datapoint, the function will also try to
              destroy the dialog. This way, it is ensured that the dialog gets always closed when the mouse moves away from a
              datapoint.
        """
        if event.inaxes:
            # Get coordinates on plot
            evt_x, evt_y = event.xdata, event.ydata
            lst_XLimits = self.axes.get_xlim()
            within_x = (lst_XLimits[1] - lst_XLimits[0])/100 * 0.5
            lst_YLimits = self.axes.get_ylim()
            within_y = (lst_YLimits[1] - lst_YLimits[0])/100 * 1.5
            for x in range(self.int_Samples):
                # For the x axis (log scale), we have to adjust relative
                if evt_x >= (x - within_x) and evt_x <= (x + within_x) and pd.isna(self.lst_Value[x]) == False:
                    # for the y axis, we have to adjust absolute
                    y = round(self.lst_Value[x])
                    str_SampleID = self.lst_SampleIDs[x]
                    if evt_y >= (y - within_y) and evt_y <= (y + within_y):
                        try: self.tltp.Destroy()
                        except: None
                        str_Tooltip = f"{str_SampleID}\n%I: {y}"
                        self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                        self.tltp.Show()
                        break
                    else:
                        try: self.tltp.Destroy()
                        except: None
                else:
                    try: self.tltp.Destroy()
                    except: None

    def on_click(self, event):
        # check if event gives valid result:
        N = len(event.ind)
        if not N: return True
        # Get plate and sample index:
        idx_Sample = event.ind[0]
        self.tabname.update_detail_plot(0, 0, idx_Sample, self.Plateformat)

    def data_to_clipboard(self, event):
        pd.DataFrame({"SampleIDs":self.lst_SampleIDs,
            "AboveThreshold":self.lst_AboveThreshold,
            "AboveSEM":self.lst_Above_SEM,
            "BelowThreshold":self.lst_BelowThreshold,
            "BelowSEM":self.lst_Below_SEM}).to_clipboard(header=True, index=False)

##################################################################
##                                                              ##
##     #####  #####   ######   #####  ######  #####    ####     ##
##    ##      ##  ##  ##      ##        ##    ##  ##  ##  ##    ##
##     ####   #####   ####    ##        ##    #####   ######    ##
##        ##  ##      ##      ##        ##    ##  ##  ##  ##    ##
##    #####   ##      ######   #####    ##    ##  ##  ##  ##    ##
##                                                              ##
##################################################################

class SpectrumPlotPanel(wx.Panel):
    def __init__(self, parent, size, tabname, title,
                 titlepos = 1.075, titlefontsize = 14,
                 xlabel = "", ylabel = "", detailplot = False,
                 summaryplot = False, buttons = False,
                 lines = [], limits = []):
        wx.Panel.__init__(self, parent,size=size)
        self.tabname = tabname
        self.detailplot = detailplot
        self.lines = lines
        self.limits = limits
        self.ylabel = ylabel
        self.figure = Figure(figsize=(size[0]/100,size[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.axes = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.12, right=0.99, top=0.90 , bottom=0.15)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.title = title

        # Arranging GUI elements
        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Plot = wx.BoxSizer(wx.VERTICAL)
        # Plot and buttons
        self.szr_Plot.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        if buttons == True:
            self.szr_ExportButtons = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_ToClipboard = btn.CustomBitmapButton(self, u"Clipboard", 0, (130,25))
            self.btn_ToClipboard.Bind(wx.EVT_BUTTON, self.plot_to_clipboard)
            self.szr_ExportButtons.Add(self.btn_ToClipboard, 0, wx.ALL, 5)
            self.btn_ToPNG = btn.CustomBitmapButton(self, u"ExportToFile", 0, (104,25))
            self.btn_ToPNG.Bind(wx.EVT_BUTTON, self.plot_to_png)
            self.szr_ExportButtons.Add(self.btn_ToPNG, 0, wx.ALL, 5)
            self.szr_Plot.Add(self.szr_ExportButtons, 0, wx.EXPAND, 0)
        self.szr_Surround.Add(self.szr_Plot, 0, wx.ALL, 0)
        self.data = None

    def draw(self):
        # Initialise - some redundancy with init because this function is reused when re-drawing the graph for a new dtaset
        self.lst_Wavelengths = [int(wl) for wl in self.data.columns.tolist()]
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(self.title)
        self.axes.set_ylabel(self.ylabel)
        self.axes.set_xlabel("Wavelength (nm)")
        
        for sample in self.data.index:
            self.axes.plot(self.lst_Wavelengths,
                           self.data.loc[sample],
                           label=sample)

        if len(self.lines) > 0:
            for line in self.lines:
                self.axes.axvline(x=line, linestyle="--", color="black", linewidth=0.5) # horizontal line
        self.axes.set_ylabel(self.ylabel)
        if len(self.limits) > 0:
            self.axes.set_ylim(self.limits)
        self.axes.legend()
        if not 0 in self.axes.get_ylim():
            self.axes.axhline(y=0, linestyle = "--", color="black", linewidth=0.5)
        self.axes.legend()
        # Connect event handlers
        self.canvas.mpl_connect("button_press_event", self.on_right_click)
        if self.detailplot == True:
            self.canvas.mpl_connect("pick_event", self.on_click)
        self.canvas.draw()

    def on_right_click(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(PlotContextMenu(self))

    def on_click(self, event):
        pass

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

    def destroy_tooltip(self, event):
        try: self.tltp.Destroy()
        except: None

    def data_to_clipboard(self, event = None):
        self.data.to_clipboard(header=True, index=True)

##################################################
##                                              ##
##    ######  #####    ####    #####  ######    ##
##      ##    ##  ##  ##  ##  ##      ##        ##
##      ##    #####   ######  ##      ####      ##
##      ##    ##  ##  ##  ##  ##      ##        ##
##      ##    ##  ##  ##  ##   #####  ######    ##
##                                              ##
##################################################

class TracePlotPanel(wx.Panel):
    """
        Plot for SPR-BLI traces.
    
    """

    def __init__(self, parent, size, tabname, title,
                 titlepos = 1.075, titlefontsize = 14,
                 xlabel = u"Fnord", ylabel = "", detailplot = False,
                 summaryplot = False, buttons = False,
                 vlines = [], limits = []):
        wx.Panel.__init__(self, parent,size=size)
        self.tabname = tabname
        self.detailplot = detailplot
        self.ylabel = ylabel
        self.XLabel = xlabel
        self.figure = Figure(figsize=(size[0]/100,size[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.axes = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.06, right=0.85, top=0.90 , bottom=0.13)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.title = title
        self.ColourOptions = [cs.TMIndigo_RGBA, cs.TMBlue_RGBA, cs.TMCyan_RGBA, cs.TMTeal_RGBA, cs.TMGreen_RGBA, cs.TMOlive_RGBA, cs.TMSand_RGBA, cs.TMRose_RGBA, cs.TMWine_RGBA, cs.TMPurple_RGBA]
        self.Highlight = None
        self.StepBorders = []
        self.StepNames = []

        # Arranging GUI elements
        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Plot = wx.BoxSizer(wx.VERTICAL)
        # Plot and buttons
        self.szr_Plot.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        if buttons == True:
            self.szr_ExportButtons = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_ToClipboard = btn.CustomBitmapButton(self, u"Clipboard", 0, (130,25))
            self.btn_ToClipboard.Bind(wx.EVT_BUTTON, self.plot_to_clipboard)
            self.szr_ExportButtons.Add(self.btn_ToClipboard, 0, wx.ALL, 5)
            self.btn_ToPNG = btn.CustomBitmapButton(self, u"ExportToFile", 0, (104,25))
            self.btn_ToPNG.Bind(wx.EVT_BUTTON, self.plot_to_png)
            self.szr_ExportButtons.Add(self.btn_ToPNG, 0, wx.ALL, 5)
            self.szr_Plot.Add(self.szr_ExportButtons, 0, wx.EXPAND, 0)
        self.szr_Surround.Add(self.szr_Plot, 0, wx.ALL, 0)
        self.data = pd.DataFrame()

    def draw(self, redraw = False):
        # Initialise - some redundancy with init because this function is reused when re-drawing the graph for a new dtaset
        self.Traces = self.data.columns.tolist()
        self.Time = self.data.index.tolist()
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(self.title)
        self.axes.set_xlabel(self.XLabel)
        self.axes.set_ylabel(self.ylabel)

        if redraw == False:
            self.Display = dict(zip(self.Traces, [True] * self.data.shape[1]))
            colours = self.ColourOptions
            multiples = len(self.Traces) // len(self.ColourOptions)
            for m in range(multiples):
                colours += self.ColourOptions
            self.Colours = dict(zip(self.Traces,colours))

        for trace in self.Traces:
            if self.Display[trace] == True:
                alpha = 1
                linewidth = 0.5
                if not self.Highlight == None:
                    if not self.Highlight == trace:
                        alpha = 0.2
                    else:
                        linewidth = 2
                self.axes.plot(self.Time,
                               self.data.loc[:,trace].tolist(),
                               label = trace,
                               color = self.Colours[trace],
                               linewidth = linewidth,
                               alpha = alpha)
        
        # Zero lines
        xlims = self.axes.get_xlim()
        ylims = self.axes.get_ylim()
        
        self.axes.axhline(y=0, xmin=xlims[0], xmax=xlims[1],
                          linestyle="--", color="black", linewidth=0.5) # horizontal line
        self.axes.axvline(x=0, ymin=ylims[0], ymax=ylims[1],
                          linestyle="--", color="black", linewidth=0.5) # horizontal line
        # Mark assay steps
        if len(self.StepBorders) > 0:
            for vline in self.StepBorders:
                if not vline > xlims[1]:
                    self.axes.axvline(x=vline, ymin=ylims[0], ymax=ylims[1], linestyle="--",
                                      color="grey", linewidth=0.5) # horizontal line
                else:
                    break

        self.Legend = self.axes.legend(bbox_to_anchor=(1.025, 1), loc='upper left', borderaxespad=0.)

        if redraw == False:
            # Connect event handlers
            self.canvas.mpl_connect("button_press_event", self.on_click)
            self.canvas.mpl_connect("button_release_event", self.OnRelease)
            self.canvas.mpl_connect("figure_leave_event", self.leave_figure)
            self.canvas.mpl_connect("axes_leave_event", self.leave_figure)
            self.Bind(wx.EVT_KILL_FOCUS, self.leave_figure)
            self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
            #if self.detailplot == True:
            #    self.canvas.mpl_connect("pick_event", self.on_click)
            # The on_click has been removed!
            if self.Highlight == None:
                self.Backup = self.canvas.copy_from_bbox(self.figure.bbox)
        
        self.canvas.draw()

    def on_click(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(PlotContextMenu(self))
        elif event.button is MouseButton.LEFT:
            if self.in_zoom == True:
                zoom_start(self,event)
            else:
                return None

    def OnRelease(self, event):
        pass

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def leave_figure(self, event):
        pass

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

    def destroy_tooltip(self, event):
        try: self.tltp.Destroy()
        except: None

    def on_mouse_move(self, event):
        if self.Legend.get_window_extent().contains(event.x, event.y):
            for text in self.Legend.get_texts():
                if text.get_window_extent().contains(event.x, event.y):
                    self.Highlight = str(text.get_text())
                    self.draw(redraw = True)
                    break
        else:
            self.MouseLeavesLegend(event)

    def MouseLeavesLegend(self, event):
        self.Highlight = None
        self.canvas.blit()
        self.canvas.restore_region(self.Backup)
        self.draw(redraw = True)
        


    def on_mouse_move(self, event):
        """
        Custom function I wrote to get tool tips working with matplotlib backend plots in wxPython.
        First implementation in panel_Dose (dose response)
        The way this works is as follows:
            - x and y coordinates of the mouse get handed to the function from a "motion_notify_event" from the plot.
            - The function pulls the plot data from the global dataframe (by looking up the sample ID)
            - Coordinates get then compared to the x and y coordinates of the graph (for loop going through the datapoints).
            - If the mouse coordinates are within a certain range of a datapoint (remember to take scale of axes into account),
              wx.Dialog dlg_ToolTip gets called. Before each call, the function will try to destry it (the neccessary "except:"
              just goes to None). If the mouse coordinates are not within range of a datapoint, the function will also try to
              destroy the dialog. This way, it is ensured that the dialog gets always closed when the mouse moves away from a
              datapoint.
        """
        if event.inaxes:
            # Get coordinates on plot
            evt_x, evt_y = event.xdata, event.ydata
            lst_XLimits = self.axes.get_xlim()
            within_x = (lst_XLimits[1] - lst_XLimits[0])/100 * 0.5
            lst_YLimits = self.axes.get_ylim()
            within_y = (lst_YLimits[1] - lst_YLimits[0])/100 * 1.5
            for x in range(self.int_Samples):
                # For the x axis (log scale), we have to adjust relative
                if evt_x >= (x - within_x) and evt_x <= (x + within_x) and pd.isna(self.lst_Value[x]) == False:
                    # for the y axis, we have to adjust absolute
                    y = round(self.lst_Value[x])
                    str_SampleID = self.lst_SampleIDs[x]
                    if evt_y >= (y - within_y) and evt_y <= (y + within_y):
                        try: self.tltp.Destroy()
                        except: None
                        str_Tooltip = str_SampleID + "\n%I: " + str(y)
                        self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                        self.tltp.Show()
                        break
                    else:
                        try: self.tltp.Destroy()
                        except: None
                else:
                    try: self.tltp.Destroy()
                    except: None

    

    def data_to_clipboard(self, event):
        pass

######################################################################################
##                                                                                  ##
##    #####   ######  #####   ##      ##   #####   ####   ######  ######   #####    ##
##    ##  ##  ##      ##  ##  ##      ##  ##      ##  ##    ##    ##      ##        ##
##    #####   ####    #####   ##      ##  ##      ######    ##    ####     ####     ##
##    ##  ##  ##      ##      ##      ##  ##      ##  ##    ##    ##          ##    ##
##    ##  ##  ######  ##      ######  ##   #####  ##  ##    ##    ######  #####     ##
##                                                                                  ##
######################################################################################

class ReplicateCorrelation(wx.Panel):
    """
    Plotting replicate corellation between two replicates.
    Replicate 1 on horizontal axis, replicate 2 on vertical axis.
    Also displays fit for replicate corellation and Rsquare value.
    """
    def __init__(self, parent, size, tabname, title = u"Replicate Corellation",
                 titlepos = 1.075, titlefontsize = 14,
                 xlabel = u"Replicate 1", ylabel = u"Replicate 2", detailplot = False,
                 summaryplot = False, buttons = False):
        self.tabname = tabname
        wx.Panel.__init__(self, parent,size=size)#=wx.Size(550,325))
        self.PanelSize = size
        self.Top = 1-30/size[1]
        self.Bottom = 1-(30/self.PanelSize[1])-(350/self.PanelSize[1])
        self.XLabel = xlabel
        self.ylabel = ylabel
        self.title = title
        self.figure = Figure(figsize=(self.PanelSize[0]/100,self.PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(title)
        self.figure.subplots_adjust(left=0.10, right=0.99, top=self.Top , bottom=self.Bottom)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.SampleIDs = []
        self.Replicate1 = []
        self.Replicate2 = []
        self.Extremes = []
        self.RSquare = None
        self.Pearson = None

    def draw(self):
        # Initialise - some redundancy with init because this function is reused when
        # re-drawing the graph for a new dataset
        # If the canvas already exists, we are updating the plot. Therefore, the old needs
        # deleting.
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(self.title)
        self.axes.scatter(self.Replicate1, self.Replicate2, marker="o", label="Replicates", color="#44b59a", s=10, picker=1)#, edgecolors ="black")
        self.axes.plot(self.Extremes, self.Fit, label="Replicate correlation (% solvent reference)")
        self.axes.set_xlabel(self.XLabel)
        self.axes.set_ylabel(self.ylabel)
        #self.axes.legend()
        if not self.RSquare == None:
            str_RSquare = u"R" + chr(178) + " = " + str(round(self.RSquare,3))
            self.axes.annotate(str_RSquare,
                xy=(0,0), xycoords="data", # datapoint that is annotated
                xytext=(440,30), textcoords="axes pixels") # position of annotation
        if not self.Pearson == None:
            str_Pearson = u"PCC = " + str(round(self.Pearson,3))
            self.axes.annotate(str_Pearson,
                xy=(0,0), xycoords="data", # datapoint that is annotated
                xytext=(440,10), textcoords="axes pixels") # position of annotation

        # Connect event handlers
        self.canvas.mpl_connect("pick_event", self.on_click)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self.on_right_click)
        self.canvas.mpl_connect("figure_leave_event", self.leave_figure)
        self.canvas.mpl_connect("axes_leave_event", self.leave_figure)
        self.canvas.draw()

    def on_right_click(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(PlotContextMenu(self))

    def leave_figure(self, event):
        try: self.tltp.Destroy()
        except: None

    def on_mouse_move(self, event):
        """
        Custom function I wrote to get tool tips working with matplotlib backend plots in wxPython.
        First implementation in panel_Dose (dose response)
        The way this works is as follows:
            - x and y coordinates of the mouse get handed to the function from a "motion_notify_event" from the plot.
            - The function pulls the plot data from the global dataframe (by looking up the sample ID)
            - Coordinates get then compared to the x and y coordinates of the graph (for loop going through the datapoints).
            - If the mouse coordinates are within a certain range of a datapoint (remember to take scale of axes into account),
              wx.Dialog dlg_ToolTip gets called. Before each call, the function will try to destry it (the neccessary "except:"
              just goes to None). If the mouse coordinates are not within range of a datapoint, the function will also try to
              destroy the dialog. This way, it is ensured that the dialog gets always closed when the mouse moves away from a
              datapoint.
        """
        if event.inaxes:
            # Get coordinates on plot
            x, y = event.xdata, event.ydata
            idx_Plate = self.tabname.lbc_Conditions.GetFirstSelected()
            idx_XCondition = (self.tabname.lbc_Conditions.GetItemText(idx_Plate,0), self.tabname.lbc_Conditions.GetItemText(idx_Plate,1),"R1")
            idx_YCondition = (self.tabname.lbc_Conditions.GetItemText(idx_Plate,0), self.tabname.lbc_Conditions.GetItemText(idx_Plate,1),"R2")
            lst_YLimits = self.axes.get_ylim()
            lst_XLimits = self.axes.get_xlim()
            within_Y = (lst_YLimits[1] - lst_YLimits[0])/100 * 0.5
            within_X = (lst_XLimits[1] - lst_XLimits[0])/100 * 0.5
            int_PlateFormat = len(self.tabname.dfr_DataStructure.loc[idx_YCondition,"Normalised"]["Normalised"])
            for i in range(int_PlateFormat):
                # For the x axis (log scale), we have to adjust relative
                if x >= (self.Replicate1[i]-within_X) and x <= (self.Replicate1[i]+within_X):
                    # for the y axis, we have to adjust absolute
                    str_Well = pf.index_to_well(i+1,int_PlateFormat)
                    value = self.Replicate2[i]
                    str_SampleID = self.SampleIDs[i]
                    if pd.isna(str_SampleID) == False:
                        if len(str_SampleID) > 40:
                            str_SampleID = str_SampleID[:40] + "..."
                            str_Well += ": " + str_SampleID
                    if y >= (value - within_Y) and y <= (value + within_Y):
                        try: self.tltp.Destroy()
                        except: None
                        self.tltp = tt.dlg_ToolTip(self, str_Well)
                        self.tltp.Show()
                        break
                    else:
                        try: self.tltp.Destroy()
                        except: None
                else:
                    try: self.tltp.Destroy()
                    except: None

    # For clicking on scatter plot
    def on_click(self, event):
        if hasattr(self.tabname, "pnl_DetailPlot"):
            # Get global variables
            # check if event gives valid result:
            N = len(event.ind)
            if not N: return True
            # Get plate and sample index:
            smpl = event.ind[0]
            plate = self.tabname.lbc_Plates.GetFirstSelected()
            # Draw fresh detail plot
            if hasattr(self.tabname, "pnl_DetailPlot"):
                self.tabname.pnl_DetailPlot.draw(self.tabname.assay_data.loc[plate,"Processed"].loc[smpl,"Well"],
                        self.tabname.assay_data.loc[plate,"Processed"].loc[smpl,"SampleID"],
                        self.tabname.assay_data.loc[plate,"Processed"].loc[smpl,"Temp"],
                        self.tabname.assay_data.loc[plate,"Processed"].loc[smpl,"Fluo"], 
                        self.tabname.assay_data.loc[plate,"Processed"].loc[smpl,"RawDeriv"],
                        self.tabname.assay_data.loc[plate,"Processed"].loc[smpl,"DoFit"])
            # Write fresh label
            self.tabname.lbl_DetailsTm.SetLabel("Tm: " + str(self.tabname.assay_data.loc[plate,"Processed"].loc[smpl,"RawInflections"][0]))
            # Update tick box
            self.tabname.chk_DetailFit.SetValue(self.tabname.assay_data.loc[plate,"Processed"].loc[smpl,"DoFit"])

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

    def data_to_clipboard(self, event = None):
        lst_Wells = []
        lst_SampleIDs = []
        lst_Replicate1 = []
        lst_Replicate2 = []
        for i in range(len(self.SampleIDs)):
            if pd.isna(self.Replicate1[i]) == False:
                lst_Wells.append(pf.index_to_well(i,len(self.SampleIDs)))
                lst_SampleIDs.append(self.SampleIDs[i])
                lst_Replicate1.append(self.Replicate1[i])
                lst_Replicate2.append(self.Replicate2[i])
        pd.DataFrame({"Well":lst_Wells,"SampleID":lst_SampleIDs,"Replicate 1 (% solvent reference)":lst_Replicate1,
            "Replicate 2 (% solvent reference)":lst_Replicate2}).to_clipboard(header=True, index=False)


######################################################################
##                                                                  ##
##    #####   ##       ####   ######   ####   #####   ##  #####     ##
##    ##  ##  ##      ##  ##    ##    ##      ##  ##  ##  ##  ##    ##
##    #####   ##      ##  ##    ##    ## ###  #####   ##  ##  ##    ##
##    ##      ##      ##  ##    ##    ##  ##  ##  ##  ##  ##  ##    ##
##    ##      ######   ####     ##     ####   ##  ##  ##  #####     ##
##                                                                  ##
######################################################################

class PlotGridEPDR(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(900,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # can"t do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def draw(self,int_Samples,data,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_progress):
        self.figure.clear()
        self.data = data
        # data is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    if self.data.loc[count,"Show"] == 0:
                        str_Y = "Averages"
                        str_YSEM = "RawSEM"
                        str_YExcluded = "RawExcluded"
                        str_FitY = "RawFit"
                        str_FitPars = "RawFitPars"
                        str_FitCI = "RawFitCI"
                        str_YLabel = "Signal in A.U."
                    elif self.data.loc[count,"Show"] == 1:
                        str_Y = "Norm"
                        str_YSEM = "NormSEM"
                        str_YExcluded = "NormExcluded"
                        str_FitY = "NormFitFree"
                        str_FitPars = "NormFitFreePars"
                        str_FitCI = "NormFitFreeCI"
                        str_YLabel = "Per-cent hinhibition"
                    else:
                        str_Y = "Norm"
                        str_YSEM = "NormSEM"
                        str_YExcluded = "NormExcluded"
                        str_FitY = "NormFitConst"
                        str_FitPars = "NormFitConstPars"
                        str_FitCI = "NormFitConstCI"
                        str_YLabel = "Per-cent hinhibition"
                    self.axes = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    lst_Dose = df.moles_to_micromoles(self.data.loc[count,"Concentrations"])
                    dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl = self.include_exclude(lst_Dose, self.data.loc[count,str_Y], self.data.loc[count,str_Y+"SEM"],self.data.loc[count,str_YExcluded])
                    if self.data.loc[count,"DoFit"] == True:
                        self.axes.plot(lst_Dose, self.data.loc[count,str_FitY], label="Fit", color=cs.TMRose_Hex)
                        str_IC50 = "IC50: " + df.write_IC50(self.data.loc[count,str_FitPars][3],self.data.loc[count,"DoFit"],self.data.loc[count,str_FitCI][3])
                        self.axes.annotate(str_IC50, xy=(5, 95), xycoords="axes pixels", size=int_LabelSize)
                    if len(resp_incl) > 0:
                        self.axes.scatter(dose_incl, resp_incl, marker=".", label="Data", color=cs.TMBlue_Hex)
                        self.axes.errorbar(dose_incl, resp_incl, yerr=sem_incl, fmt="none", color=cs.TMBlue_Hex)
                    if len(resp_excl) > 0:
                        self.axes.scatter(dose_excl, resp_excl, marker=".", label="Excluded", color=cs.BgMediumHex)
                        try:
                            self.axes.errorbar(dose_excl, resp_excl, yerr=sem_excl, fmt="none", color=cs.BgMediumHex)
                        except:
                            #print(dose_excl)
                            #print(resp_excl)
                            None
                    # Sub plot title
                    self.axes.set_title(self.data.loc[count,"SampleID"])
                    self.axes.title.set_size(int_TitleSize)
                    # X Axis
                    self.axes.set_xlabel("Concentration [" + chr(181) +"M]")
                    self.axes.xaxis.label.set_size(int_LabelSize)
                    self.axes.set_xscale("log")
                    self.axes.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.axes.yaxis.label.set_size(int_LabelSize)
                    self.axes.set_ylabel(str_YLabel)
                    self.axes.tick_params(axis="y", labelsize=int_LabelSize)
                    self.axes.set_ylim([-20,120])
                    # Legend
                    #self.axes.legend(fontsize=int_LabelSize)
                    dlg_progress.Update(count)
                    count += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def include_exclude(self, dose, resp, sem, resp_excl):

        # Ensure we have a list of ALL responses, included or excluded
        resp_all = []
        for r in range(len(resp)):
            if not pd.isna(resp[r]) == True:
                resp_all.append(resp[r])
            else:
                resp_all.append(resp_excl[r])

        dose_incl = []
        resp_incl = []
        sem_incl = []
        dose_excl = []
        resp_excl = []
        sem_excl = []
        for r in range(len(resp)):
            if not pd.isna(resp[r]) == True:
                dose_incl.append(dose[r])
                resp_incl.append(resp_all[r])
                sem_incl.append(sem[r])
            else:
                dose_excl.append(dose[r])
                resp_excl.append(resp_all[r])
                sem_excl.append(sem[r])
        
        return dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl    

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

class PlotGridDSF(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(1200,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # can"t do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_progress):
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    self.axes = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    lst_Temp = dfr_Input.loc[count,"Temp"]
                    self.axes.plot(lst_Temp, dfr_Input.loc[count,"Norm"], label="Fluorescence", color="#872154")
                    #self.axes.plot(lst_Temp, dfr_Input.loc[count,"RawDeriv"], label="Fit", color="#ddcc77")
                    if dfr_Input.loc[count,"DoFit"] == True:
                        if dfr_Input.loc[count,"Method"] == "Derivative":
                            tm = dfr_Input.loc[count,"NormInfMax"]
                            tm = round(dfr_Input.loc[count,"Temp"][tm],2)
                        else:
                            tm = round(dfr_Input.loc[count,"NormFitPars"][0],2)
                        str_Tm = str(tm) + chr(176) + "C"
                    else:
                        str_Tm = "N.D."
                    self.axes.annotate(str_Tm, xy=(5, 90), xycoords="axes pixels", size=int_LabelSize)
                    # Sub plot title
                    self.axes.set_title(dfr_Input.loc[count,"SampleID"])
                    self.axes.title.set_size(int_TitleSize)
                    # X Axis
                    self.axes.set_xlabel("Temperature ("+ chr(176) + "C)")
                    self.axes.xaxis.label.set_size(int_LabelSize)
                    self.axes.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.axes.yaxis.label.set_size(int_LabelSize)
                    self.axes.set_ylabel("Norm. fluorescence")
                    self.axes.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
                    self.axes.tick_params(axis="y", labelsize=int_LabelSize)
                    #self.axes.set_ylim([-20,120])
                    # Legend
                    #self.axes.legend(fontsize=int_LabelSize)
                    count += 1
                    dlg_progress.Update(count)
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

class PlotGridNDSF(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(1100,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # can"t do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_progress):
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    self.axes = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    lst_Temp = dfr_Input.loc[count,"Temp"]
                    temps = len(lst_Temp)
                    #if dfr_Input.loc[count,"DoFit"] == True:
                    #self.axes.plot(lst_Temp, dfr_Input.loc[count,"Ratio"], label="Ratio", color="#872154")
                    lst_RatioDeriv = dfr_Input.loc[count,"RatioDeriv"][20:(temps-20)]/np.max(dfr_Input.loc[count,"RatioDeriv"][20:(temps-20)])
                    self.axes.plot(lst_Temp[20:(temps-20)], lst_RatioDeriv, label="RatioDeriv", color=cs.TMBlue_Hex)
                    lst_TempDeriv = dfr_Input.loc[count,"ScatteringDeriv"][20:(temps-20)]/np.max(dfr_Input.loc[count,"ScatteringDeriv"][20:(temps-20)])
                    self.axes.plot(lst_Temp[20:(temps-20)], lst_TempDeriv, label="ScatterDeriv", color=cs.TMRose_Hex)
                    str_Tm = str(round(dfr_Input.loc[count,"RatioInflections"][0],1)) + chr(176) + "C"
                    self.axes.annotate(str_Tm, xy=(2, 89), xycoords="axes pixels", size=int_LabelSize)
                    # Sub plot title
                    self.axes.set_title(dfr_Input.loc[count,"SampleID"])
                    self.axes.title.set_size(10)
                    # X Axis
                    self.axes.set_xlabel("Temperature ("+ chr(176) + "C)")
                    self.axes.xaxis.label.set_size(int_LabelSize)
                    self.axes.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.axes.yaxis.label.set_size(int_LabelSize)
                    self.axes.set_ylabel("Normalised derivative")
                    self.axes.tick_params(axis="y", labelsize=int_LabelSize)
                    #self.axes.set_ylim([-20,120])
                    # Legend
                    #self.axes.legend(fontsize=int_LabelSize)
                    dlg_progress.Update(count)
                    count += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

class PlotGridRATE(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(1200,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # cannot do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_progress):
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    self.axes = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    if dfr_Input.loc[count,"DoLinFit"] == True:
                        self.axes.plot(dfr_Input.loc[count,"Time"], dfr_Input.loc[count,"Signal"], label="Signal in A.U.", color="#872154")
                        self.axes.plot(dfr_Input.loc[count,"LinFitTime"], dfr_Input.loc[count,"LinFit"], label="Linear", color="#ddcc77")
                        str_Rate = str(round(dfr_Input.loc[count,"LinFitPars"][0],1)) + " 1/s"
                        self.axes.annotate(str_Rate, xy=(90, 10), xycoords="axes pixels", size=int_LabelSize)
                    # Sub plot title
                    self.axes.set_title(dfr_Input.loc[count,"SampleID"])
                    self.axes.title.set_size(10)
                    # X Axis
                    self.axes.set_xlabel("Time (s)")
                    self.axes.label.set_size(int_LabelSize)
                    self.axes.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.axes.yaxis.label.set_size(int_LabelSize)
                    self.axes.set_ylabel("Signal")
                    self.axes.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
                    self.axes.tick_params(axis="y", labelsize=int_LabelSize)
                    #self.axes.set_ylim([-20,120])
                    # Legend
                    #self.axes.legend(fontsize=int_LabelSize)
                    dlg_progress.Update(count)
                    count += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

class PlotGridDRTC(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(900,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # cannot do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_progress):
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        smpl = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > smpl: # Check whether we"re still in the dataframe
                    self.axes = self.figure.add_subplot(int_GridHeight,int_GridWidth,smpl+1)
                    lst_Time = []
                    lst_IC50s = []
                    lst_Errors = []
                    if dfr_Input.loc[smpl,"DoFit"] == True:
                        for cycle in range(len(dfr_Input.loc[smpl,"NormMean"])):
                            if dfr_Input.loc[smpl,"Show"][cycle] == 1:
                                str_Fit = "Free"
                            else:
                                str_Fit = "Const"
                            lst_IC50s.append(dfr_Input.loc[smpl,"NormFit"+str_Fit+"Pars"][cycle][3])
                            lst_Errors.append(dfr_Input.loc[smpl,"NormFit"+str_Fit+"Errors"][cycle][3])
                            lst_Time.append(dfr_Input.loc[smpl,"Time"][cycle])
                        self.axes.plot(lst_Time, lst_IC50s, label="IC50 in uM", color="#872154")
                        self.axes.errorbar(lst_Time, lst_IC50s, yerr=lst_Errors,fmt="none", color="#872154", elinewidth=0.3, capsize=2)
                        # self.axes.plot(dfr_Input.loc[smpl,"LinFitTime"], dfr_Input.loc[smpl,"LinFit"], label="Linear", color="#ddcc77")
                        # str_Kinetics = str(round(dfr_Input.loc[smpl,"LinFitPars"][0],1)) + " 1/s"
                        # self.axes.annotate(str_Kinetics, xy=(5, 98), xycoords="axes pixels", size=int_LabelSize)
                    # Sub plot title
                    self.axes.set_title(dfr_Input.loc[smpl,"SampleID"])
                    self.axes.title.set_size(10)
                    # X Axis
                    self.axes.set_xlabel("Time (s)")
                    self.axes.xaxis.label.set_size(int_LabelSize)
                    self.axes.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.axes.yaxis.label.set_size(int_LabelSize)
                    self.axes.set_ylabel("IC50 ("+chr(181)+"M)")
                    self.axes.set_ylim(bottom=0)
                    self.axes.set_xlim(left=-50)
                    #self.axes.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
                    self.axes.tick_params(axis="y", labelsize=int_LabelSize)
                    #self.axes.set_ylim([-20,120])
                    # Legend
                    #self.axes.legend(fontsize=int_LabelSize)
                smpl += 1
                dlg_progress.Update(smpl)
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)
        
    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

class PlotGridDPandFit(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(900,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # can"t do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def draw(self,int_Samples,data,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_progress):
        self.figure.clear()
        self.data = data
        # data is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    if self.data.loc[count,"Show"] == 0:
                        str_Y = "Averages"
                        str_YSEM = "RawSEM"
                        str_YExcluded = "RawExcluded"
                        str_FitY = "RawFit"
                        str_FitPars = "RawFitPars"
                        str_FitCI = "RawFitCI"
                        str_YLabel = "Normalised initial rate"
                    elif self.data.loc[count,"Show"] == 1:
                        str_Y = "Norm"
                        str_YSEM = "NormSEM"
                        str_YExcluded = "NormExcluded"
                        str_FitY = "NormFitFree"
                        str_FitPars = "NormFitFreePars"
                        str_FitCI = "NormFitFreeCI"
                        str_YLabel = "Normalised initial rate"
                    else:
                        str_Y = "Norm"
                        str_YSEM = "NormSEM"
                        str_YExcluded = "NormExcluded"
                        str_FitY = "NormFitConst"
                        str_FitPars = "NormFitConstPars"
                        str_FitCI = "NormFitConstCI"
                        str_YLabel = "Normalised initial rate"
                    self.axes = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    lst_Dose = df.moles_to_micromoles(self.data.loc[count,"Concentrations"])
                    dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl = self.include_exclude(lst_Dose, self.data.loc[count,"RateFit"]["viNorm"], self.data.loc[count,"RateFit"]["Error"],self.data.loc[count,"RateFit"]["Excluded"])
                    if self.data.loc[count,"DoFit"] == True:
                        self.axes.plot(lst_Dose, self.data.loc[count,"RateFit"]["Fit"], label="Fit", color=cs.TMRose_Hex)
                        str_IC50 = "IC50: " + df.write_IC50(self.data.loc[count,"RateFit"]["Pars"][3],self.data.loc[count,"RateFit"]["DoFit"],self.data.loc[count,"RateFit"]["CI"][3])
                        self.axes.annotate(str_IC50, xy=(5, 95), xycoords="axes pixels", size=int_LabelSize)
                    if len(resp_incl) > 0:
                        self.axes.scatter(dose_incl, resp_incl, marker=".", label="Data", color=cs.TMBlue_Hex)
                        ylims = self.axes.get_ylim()
                        self.axes.errorbar(dose_incl, resp_incl, yerr=sem_incl, fmt="none", color=cs.TMBlue_Hex)
                    if len(resp_excl) > 0:
                        self.axes.scatter(dose_excl, resp_excl, marker=".", label="Excluded", color=cs.BgMediumHex)
                        try:
                            self.axes.errorbar(dose_excl, resp_excl, yerr=sem_excl, fmt="none", color=cs.BgMediumHex)
                        except:
                            #print(dose_excl)
                            #print(resp_excl)
                            None
                    # Sub plot title
                    self.axes.set_title(self.data.loc[count,"SampleID"])
                    self.axes.title.set_size(int_TitleSize)
                    # X Axis
                    self.axes.set_xlabel("Concentration [" + chr(181) +"M]")
                    self.axes.xaxis.label.set_size(int_LabelSize)
                    self.axes.set_xscale("log")
                    self.axes.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.axes.yaxis.label.set_size(int_LabelSize)
                    self.axes.set_ylabel(str_YLabel)
                    self.axes.tick_params(axis="y", labelsize=int_LabelSize)
                    self.axes.set_ylim([ylims[0],ylims[1]])
                    # Legend
                    #self.axes.legend(fontsize=int_LabelSize)
                    dlg_progress.Update(count)
                    count += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def include_exclude(self, dose, resp, sem, excluded):

        # Ensure we have a list of ALL responses, included or excluded
        dose_incl = []
        resp_incl = []
        sem_incl = []
        dose_excl = []
        resp_excl = []
        sem_excl = []
        for r in range(len(excluded)):
            if excluded[r] == False:
                dose_incl.append(dose[r])
                resp_incl.append(resp[r])
                sem_incl.append(sem[r])
            else:
                dose_excl.append(dose[r])
                resp_excl.append(resp[r])
                sem_excl.append(sem[r])
        
        return dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl    

    def plot_to_clipboard(self, event = None):
        shared_plot_to_clipboard(self)

    def plot_to_png(self, event = None):
        shared_plot_to_png(self)

########################################################################################################
##                                                                                                    ##
##     #####   ####   ##    ##  ##    ##   ####   ##  ##    ######  ##  ##  ##  ##   #####   #####    ##
##    ##      ##  ##  ###  ###  ###  ###  ##  ##  ### ##    ##      ##  ##  ### ##  ##      ##        ##
##    ##      ##  ##  ########  ########  ##  ##  ######    ####    ##  ##  ######  ##       ####     ##
##    ##      ##  ##  ## ## ##  ## ## ##  ##  ##  ## ###    ##      ##  ##  ## ###  ##          ##    ##
##     #####   ####   ##    ##  ##    ##   ####   ##  ##    ##       ####   ##  ##   #####  #####     ##
##                                                                                                    ##
########################################################################################################

def shared_plot_to_clipboard(Plot):
    """
    Copy the plot to clipboard.

    The window gets frozen, the background colour changed to white, the canvas redrawn, saved into a wx.BitmapDataObject, 
    then the canvas redrawn with the original background colour, then the window is thawed again.
    After that, the BitmapDataObject is handed to the clipboard.
    """
    Plot.Freeze()
    Plot.figure.set_facecolor(cs.WhiteHex)
    Plot.canvas.draw()
    # Convert plot to PIL image object, then to wx.BitmapObject
    pil_Plot = Image.frombytes("RGB", Plot.canvas.get_width_height(), Plot.canvas.tostring_rgb())
    int_Width, int_Height = pil_Plot.size
    Plot.obj_Plot = wx.BitmapDataObject()
    Plot.obj_Plot.SetBitmap(wx.Bitmap.FromBuffer(int_Width, int_Height, pil_Plot.tobytes()))
    Plot.figure.set_facecolor(cs.BgUltraLightHex)
    Plot.canvas.draw()
    # Hand to clipboard
    if wx.TheClipboard.Open():
        wx.TheClipboard.Clear()
        wx.TheClipboard.SetData(Plot.obj_Plot)
        wx.TheClipboard.Close()
    else:
        msg.warn_clipboard_error(Plot)
    Plot.Thaw()

def shared_plot_to_png(Plot):
    """
    Saves graph as PNG file using matplotlib's built in methods.
    
    First, the user is asked to specify a path via wx.FileDialog.

    The window gets frozen, the background colour changed to white, the canvas redrawn, saved to the specified path, 
    then the canvas redrawn with the original background colour, then the window is thawed again.
    After that, the BitmapDataObject is handed to the clipboard.
    """
    dlg_PlatePlotPNG = wx.FileDialog(Plot, "Save plot as", wildcard="PNG files(*.png)|*.png", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

    if dlg_PlatePlotPNG.ShowModal() == wx.ID_OK:
        save_path = dlg_PlatePlotPNG.GetPath()
        # Check if save_path ends in .png. If so, remove
        if save_path[-1:-4] == ".png":
            save_path = save_path[:len(save_path)]
        Plot.Freeze()
        Plot.figure.set_facecolor(cs.WhiteHex)
        Plot.canvas.draw()
        try:
            Plot.figure.savefig(save_path, dpi=None, facecolor="w", edgecolor="w", orientation="portrait", format=None,
                transparent=False, bbox_inches=None, pad_inches=0.1)
            msg.info_save_success()
        except:
            msg.warn_permission_denied()
        Plot.figure.set_facecolor(cs.BgUltraLightHex)
        Plot.canvas.draw()
        Plot.Thaw()
    else:
        return

def zooming(Plot, event):
    Plot.in_zoom = True

def zoom_start(Plot, event):
    SetCursor(wx.Cursor(wx.CURSOR_MAGNIFIER))
    try:
        Plot.ZoomFrame.Destroy()
        Plot.ZoomFrame = None
    except:
        None
    Plot.zoomed = False
    Plot.ZoomStartX = round(event.xdata,0)
    Plot.ZoomStartY = round(event.ydata,0)
    Plot.OriginalXLimits = Plot.axes.get_xlim()
    Plot.OriginalYLimits = Plot.axes.get_ylim()
    Plot.ZoomFrameOrigin = wx.Point(wx.GetMousePosition()[0]+2,wx.GetMousePosition()[1]+2)
    Plot.ZoomFrame = ZoomFrame(Plot)
    Plot.ZoomFrame.Show()

def zoom_button_lift(Plot, event):
    SetCursor(wx.Cursor(wx.CURSOR_ARROW))
    Plot.ZoomEndX = round(event.xdata,0)
    Plot.ZoomEndY = round(event.ydata,0)
    Plot.in_zoom = False
    Plot.zoomed = True
    try:
        Plot.ZoomFrame.Destroy()
        Plot.ZoomFrame = None
    except:
        None
    Plot.draw()

def zoom_reset(Plot, event):
    try:
        Plot.ZoomFrame.Destroy()
        Plot.ZoomFrame = None
    except:
        None
    Plot.in_zoom = False
    Plot.zoomed = False
    Plot.draw()

def leave_figure(Plot, event):
    SetCursor(wx.Cursor(wx.CURSOR_ARROW))
    if Plot.in_zoom == True:
        Plot.in_zoom = False 
        try:
            if not event.xdata == None:
                Plot.ZoomEndX = round(event.xdata,0)
            if not event.ydata == None:
                Plot.ZoomEndY = round(event.ydata,0)
            Plot.zoomed = True
            Plot.ZoomFrame.Destroy()
            Plot.ZoomFrame = None
            Plot.draw()
        except:
            None
        
def zoom_drag_frame(Plot, event):
    if Plot.in_zoom == True and hasattr(Plot.ZoomFrame, "Position") == True:
        mouseposition = wx.GetMousePosition()
        size_x = abs(mouseposition[0] - Plot.ZoomFrameOrigin[0]) - 2
        size_y = abs(mouseposition[1] - Plot.ZoomFrameOrigin[1]) - 2
        new_size = wx.Size(size_x, size_y)
        if mouseposition[0] < Plot.ZoomFrameOrigin[0]:
            new_x = mouseposition[0] + 2
        else:
            new_x = Plot.ZoomFrameOrigin[0] - 2
        if mouseposition[1] < Plot.ZoomFrameOrigin[1]:
            new_y = mouseposition[1] + 2
        else:
            new_y = Plot.ZoomFrameOrigin[1] - 2
        new_position = wx.Point(new_x, new_y)
        Plot.ZoomFrame.Redraw(new_position, new_size)
        Plot.SetFocus()


######################################################################################################
##                                                                                                  ##
##     #####   ####   ##  ##  ######  ######  ##  ##  ######    ##    ##  ######  ##  ##  ##  ##    ##
##    ##      ##  ##  ### ##    ##    ##      ##  ##    ##      ###  ###  ##      ### ##  ##  ##    ##
##    ##      ##  ##  ######    ##    ####     ####     ##      ########  ####    ######  ##  ##    ##
##    ##      ##  ##  ## ###    ##    ##      ##  ##    ##      ## ## ##  ##      ## ###  ##  ##    ##
##     #####   ####   ##  ##    ##    ######  ##  ##    ##      ##    ##  ######  ##  ##   ####     ##
##                                                                                                  ##
######################################################################################################

class PlotContextMenu(wx.Menu):
    def __init__(self, parent, mouse_x = None, mouse_y = None):
        super(PlotContextMenu, self).__init__()
        """
        Context menu to copy, export and copy the data of plots.
        """
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.parent = parent

        # Only show magnify/rest zoom options if appropriate
        if hasattr(self.parent, "zooming") == True:
            self.mi_Magnify = wx.MenuItem(self, wx.ID_ANY, u"Zoom", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_Magnify.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Zoom.ico"))
            self.Append(self.mi_Magnify)
            self.Bind(wx.EVT_MENU, self.parent.zooming, self.mi_Magnify)

            self.mi_zoom_reset = wx.MenuItem(self, wx.ID_ANY, u"Reset zoom", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_zoom_reset.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\UnZoom.ico"))
            self.Append(self.mi_zoom_reset)
            self.Bind(wx.EVT_MENU, self.parent.zoom_reset, self.mi_zoom_reset)

        if hasattr(self.parent, "ShowMarker") == True:
            self.mi_ShowMarker = wx.MenuItem(self, wx.ID_ANY, u"Show marker(s)", wx.EmptyString, wx.ITEM_NORMAL)
            if self.parent.ShowMarker == True:
                self.mi_ShowMarker.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
            else:
                self.mi_ShowMarker.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxUnTicked.ico"))
            self.Append(self.mi_ShowMarker)
            self.Bind(wx.EVT_MENU, self.toggle_marker, self.mi_ShowMarker)

        if hasattr(self.parent, "set_to_start") == True:
            self.mi_Start = wx.MenuItem(self, wx.ID_ANY, u"Start", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_Start.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\LeftBorder.ico"))
            self.Append(self.mi_Start)
            self.Bind(wx.EVT_MENU, lambda event: self.parent.set_to_start(event, mouse_x), self.mi_Start)
        if hasattr(self.parent, "set_to_stop") == True:
            self.mi_Stop = wx.MenuItem(self, wx.ID_ANY, u"Stop", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_Stop.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\RightBorder.ico"))
            self.Append(self.mi_Stop)
            self.Bind(wx.EVT_MENU, lambda event: self.parent.set_to_stop(event, mouse_x), self.mi_Stop)

        if hasattr(self.parent, "Zooming") == True or hasattr(self.parent, "ShowMarker") == True:
            self.AppendSeparator()

        self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy plot image", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\CopyPlot.ico"))
        self.Append(self.mi_Copy)
        self.Bind(wx.EVT_MENU, self.parent.plot_to_clipboard, self.mi_Copy)

        self.mi_Export = wx.MenuItem(self, wx.ID_ANY, u"Export plot image", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Export.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\SaveAs.ico"))
        self.Append(self.mi_Export)
        self.Bind(wx.EVT_MENU, self.parent.plot_to_png, self.mi_Export)
        
        self.mi_PlotData = wx.MenuItem(self, wx.ID_ANY, u"Copy plot data", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_PlotData.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\CopyData.ico"))
        self.Append(self.mi_PlotData)
        self.Bind(wx.EVT_MENU, self.parent.data_to_clipboard, self.mi_PlotData)

        if hasattr(self.parent, "SummaryPlot") == True:
            if self.parent.SummaryPlot == True:
                self.AppendSeparator()
                self.mi_ChangeTitle = wx.MenuItem(self, wx.ID_ANY, u"Change Title", wx.EmptyString, wx.ITEM_NORMAL)
                #self.mi_ChangeTitle.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\CopyData.ico"))
                self.Append(self.mi_ChangeTitle)
                self.Bind(wx.EVT_MENU, self.change_title, self.mi_ChangeTitle)

    def change_title(self, event):
        event.Skip()
        dlg_ChangeTitle = ChangeTitleDialog(self.parent)
        dlg_ChangeTitle.Show()
    
    def toggle_marker(self, event):
        if self.parent.ShowMarker == True:
            self.parent.ShowMarker = False
        else:
            self.parent.ShowMarker = True
        self.parent.draw()

########################################################################################
##                                                                                    ##
##    ######   ####    ####   ##    ##    ######  #####    ####   ##    ##  ######    ##
##       ##   ##  ##  ##  ##  ###  ###    ##      ##  ##  ##  ##  ###  ###  ##        ##
##      ##    ##  ##  ##  ##  ########    ####    #####   ######  ########  ####      ##
##     ##     ##  ##  ##  ##  ## ## ##    ##      ##  ##  ##  ##  ## ## ##  ##        ##
##    ######   ####    ####   ##    ##    ##      ##  ##  ##  ##  ##    ##  ######    ##
##                                                                                    ##
########################################################################################

class ZoomFrame(wx.Dialog):
    def __init__(self, parent, position = None, size = wx.Size(1,1)):
        wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Tooltip", pos=wx.DefaultPosition, size = size, style = wx.STAY_ON_TOP)
        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )
        self.SetBackgroundColour(cs.White)
        self.parent = parent
        if position == None:
            self.Position = self.parent.ZoomFrameOrigin
        else:
            self.Position = position
        self.Size = size
        self.SetTransparent(75)
        self.szr_Main = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Main = wx.StaticText(self, wx.ID_ANY, u"LABEL", wx.DefaultPosition, self.Size, 0)
        self.szr_Main.Add(self.lbl_Main,0,wx.ALL,0)
        self.SetSizer(self.szr_Main)
        self.Layout()
        self.szr_Main.Fit(self)

        self.SetPosition(self.Position)

    def __del__( self ):
        pass

    def Redraw(self, position, size):
        self.Position = position
        self.Size = size
        self.SetSize(self.Size)
        self.SetPosition(self.Position)
        self.Layout()

################################################################################################
##                                                                                            ##
##     #####  ##  ##   ####   ##  ##   #####  ######    ######  ##  ######  ##      ######    ##
##    ##      ##  ##  ##  ##  ### ##  ##      ##          ##    ##    ##    ##      ##        ##
##    ##      ######  ######  ######  ## ###  ####        ##    ##    ##    ##      ####      ##
##    ##      ##  ##  ##  ##  ## ###  ##  ##  ##          ##    ##    ##    ##      ##        ##
##     #####  ##  ##  ##  ##  ##  ##   ####   ######      ##    ##    ##    ######  ######    ##
##                                                                                            ##
################################################################################################

class ChangeTitleDialog(wx.Dialog):
    def __init__(self, plot):
        wx.Dialog.__init__ (self, parent = plot, id = wx.ID_ANY, title = u"Tooltip", pos=wx.DefaultPosition, size = wx.Size(114,27), style = wx.STAY_ON_TOP)

        self.SetBackgroundColour(cs.White)
        self.Plot = plot

        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_Title = wx.TextCtrl(self, wx.ID_ANY, self.Plot.title, wx.DefaultPosition, wx.Size(100,22), wx.TE_PROCESS_ENTER )
        self.szr_Surround.Add(self.txt_Title,0,wx.ALL,1)
        self.btn_TinyX = btn.TinyXButton(self)
        self.szr_Surround.Add(self.btn_TinyX, 0, wx.ALL, 1)

        self.SetSizer(self.szr_Surround)
        self.Layout()
        self.szr_Surround.Fit(self)

        self.Centre( wx.BOTH )
        MousePosition = wx.GetMousePosition()
        TooltipPosition = wx.Point(MousePosition[0] - self.GetSize()[0], MousePosition[1]) # (x,y)
        self.SetPosition(TooltipPosition)
        self.SetFocus()
        self.Bind(wx.EVT_KILL_FOCUS, self.End)
        self.Bind(wx.EVT_KEY_DOWN, self.Escape)
        self.btn_TinyX.Bind(wx.EVT_BUTTON, self.End)
        self.btn_TinyX.Bind(wx.EVT_KEY_DOWN, self.Escape)
        self.txt_Title.Bind(wx.EVT_KEY_DOWN, self.Escape)
        self.txt_Title.Bind(wx.EVT_TEXT_ENTER, self.UpdateTitle)

    def __del__( self ):
        pass

    def UpdateTitle(self, event):
        event.Skip()
        self.Plot.title = self.txt_Title.GetLineText(0)
        self.Plot.draw()
        self.Destroy()

    def End(self, event):
        self.Destroy()

    def Escape(self, event):
        event.Skip()
        if event.GetKeyCode() == 27:
            self.Destroy()
