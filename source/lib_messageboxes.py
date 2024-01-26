"""
Contains functions to display message boxes. Serves to make process easier.
Arguments for all functions are optional unless they are named.

Functions:

    info_no_analysis
    warn_save_error_no_analysis
    info_save_success
    warn_missing_datafile
    warn_not_transferfile
    warn_not_datafile
    warn_no_layout
    warn_no_transfer
    warn_clipboard_error
    info_missing_details
    warn_identical_boundaries
    ItemAlreadyExists
    query_mismatch
    query_redo_analysis
    query_change_sample_source
    query_discard_changes
    query_close_program
    warn_permission_denied
    query_connect_db
    info_all_verified

"""

import wx

def info(parent, message, caption="Note"):
    """
    Generic wrapper to make message dialogue.

    Arguments:
    message => string. The actual message to display
    caption -> string. Caption of the message box
    """
    dlg_Info = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_WARNING)
    dlg_Info.ShowModal()
    dlg_Info.Destroy()

def info_no_analysis(*args):
    """
    Displays message box if user tries to display a page that
    requires a completed analysis without having completed one.
    """
    message = wx.MessageBox(u"Cannot display this page, no analysis has been performed.",
                            caption = u"No can do",
                            style = wx.OK|wx.ICON_INFORMATION)

def warn_save_error_no_analysis(*args):
    """
    Displays message box if user tries to save an analysis without
    having completed one.
    """
    message = wx.MessageBox(u"Cannot save project: No analysis was performed.",
                            caption = u"Save Error",
                            style = wx.OK|wx.ICON_WARNING)

def info_save_success(*args):
    """
    Displays message box after project has been successfully saved.
    """
    message = wx.MessageBox(u"File saved successfully.",
                            caption = u"Save Success",
                            style = wx.OK|wx.ICON_INFORMATION)

def warn_missing_datafile(*args):
    """
    Displays message box if user tries to perform analysis w/o having
    assigned data files.
    """
    message = wx.MessageBox(u"Cannot proceed: No data files assigned",
                            caption = u"No data files assigned",
                            style = wx.OK|wx.ICON_WARNING)

def warn_not_transferfile(*args):
    """
    Displays message box if loaded file does not match expected file type.
    """
    message = wx.MessageBox(u"The file you loaded was not a correct transfer file",
                            caption = u"File error",
                            style = wx.OK|wx.ICON_WARNING)
    
def warn_missing_column(column):
    """
    Displays message box if a required column is missing from the transfer file.
    """
    message = wx.MessageBox(u"The transfer file could not be parsed."
                            + "\nA required column is missing from the transfer file:"
                            + f"\n{column}",
                            caption = u"Missing column",
                            style = wx.OK|wx.ICON_WARNING)

def warn_not_datafile(*args):
    """
    Displays message box if loaded file does not match expected file type.
    """
    message = wx.MessageBox(u"The file you loaded was eiter:\n"
                            + u"\ni. not a correct raw data file or"
                            + u"\nii. not formatted correctly\n"
                            + u"\nand therefore could not be parsed."
                            + u"\nCheck the file and try again.",
                            caption = u"File error",
                            style = wx.OK|wx.ICON_WARNING)

def warn_no_layout(*args):
    """
    Displays message box if user tries to perform analysis without a plate layout.
    """
    message = wx.MessageBox(u"You have not defined a plate layout. Cannot proceed with analysis.",
                            caption = u"No layout defined",
                            style = wx.OK|wx.ICON_INFORMATION)

def warn_no_transfer(*args):
    """
    Displays message box if user tries to perform analysis with missing files.
    """
    message = wx.MessageBox(u"Cannot proceed: No transfer file loaded",
                            caption = u"No transfer file loaded",
                            style = wx.OK|wx.ICON_WARNING)

def warn_clipboard_error(*args):
    """
    Displays message box on clipboard error.
    """
    message = wx.MessageBox(u"Could not open the clipboard. Please try again",
                            caption = u"Clipboard Error",
                            style = wx.OK|wx.ICON_WARNING)

def info_missing_details(*args):
    """
    Displays message box if assay details are incomplete.
    """
    message = wx.MessageBox(u"One or more fields have not been filled out, please check",
                            caption = u"Missing details",
                            style = wx.OK|wx.ICON_INFORMATION)

