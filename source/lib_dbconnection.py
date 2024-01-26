"""
Contains dialog box for database connections.

    Classs
        OXFSCARABdb
        DBCredentials
        DBLookupCompound

    Functions
        sqllist
        format_date
"""

import wx
import wx.xrc
import wx.grid
import os
import lib_custombuttons as btn
import lib_colourscheme as cs
import oracledb as odb

import pandas as pd

class OXFSCARABdb:
    """
    A class providing connectivity to CMD-Oxford Scarab database
    Based on code kindly provided by Lucas Martins Ferreira
    
    Originally, this included "admin" as a usertype and a lot of other tings.
    This was omitted from this class since it is not required for this application.
    
    """
    def __init__(self, username, password):
        
        self.connected = False
        self.error = ""

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        client_dir = os.path.join(dir_path, "instantclient_21_8")

        if not os.path.isdir(client_dir):
            self.connected = False
            self.error = u"client_not_found"
            return
        else:
            try:
                odb.init_oracle_client(lib_dir=client_dir)
            except:
                self.connected = False
                self.error = u"client_not_initialised"
                return
            try:
                self.conn = odb.connect(user = username,
                                        password = password,
                                        dsn = "delphi.cmd.ox.ac.uk/CMDpdb")
                self.connected = True
            except odb.Error as err:
                error_obj, = err.args
                self.error = error_obj.full_code
                self.connected = False
                return
            except Exception as ex:
                self.error = ex
                self.connected = False
                return
            except: 
                self.connected = False
                self.error = "generic"
                return
    
    def close(self):

        if self.connected == True:
            try:
                self.conn.close()
                #print("Connection closed")
                return "closed"
            except:
                wx.MessageBox(message = u"The connection could not be closed. This could be due to the connection being severed already or not having been correctly established in the first place.",
                              caption = "Failed to close connection",
                              style = wx.OK|wx.ICON_INFORMATION)
                
                return "open"
        else:
            wx.MessageBox(message = u"The connection could not be closed. This could be due to the connection being severed already or not having been correctly established in the first place.",
                              caption = "Failed to close connection",
                              style = wx.OK|wx.ICON_INFORMATION)
            return "closed"

