import pandas as pd
import workflows.wf_rawdatafunctions as rd
import workflows.wf_rawdatafunctions as tf
import lib_messageboxes as msg



def complete_container(workflow, dlg_progress):

    plate_assignment = workflow.dfr_PlateAssignment
    data_path = workflow.paths["Data"]
    transfer_file = workflow.dfr_TransferFile
    layout = workflow.dfr_Layout
    details = workflow.details
    data_rules = workflow.rawdata_rules
    exceptions = workflow.dfr_Exceptions

    assay_name = details["AssayType"]
    assay_category = details["AssayCategory"]
    assay_volume = details["AssayVolume"]
    sample_source = details["SampleSource"]
    device = details["Device"]
    plate_assignment = plate_assignment[plate_assignment["DataFile"] != ""]

    # Assay category is broad: single_dose, IC50 (or dose response), DSF_384...
    # Count how many rows we need:
    dlg_progress.lbx_Log.InsertItems([f"Assay category: {assay_category}"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
    container = pd.DataFrame(columns=["Destination","Samples","Wells","DataFile",
        "RawData","Processed","PlateID","Layout","References"], index=range(plate_assignment.shape[0]))
    # Iterate through the plate_assignment frame
    for plate in plate_assignment.index:
        container.loc[plate,"Destination"] = plate_assignment.loc[plate,"TransferEntry"]
        dest = container.loc[plate,"Destination"]
        dlg_progress.lbx_Log.InsertItems([f"Processing plate {plate+1}: {dest}"], dlg_progress.lbx_Log.Count)
        dlg_progress.lbx_Log.InsertItems(["==============================================================="], dlg_progress.lbx_Log.Count)
        container.loc[plate,"Wells"] = int(plate_assignment.loc[plate,"Wells"])
        container.loc[plate,"DataFile"] = plate_assignment.loc[plate,"DataFile"]
        # Get raw data
        datafile = container.loc[plate,"DataFile"]
        dlg_progress.lbx_Log.InsertItems([F"Read raw data file: {datafile}"], dlg_progress.lbx_Log.Count)
        if assay_category.find("dose_response") != -1:
            container.at[plate,"RawData"] = ro.get_bmg_plate_readout(data_path,
                                                                          container.loc[plate,"DataFile"],
                                                                          container.loc[plate,"Wells"],
                                                                          assay_name)
            #container.at[plate,"RawData"], rawdataread = ro.get_readout(data_path,
            #                                                            container.loc[plate,"DataFile"],
            #                                                            data_rules)
        elif assay_category.find("single_dose") != -1:
            # All plates will be the same plate type!
            raw_data = ro.get_bmg_list_readout(data_path, int(plate_assignment.loc[0,"Wells"]))
            container.at[plate,"RawData"] = raw_data[["Well",container.loc[plate,"DataFile"]]]
            #container.at[plate,"RawData"], rawdataread = ro.get_readout(data_path,
            #                                                            container["DataFile"].to_list(),
            #                                                            data_rules)
        elif assay_category == "thermal_shift":
            if "Agilent" in assay_name and "96" in assay_name:
                container.at[plate,"RawData"] = ro.get_mxp_readout(data_path + chr(92) + container.loc[plate,"DataFile"], 24) # last argument is NOT number of wells but starting temperature!
            elif "LightCycler" in assay_name and "96" in assay_name:
                container.at[plate,"RawData"] = ro.get_lightcycler_readout(data_path + chr(92) + container.loc[plate,"DataFile"], 96)
            elif "LightCycler" in assay_name and "384" in assay_name:
                container.at[plate,"RawData"] = ro.get_lightcycler_readout(data_path + chr(92) + container.loc[plate,"DataFile"], 384)
            elif "QuantStudio" in assay_name and "384" in assay_name:
                container.at[plate,"RawData"] = ro.get_quantstudio_readout(data_path + chr(92) + container.loc[plate,"DataFile"], 384)
        elif assay_category == "rate":
            container.at[plate,"RawData"] = ro.get_bmg_timecourse_readout(data_path + container.loc[plate,"DataFile"])
        # Test whether a correct file was loaded:
        if container.loc[plate,"RawData"] is None: # == False:
            msg.warn_not_datafile("self")
            return None
        # Get samples
        if sample_source == "echo":
            dlg_progress.lbx_Log.InsertItems(["Extract sample IDs from transfer file"], dlg_progress.lbx_Log.Count)
            container.at[plate,"Samples"] = get_samples(transfer_file,
                                                        container.loc[plate,"Destination"],
                                                        container.loc[plate,"Wells"])
        elif sample_source == "lightcycler":
            dlg_progress.lbx_Log.InsertItems(["Extract sample IDs from raw data file"], dlg_progress.lbx_Log.Count)
            container.at[plate,"Samples"] = get_samples_lightcycler(container.loc[plate,"Destination"],
                                                                    container.at[plate,"RawData"],
                                                                    len(layout.loc[plate,"ProteinNumerical"]))
        elif sample_source == "well":
            container.at[plate,"Samples"] = get_samples_wellonly(container.loc[plate,"Destination"],
                                                                 container.at[plate,"RawData"],
                                                                 len(layout.loc[plate,"ProteinNumerical"]))
        if assay_category == "thermal_shift":
            # References get handled differently here
            if layout.shape[0] > 1:
                idx_Layout = plate
            else:
                idx_Layout = 0
            container.at[plate,"PlateID"] = layout.loc[idx_Layout,"PlateID"]
            container.at[plate,"Layout"] = layout.loc[idx_Layout,"Layout"]
            # Create dataframe for data processing
            container.at[plate,"Processed"], container.at[plate,"References"] = create_dataframe_DSF(container.at[plate,"RawData"],
                                                                                                              container.loc[plate,"Samples"],
                                                                                                              layout.loc[idx_Layout,"Layout"],
                                                                                                              dlg_progress)
        elif assay_category.find("rate") != -1:
            # References get handled differently here
            container.at[plate,"Layout"] = get_layout(transfer_file,
                                                      container.loc[plate,"Destination"],
                                                      container.loc[plate,"RawData"].rename(columns={"Signal":"Reading"}))
            # Create dataframe for data processing
            container.at[plate,"Processed"], container.at[plate,"References"] = create_dataframe_rate(container.at[plate,"RawData"],
                container.loc[plate,"Samples"],container.loc[plate,"Layout"],dlg_progress)
        else:
            # Endpoint assays
            # Get controls and references
            container.at[plate,"Layout"] = get_layout(transfer_file,
                                                      container.loc[plate,"Destination"],
                                                      container.loc[plate,"RawData"].rename(columns={datafile:"Reading"}))
            container.at[plate,"References"] = get_references(container.at[plate,"Layout"],
                                                              datafile,
                                                              container.loc[plate,"RawData"])
            if pd.isna(container.loc[plate,"References"].loc["SolventMean",0]) == True:
                dlg_progress.lbx_Log.InsertItems(["Note: No Solvent wells"], dlg_progress.lbx_Log.Count)
            if pd.isna(container.loc[plate,"References"].loc["ControlMean",0]) == True:
                dlg_progress.lbx_Log.InsertItems(["Note: No control wells"], dlg_progress.lbx_Log.Count)
            if pd.isna(container.loc[plate,"References"].loc["BufferMean",0]) == True:
                dlg_progress.lbx_Log.InsertItems(["Note: No buffer wells"], dlg_progress.lbx_Log.Count)
            # Create dataframe for data processing
            if assay_category.find("dose_response") != -1:
                container.at[plate,"Processed"] = create_dataframe_EPDR(container.at[plate,"RawData"],
                    container.loc[plate,"Samples"],container.loc[plate,"References"],assay_name,assay_volume,dlg_progress)
            elif assay_category.find("single_dose") != -1:
                container.at[plate,"Processed"] = create_dataframe_EPSD(container.at[plate,"RawData"],
                    container.loc[plate,"Samples"],container.loc[plate,"References"],assay_name,assay_volume,dlg_progress)
        dlg_progress.lbx_Log.InsertItems(["Plate "+ str(plate+1) + " completed"], dlg_progress.lbx_Log.Count)
        dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)

    return container