def warn_identical_boundaries(*args):
    """
    Displays message box if assay details are incomplete.
    """
    message = wx.MessageBox(u"The boundaries you have selected are identical. Please choose different points.",
                            caption = u"Identical boundaries",
                            style = wx.OK|wx.ICON_WARNING)

def ItemAlradyExists(item):
    """
    Displays message box notifying user item already exists.

    Arguuments:
        item -> string
    """
    message = wx.MessageBox(u"The " + item + " already exsists.",
                            caption = u"Item already exists",
                            style = wx.OK|wx.ICON_WARNING)

def info_plateformat_mismatch(*args):
    """
    Displays message box if plate formats within analysis do not match.
    """
    message = wx.MessageBox(u"The Plate format of the entry you want to create does not match the previous entries."
                            + u"\nAll entries must be of the same format.",
                            caption = u"Plate formats do not match",
                            style = wx.OK|wx.ICON_INFORMATION)

def query_mismatch(criterion, item):
    """
    Displays message box asking user if they want to clear a mismatching item.

    Arguments:
        criterion -> string, the criterion by which things are compared
        item -> string; the mismatchin item(s).
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox(u"The " + criterion + " do no match. Do you want to clear the current " + item + "?",
                            caption = u"Mismatch",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def query_redo_analysis(*args):
    """
    Displays message box asking user if they want to re-analyse data.
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox(u"Assay details or transfer/data files have been changed."
                            + u" Do you want to re-analyse the data?",
                            caption = u"Re-analyse data?",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def query_change_sample_source(*args):
    """
    Displays message box asking user to confirm sample source change.
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox(u"You have already chosen a sample source and added or loaded destination plate entries."
                            + u"\nIf you change the sample source, the current entries will be deleted."
                            + u"\nDo you want to proceed?",
                            caption = "Change sample source?",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def query_discard_changes(*args):
    """
    Displays message box asking user to confirm discarding of unsaved
    data when closing project.
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox(u"You may have unsaved data. Do you still want to close this project?",
                            caption = u"Discard changes?",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def query_close_program(*args):
    """
    Displays message box asking user to confirm discarding of unsaved
    data when closing program.
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox(u"You may have unsaved data. Do you still want to close the program?",
                            caption = u"Discard changes?",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def warn_permission_denied(*args):
    """
    Displays message box if file could not be saved due to insufficient
    permissions.
    """
    message = wx.MessageBox(u"Cannot save file. Please check that"
                            + u"\n  i. you have permission to write in this directory"
                            + u"\n  ii. the file you are trying to overwrite is not protected"
                            + u"\n  iii. the file you are trying to overwrite is not in use by another program.",
                            caption = u"Permission denied!",
                            style = wx.OK|wx.ICON_WARNING)

def warn_files_not_loaded(*args):
    """
    Displays message box if one of more data files could not be found
    """
    message = wx.MessageBox(u"One or more files could not be loaded. Please check that"
                            + u"\n  i. files have not been moved"
                            + u"\n  ii. they are of the correct file type for this workflow.",
                            caption = u"File(s) not found",
                            style = wx.OK|wx.ICON_WARNING)

def query_connect_db(*args):
    """
    Displays message box saying BBQ is not connected to a database
    """
    message = wx.MessageBox(u"BBQ is not connected to a database. Would you like to connect?",
                            caption = u"No database connection",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def info_all_verified(*args):
    """
    Displays message box saying all values have been verified for
    dabase upload
    """
    message = wx.MessageBox(u"All values have been verified for upload to database.",
                            caption = u"Verification successful",
                            style = wx.OK|wx.ICON_INFORMATION)

def info_some_not_verified(*args):
    """
    Displays message box saying some values could not be verified for
    dabase upload
    """
    message = wx.MessageBox(u"One or more values could not be verified for upload. See lines highlighted in yellow.",
                            caption = u"Verification failed",
                            style = wx.OK|wx.ICON_INFORMATION)

def info_upload_success(results):
    """
    Displays message box saying all results were uploaded fine
    """
    message = wx.MessageBox(f"All {results} results were sucessfully uploaded.",
                            caption = u"Upload sucessful",
                            style = wx.OK|wx.ICON_INFORMATION)

def warn_upload_failure(failure):
    """
    Displays message box saying all results were uploaded fine
    """
    message = wx.MessageBox(u"The following error occurred while trying to upload the results: "
                            + u"\n\n " + failure
                            + u"\n\n Please contact BBQ and SCARAB support.",
                            caption = u"Upload sucessful",
                            style = wx.OK|wx.ICON_WARNING)