class DBCredentials(wx.Dialog):
    
    def __init__(self, parent):

        wx.Frame.__init__ (self, parent, id = wx.ID_ANY, title = wx.EmptyString,
                           pos = wx.DefaultPosition, size = wx.Size(305,130),
                           style = wx.TAB_TRAVERSAL)


        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        dbicon = os.path.join(dir_path, u"other", u"db_SCARAB.png")

        df_msgs = pd.read_csv(os.path.join(dir_path, "dbmsgs.csv"))
        self.msgs = df_msgs.set_index("Code")

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        self.parent = parent

        self.szr_Frame = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Panel = wx.Panel(self)
        self.pnl_Panel.SetBackgroundColour(cs.BgMedium)

        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)

        # TITLE BAR #####################################################################
        self.pnl_TitleBar = wx.Panel(self.pnl_Panel)
        self.pnl_TitleBar.SetBackgroundColour(cs.BgUltraDark)
        self.pnl_TitleBar.SetForegroundColour(cs.White)
        self.szr_TitleBar = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Title = wx.StaticText(self.pnl_TitleBar, label= u"Connect to database")
        self.lbl_Title.Wrap(-1)
        self.szr_TitleBar.Add( self.lbl_Title, 0, wx.ALL, 5 )
        self.szr_TitleBar.Add((0,0), 1, wx.EXPAND, 5)
        self.btn_X = btn.CustomBitmapButton(self.pnl_TitleBar,
                                            name = "small_x",
                                            index = 0,
                                            size = (25,25),
                                            pathaddendum = u"titlebar")
        self.szr_TitleBar.Add(self.btn_X,0,wx.ALL,0)
        self.pnl_TitleBar.SetSizer(self.szr_TitleBar)
        self.pnl_TitleBar.Layout()
        self.szr_Surround.Add(self.pnl_TitleBar, 0, wx.EXPAND, 5)

        # Sizer for inputs
        self.szr_InputFrame = wx.BoxSizer(wx.HORIZONTAL)
        self.bmp_DB = wx.StaticBitmap(self.pnl_Panel,
                                      size = wx.Size(64,64),
                                      bitmap = wx.Bitmap(dbicon, wx.BITMAP_TYPE_ANY))
        self.szr_InputFrame.Add(self.bmp_DB, 0, wx.ALL, 10)
        self.szr_Right = wx.BoxSizer(wx.VERTICAL)
        self.szr_Right.Add((225,10), 0,0,0)
        self.szr_Inputs = wx.FlexGridSizer(2, 3, 0, 0)
        self.szr_Inputs.SetFlexibleDirection( wx.BOTH )
        self.szr_Inputs.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
        self.lbl_Username = wx.StaticText(self.pnl_Panel,
                                       label = u" Username",
                                       size = wx.Size(100,-1))
        self.szr_Inputs.Add(self.lbl_Username, 0, 0, 0)
        self.szr_Inputs.Add((5,10), 0, 0, 0)
        self.lbl_Password = wx.StaticText(self.pnl_Panel,
                                       label = u" Password",
                                       size = wx.Size(100,-1))
        self.szr_Inputs.Add(self.lbl_Password, 0, 0, 0)
        self.txt_Username = wx.TextCtrl(self.pnl_Panel,
                                        value = os.getlogin(),
                                        style = wx.TE_PROCESS_ENTER,
                                        size = wx.Size(100,-1))
        self.szr_Inputs.Add(self.txt_Username, 0, 0, 0)
        self.szr_Inputs.Add((5,-1), 0, 0, 0)
        self.txt_Password = wx.TextCtrl(self.pnl_Panel,
                                        value = u"",
                                        style = wx.TE_PASSWORD|wx.TE_PROCESS_ENTER,
                                        size = wx.Size(100,-1))
        self.szr_Inputs.Add(self.txt_Password, 0, 0, 0)
        self.txt_Password.SetFocus()
        self.szr_Right.Add(self.szr_Inputs, 0, 0, 0)
        self.szr_Right.Add((225,10), 0,0,0)
        self.szr_Buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Buttons.Add((-1,25), 1, wx.EXPAND, 0)
        self.btn_Login = wx.Button(self.pnl_Panel,
                                   label = u"Log in")
        self.szr_Buttons.Add(self.btn_Login, 0, wx.ALL, 5)
        self.btn_Cancel = btn.CustomBitmapButton(self.pnl_Panel,
                                                 name = u"Cancel",
                                                 index = 1,
                                                 size = (100,30),
                                                 tooltip = u"Cancel login attempt")
        self.szr_Buttons.Add(self.btn_Cancel, 0, wx.ALL, 5)
        self.szr_Buttons.Add((10,10), 0,0,0)
        self.szr_Right.Add(self.szr_Buttons, 0, wx.EXPAND, 5)
        self.szr_Right.Add((225,10), 0,0,0)
        self.szr_InputFrame.Add(self.szr_Right, 0, wx.ALL, 0)
        self.szr_Surround.Add(self.szr_InputFrame, 0, wx.ALL, 0)
        
        self.pnl_Panel.SetSizer(self.szr_Surround)
        self.pnl_Panel.Layout()
        self.szr_Frame.Add(self.pnl_Panel,0,wx.EXPAND,0)

        self.SetSizer(self.szr_Frame)
        self.Layout()
        self.Center(wx.BOTH)

        # Required for window dragging:
        self.delta = wx.Point(0,0)
        self.pnl_TitleBar.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.lbl_Title.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.dragging = False

        self.btn_Login.Bind(wx.EVT_BUTTON, self.login)
        self.btn_Cancel.Bind(wx.EVT_BUTTON, self.cancel)
        self.btn_X.Bind(wx.EVT_BUTTON, self.cancel)
        self.txt_Username.Bind(wx.EVT_TEXT_ENTER, self.login)
        self.txt_Password.Bind(wx.EVT_TEXT_ENTER, self.login)

    def __del__(self):
        pass

    # The following three function are taken from a tutorial on the wxPython Wiki:
    # https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
    # They have been modified if and where appropriate.

    def on_mouse_move(self, event):
        """
        Changes position of window based on mouse movement
        if left mouse button is down on titlebar.
        """
        if self.dragging == True:
            if event.Dragging() and event.LeftIsDown():
                x,y = self.ClientToScreen(event.GetPosition())
                newPos = (x - self.delta[0], y - self.delta[1])
                self.Move(newPos)

    def on_left_down(self, event):
        """
        Initiates all required properties for window dragging.
        """
        self.CaptureMouse()
        x, y = self.ClientToScreen(event.GetPosition())
        originx, originy = self.GetPosition()
        dx = x - originx
        dy = y - originy
        self.delta = [dx, dy]
        self.dragging = True

    def on_left_up(self, event):
        """
        Releases mouse capture and resets property for window
        dragging.
        """
        if self.HasCapture():
            self.ReleaseMouse()
        self.dragging = False

    def cancel(self, event):
        """
        Closes window without changing parent object's
        layout dataframe.
        """
        if event is not None:
            event.Skip()
        self.parent.db_connection = None
        self.parent.db_comment = "cancel"
        self.EndModal(True)

    def on_enter(self, event):
        self.login(event = None)

    def login(self, event):
        """
        Event handler.
        Runs login to databas
        """

        username = self.txt_Username.GetValue()
        password = self.txt_Password.GetValue()
        # Perform checks to ensure form is filled out:
        if username == "":
            wx.MessageBox(message = u"You have not entered a username. Cannot connect to database",
                          caption = u"No username",
                          style = wx.OK|wx.ICON_WARNING)
            return None
        elif password =="":
            wx.MessageBox(message = u"You have not entered a password. Cannot connect to database",
                          caption = u"No password",
                          style = wx.OK|wx.ICON_WARNING)
            return None

        self.parent.db_connection = OXFSCARABdb(username = username,
                                                password = password)
        if self.parent.db_connection.connected == True:
            self.parent.db_comment = "success"                   
            self.EndModal(True)
        else:
            error = self.parent.db_connection.error
            if error in self.msgs.index:
                wx.MessageBox(message = self.msgs.loc[error,"Message"],
                              caption = self.msgs.loc[error,"Caption"],
                              style = wx.OK|wx.ICON_WARNING)

            self.parent.db_connection = None
            self.parent.db_comment = "error"
            return None

def sqllist(lst):
    """
    Turns a list into a string for SQL query
    """
    sql = ""
    for item in lst:
        sql += "'" + item +"', "
    # We're adding one more comma and space than we need:
    return sql[:-2]

def format_date(date):
    """
    Helper function to convert date from ISO8601 format
    to default format for oracle database
    """
    day = date[8:10]
    month = date[5:7]
    year = date[0:4]

    months = {"01":"JAN",
              "02":"FEB",
              "03":"MAR",
              "04":"APR",
              "05":"MAY",
              "06":"JUN",
              "07":"JUL",
              "08":"AUG",
              "09":"SEP",
              "10":"OCT",
              "11":"NOV",
              "12":"DEC"}

    return day + "-" + months[month] + "-" + year
