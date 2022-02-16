import pandas as pd
import plotly.graph_objects as go
from dynawo_validation.dynaflow.notebooks import create_graph
from dynawo_validation.dynaflow.pipeline.common_funcs import calc_global_score
from IPython.display import display, HTML, Markdown
import ipydatagrid
from ipywidgets import widgets, AppLayout
import warnings
from matplotlib import cm, patches, pyplot
import pylab as pl
import numpy as np
from lxml import etree
import lzma
import os
import copy


# Read the metric file
def read_csv_metrics(pf_dir):
    data = pd.read_csv(pf_dir + "/pf_metrics/metrics.csv.xz", index_col=0)
    return data


# Read general aut_diffs csv
def read_csv_aut_diffs(aut_dir):
    dataA = pd.read_csv(aut_dir + "/SIMULATOR_A_AUT_CHANGES.csv", sep=";", index_col=0)
    dataB = pd.read_csv(aut_dir + "/SIMULATOR_B_AUT_CHANGES.csv", sep=";", index_col=0)
    return dataA, dataB


# Read csv for aut plot
def read_aut_case(aut_dir, var):
    if var == "ratioTapChanger":
        var = "TAP_CHANGES.csv"
    else:
        var = "PSTAP_CHANGES.csv"
    return pd.read_csv(aut_dir + var, sep=";", index_col=0)


# Create the first graph
def get_initial_graph(netwgraph_iidm_file, value, t, c):
    return create_graph.get_graph(netwgraph_iidm_file, value, t, c)


# For hiding code cells
def toggle_code(state):
    """
    Toggles the JavaScript show()/hide() function on the div.input element.\n",
    """
    javascript_functions = {False: "hide()", True: "show()"}
    output_args = (javascript_functions[state],)
    output_string = '<script>$("div.input").{}</script>'
    output = output_string.format(*output_args)
    display(HTML(output))


def button_action(value):
    """
    Calls the toggle_code function and updates the button description.
    """
    state = value.new
    toggle_code(state)
    button_descriptions = {False: "Show code", True: "Hide code"}
    value.owner.description = button_descriptions[state]


def do_displaybutton():
    state = False
    toggle_code(state)
    button_descriptions = {False: "Show code", True: "Hide code"}
    button = widgets.ToggleButton(state, description=button_descriptions[state])
    button.observe(button_action, "value")
    display(button)


# Calculate absolute and relative error
def calculate_error(df1):
    REL_ERR_CLIPPING = 0.1
    # df1["VOLT_LEVEL"] = df1["VOLT_LEVEL"].astype(str)
    # to force "discrete colors" in Plotly Express
    df1["ABS_ERR"] = (df1["VALUE_A"] - df1["VALUE_B"]).abs()
    df1["REL_ERR"] = df1["ABS_ERR"] / df1["VALUE_A"].abs().clip(lower=REL_ERR_CLIPPING)
    return df1


# Read a specific contingency
def read_case(name, PF_SOL_DIR, PREFIX):
    file_name = PF_SOL_DIR + "/pf_sol/" + PREFIX + "#" + name + "_pfsolutionAB.csv.xz"
    data = pd.read_csv(file_name, sep=";", index_col=False, compression="infer")
    data["DIFF"] = data.VALUE_A - data.VALUE_B
    data = calculate_error(data)
    return data


def read_aut_group(name, PF_SOL_DIR, DWO_DWO, PREFIX):
    if DWO_DWO == 0:
        file_name = PF_SOL_DIR + "/aut/" + PREFIX + "#" + name + "-aut-groups.csv"
        data = pd.read_csv(file_name, sep=";")
        return data, None
    else:
        file_name = PF_SOL_DIR + "/aut/" + PREFIX + "#" + name + "-autA-groups.csv"
        data1 = pd.read_csv(file_name, sep=";")
        file_name = PF_SOL_DIR + "/aut/" + PREFIX + "#" + name + "-autB-groups.csv"
        data2 = pd.read_csv(file_name, sep=";")
        return data1, data2


# Create the general graphic of simulator A vs B
def create_general_trace(data, x, y, DATA_LIMIT):
    if data.shape[0] > DATA_LIMIT:
        data = data.reindex(data[y].abs().sort_values().index)
        data = data[-DATA_LIMIT:]
    trace = go.Scatter(
        x=data[x],
        y=data[y],
        mode="markers",
        text=data["contg_case"] + "_(" + data["volt_level"] + ")",
        name=x + "_" + y,
    )
    return trace


# Create the colors and legends for plot
def create_colors(data):
    colordata = []
    for datanum in data["VOLT_LEVEL"]:
        if datanum >= 380:
            colordata.append("rgb(255,0,0)")
        elif datanum >= 225:
            colordata.append("rgb(0,255,0)")
        elif datanum >= 150:
            colordata.append("rgb(0,255,255)")
        elif datanum >= 90:
            colordata.append("rgb(255,255,0)")
        elif datanum >= 63:
            colordata.append("rgb(170,0,255)")
        elif datanum >= 45:
            colordata.append("rgb(64,64,64)")
        elif datanum >= 42:
            colordata.append("rgb(128,128,128)")
        elif datanum >= 20:
            colordata.append("rgb(196,196,196)")
        else:
            colordata.append("rgb(255,255,255)")
    patch_380 = patches.Patch(color=(255 / 255, 0, 0), label="380 kV")
    patch_225 = patches.Patch(color=(0, 255 / 255, 0), label="225 kV")
    patch_150 = patches.Patch(color=(0, 255 / 255, 255 / 255), label="150 kV")
    patch_90 = patches.Patch(color=(255 / 255, 255 / 255, 0), label="90 kV")
    patch_63 = patches.Patch(color=(170 / 255, 0, 255 / 255), label="63 kV")
    patch_45 = patches.Patch(color=(64 / 255, 64 / 255, 64 / 255), label="45 kV")
    patch_42 = patches.Patch(color=(128 / 255, 128 / 255, 128 / 255), label="45 kV")
    patch_20 = patches.Patch(color=(196 / 255, 196 / 255, 196 / 255), label="20 kV")
    pyplot.legend(
        handles=[
            patch_380,
            patch_225,
            patch_150,
            patch_90,
            patch_63,
            patch_45,
            patch_42,
            patch_20,
        ]
    )
    pyplot.savefig("legend0.png")
    pyplot.close()
    contgcasediffs_legend = pl.imread("legend0.png")[40:170, 300:385, :]
    addwhite0 = np.zeros(
        (100, contgcasediffs_legend.shape[1], contgcasediffs_legend.shape[2])
    )
    addwhite1 = np.zeros(
        (300, contgcasediffs_legend.shape[1], contgcasediffs_legend.shape[2])
    )
    contgcasediffs_legend = np.concatenate(
        (addwhite0, contgcasediffs_legend, addwhite1), axis=0
    )
    pl.imsave("legend0.png", contgcasediffs_legend)
    return colordata


# Create the individual graphic of simulator A vs B
def create_individual_trace(data, x, y):
    colordata = create_colors(data)
    trace = go.Scatter(
        x=data[x],
        y=data[y],
        mode="markers",
        text=data["ID"],
        name=x + "_" + y,
        marker=dict(color=colordata),
        showlegend=False,
    )
    return trace


def create_aut_group_trace(data1, data2):
    if data2 is None:
        data = data1.sort_values("GROUP", axis=0)
        c = list(data["GROUP"])
        if len(c) != 0:
            max_val = max(c)
        else:
            max_val = 0
        plasma = cm.get_cmap("plasma", 12)
        for i in range(len(c)):
            c[i] = c[i] / (max_val + 1)
            r = plasma(c[i])[0] * 256
            g = plasma(c[i])[1] * 256
            b = plasma(c[i])[2] * 256
            c[i] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
        trace1 = go.Scatter(
            x=data["TIME"],
            y=data["DEVICE"],
            mode="markers",
            text=data["EVENT_MESSAGE"],
            marker=dict(color=c),
        )
        trace2 = None
    else:
        data = data1.sort_values("GROUP", axis=0)
        c = list(data["GROUP"])
        if len(c) != 0:
            max_val = max(c)
        else:
            max_val = 0
        plasma = cm.get_cmap("plasma", 12)
        for i in range(len(c)):
            c[i] = c[i] / (max_val + 1)
            r = plasma(c[i])[0] * 256
            g = plasma(c[i])[1] * 256
            b = plasma(c[i])[2] * 256
            c[i] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
        trace1 = go.Scatter(
            x=data["TIME"],
            y=data["DEVICE"],
            mode="markers",
            text=data["EVENT_MESSAGE"],
            marker=dict(color=c),
        )
        data = data2.sort_values("GROUP", axis=0)
        c = list(data["GROUP"])
        if len(c) != 0:
            max_val = max(c)
        else:
            max_val = 0
        plasma = cm.get_cmap("plasma", 12)
        for i in range(len(c)):
            c[i] = c[i] / (max_val + 1)
            r = plasma(c[i])[0] * 256
            g = plasma(c[i])[1] * 256
            b = plasma(c[i])[2] * 256
            c[i] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
        trace2 = go.Scatter(
            x=data["TIME"],
            y=data["DEVICE"],
            mode="markers",
            text=data["EVENT_MESSAGE"],
            marker=dict(color=c),
        )

    return trace1, trace2


# Find the execution launchers
def find_launchers(pathtofiles):
    launcherA = None
    launcherB = None
    for file in os.listdir(pathtofiles):
        basefile = os.path.basename(file)
        if ".LAUNCHER_A_WAS_" == basefile[:16] and launcherA is None:
            launcherA = basefile[16:]
        elif ".LAUNCHER_A_WAS_" == basefile[:16]:
            raise ValueError("Two or more .LAUNCHER_WAS_A in results dir")
        elif ".LAUNCHER_B_WAS_" == basefile[:16] and launcherB is None:
            launcherB = basefile[16:]
        elif ".LAUNCHER_B_WAS_" == basefile[:16]:
            raise ValueError("Two or more .LAUNCHER_WAS_A in results dir")
    return launcherA, launcherB


# In order not to have to save all the differences of each of the contingencies,
# we eliminate them in the pipeline and create only the necessary ones here.
def create_aut_df(results_dir, A_B, contgcase, prefix, basecase, dwo_dwo, var_value):
    launcherA, launcherB = find_launchers(results_dir)
    run_dwo = True
    if A_B == 1:
        if launcherA[:5] == "hades":
            xml_CONTGCASE = (
                results_dir
                + "/"
                + prefix
                + "/xml/"
                + prefix
                + "#"
                + contgcase
                + "-Hades.Out.xml.xz"
            )
            save_path = results_dir + basecase + "/"
            hades_input = results_dir + basecase + "/Hades/donneesEntreeHADES2.xml"
            run_dwo = False
        else:
            if dwo_dwo == 0:
                xml_CONTGCASE = (
                    results_dir
                    + "/"
                    + prefix
                    + "/xml/"
                    + prefix
                    + "#"
                    + contgcase
                    + "-Dynawo.IIDM.xml.xz"
                )
                save_path = results_dir + basecase + "/"
            else:
                xml_CONTGCASE = (
                    results_dir
                    + "/"
                    + prefix
                    + "/xml/"
                    + prefix
                    + "#"
                    + contgcase
                    + "-Dynawo.IIDMA.xml.xz"
                )
                save_path = results_dir + basecase + "/A/"

    if A_B == 2:
        if launcherB[:5] == "hades":
            xml_CONTGCASE = (
                results_dir
                + "/"
                + prefix
                + "/xml/"
                + prefix
                + "#"
                + contgcase
                + "-Hades.Out.xml.xz"
            )
            save_path = results_dir + basecase + "/"
            hades_input = results_dir + basecase + "/Hades/donneesEntreeHADES2.xml"
            run_dwo = False
        else:
            if dwo_dwo == 0:
                xml_CONTGCASE = (
                    results_dir
                    + "/"
                    + prefix
                    + "/xml/"
                    + prefix
                    + "#"
                    + contgcase
                    + "-Dynawo.IIDM.xml.xz"
                )
                save_path = results_dir + basecase + "/"
            else:
                xml_CONTGCASE = (
                    results_dir
                    + "/"
                    + prefix
                    + "/xml/"
                    + prefix
                    + "#"
                    + contgcase
                    + "-Dynawo.IIDMB.xml.xz"
                )
                save_path = results_dir + basecase + "/B/"

    if not run_dwo:

        tree = etree.parse(hades_input)
        root = tree.getroot()
        reseau = root.find("./reseau", root.nsmap)
        donneesQuadripoles = reseau.find("./donneesQuadripoles", root.nsmap)
        tap2xfmr = dict()
        pstap2xfmr = dict()
        for branch in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
            tap_ID = branch.get("ptrregleur")
            if tap_ID != "0" and tap_ID is not None:
                tap2xfmr[tap_ID] = branch.get("nom")
            pstap_ID = branch.get("ptrdepha")
            if pstap_ID != "0" and pstap_ID is not None:
                pstap2xfmr[pstap_ID] = branch.get("nom")

        hds_contgcase_tree = etree.parse(
            lzma.open(xml_CONTGCASE), etree.XMLParser(remove_blank_text=True)
        )

        # MATCHING
        if save_path[-1] != "/":
            save_path = save_path + "/"
        root = hds_contgcase_tree.getroot()
        reseau = root.find("./reseau", root.nsmap)

        # CONTG
        if var_value == "ratioTapChanger":
            donneesRegleurs = reseau.find("./donneesRegleurs", root.nsmap)
            hades_regleurs_contg = dict()
            for regleur in donneesRegleurs.iterfind("./regleur", root.nsmap):
                for variable in regleur.iterfind("./variables", root.nsmap):
                    regleur_id = tap2xfmr[variable.getparent().get("num")]
                    if regleur_id not in hades_regleurs_contg:
                        hades_regleurs_contg[regleur_id] = int(variable.get("plot"))
                    else:
                        raise ValueError(f"Tap ID repeated (regleur_id={regleur_id})")

            df_hades_regleurs_basecase = pd.read_csv(
                save_path + "df_hades_regleurs_basecase.csv", sep=";", index_col=0
            )

            data_keys = hades_regleurs_contg.keys()
            data_list = hades_regleurs_contg.values()
            df_hades_regleurs_contg = pd.DataFrame(
                data=data_list, index=data_keys, columns=["AUT_VAL"]
            )

            df_hades_regleurs_diff = copy.deepcopy(df_hades_regleurs_basecase)

            df_hades_regleurs_diff = df_hades_regleurs_diff.rename(
                columns={"AUT_VAL": "BC_VAL"}
            )
            df_hades_regleurs_diff["CG_VAL"] = df_hades_regleurs_contg["AUT_VAL"]

            df_hades_regleurs_diff["DIFF"] = (
                df_hades_regleurs_contg["AUT_VAL"]
                - df_hades_regleurs_basecase["AUT_VAL"]
            )

            df_hades_regleurs_diff["ABS_DIFF"] = df_hades_regleurs_diff["DIFF"].abs()

            df_hades_regleurs_diff.loc[
                df_hades_regleurs_diff["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_hades_regleurs_diff.loc[
                df_hades_regleurs_diff["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_hades_regleurs_diff["POS_DIFF"] = df_hades_regleurs_diff["DIFF"]
            df_hades_regleurs_diff.loc[
                df_hades_regleurs_diff["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_hades_regleurs_diff["NEG_DIFF"] = df_hades_regleurs_diff["DIFF"]
            df_hades_regleurs_diff.loc[
                df_hades_regleurs_diff["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            return df_hades_regleurs_diff

        if var_value == "phaseTapChanger":
            donneesDephaseurs = reseau.find("./donneesDephaseurs", root.nsmap)
            hades_dephaseurs_contg = dict()
            for dephaseur in donneesDephaseurs.iterfind("./dephaseur", root.nsmap):
                for variable in dephaseur.iterfind("./variables", root.nsmap):
                    dephaseur_id = pstap2xfmr[variable.getparent().get("num")]
                    if dephaseur_id not in hades_dephaseurs_contg:
                        hades_dephaseurs_contg[dephaseur_id] = int(variable.get("plot"))
                    else:
                        raise ValueError(
                            f"Tap ID repeated (dephaseur_id={dephaseur_id})"
                        )

            df_hades_dephaseurs_basecase = pd.read_csv(
                save_path + "df_hades_dephaseurs_basecase.csv", sep=";", index_col=0
            )

            data_keys = hades_dephaseurs_contg.keys()
            data_list = hades_dephaseurs_contg.values()
            df_hades_dephaseurs_contg = pd.DataFrame(
                data=data_list, index=data_keys, columns=["AUT_VAL"]
            )

            df_hades_dephaseurs_diff = copy.deepcopy(df_hades_dephaseurs_basecase)

            df_hades_dephaseurs_diff = df_hades_dephaseurs_diff.rename(
                columns={"AUT_VAL": "BC_VAL"}
            )
            df_hades_dephaseurs_diff["CG_VAL"] = df_hades_dephaseurs_contg["AUT_VAL"]

            df_hades_dephaseurs_diff["DIFF"] = (
                df_hades_dephaseurs_contg["AUT_VAL"]
                - df_hades_dephaseurs_basecase["AUT_VAL"]
            )

            df_hades_dephaseurs_diff["ABS_DIFF"] = df_hades_dephaseurs_diff[
                "DIFF"
            ].abs()

            df_hades_dephaseurs_diff.loc[
                df_hades_dephaseurs_diff["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_hades_dephaseurs_diff.loc[
                df_hades_dephaseurs_diff["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_hades_dephaseurs_diff["POS_DIFF"] = df_hades_dephaseurs_diff["DIFF"]
            df_hades_dephaseurs_diff.loc[
                df_hades_dephaseurs_diff["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_hades_dephaseurs_diff["NEG_DIFF"] = df_hades_dephaseurs_diff["DIFF"]
            df_hades_dephaseurs_diff.loc[
                df_hades_dephaseurs_diff["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            return df_hades_dephaseurs_diff

    else:
        dwo_contgcase_tree = etree.parse(
            lzma.open(xml_CONTGCASE), etree.XMLParser(remove_blank_text=True)
        )

        # CONTG

        root = dwo_contgcase_tree.getroot()
        ns = etree.QName(root).namespace
        if save_path[-1] != "/":
            save_path = save_path + "/"

        if var_value == "ratioTapChanger":
            dynawo_ratioTapChanger_contgcase = dict()
            for ratioTapChanger in root.iter("{%s}ratioTapChanger" % ns):
                ratioTapChanger_id = ratioTapChanger.getparent().get("id")
                if ratioTapChanger_id not in dynawo_ratioTapChanger_contgcase:
                    dynawo_ratioTapChanger_contgcase[ratioTapChanger_id] = int(
                        ratioTapChanger.get("tapPosition")
                    )
                else:
                    raise ValueError("Tap ID repeated")

            df_dynawo_ratioTapChanger_basecase = pd.read_csv(
                save_path + "df_dynawo_ratioTapChanger_basecase.csv",
                sep=";",
                index_col=0,
            )

            data_keys = dynawo_ratioTapChanger_contgcase.keys()
            data_list = dynawo_ratioTapChanger_contgcase.values()
            df_dynawo_ratioTapChanger_contgcase = pd.DataFrame(
                data=data_list, index=data_keys, columns=["TAP_VAL"]
            )

            df_dynawo_ratioTapChanger_diff = copy.deepcopy(
                df_dynawo_ratioTapChanger_basecase
            )

            df_dynawo_ratioTapChanger_diff = df_dynawo_ratioTapChanger_diff.rename(
                columns={"TAP_VAL": "BC_VAL"}
            )
            df_dynawo_ratioTapChanger_diff[
                "CG_VAL"
            ] = df_dynawo_ratioTapChanger_contgcase["TAP_VAL"]

            df_dynawo_ratioTapChanger_diff["DIFF"] = (
                df_dynawo_ratioTapChanger_contgcase["TAP_VAL"]
                - df_dynawo_ratioTapChanger_basecase["TAP_VAL"]
            )

            df_dynawo_ratioTapChanger_diff["ABS_DIFF"] = df_dynawo_ratioTapChanger_diff[
                "DIFF"
            ].abs()

            df_dynawo_ratioTapChanger_diff.loc[
                df_dynawo_ratioTapChanger_diff["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_ratioTapChanger_diff.loc[
                df_dynawo_ratioTapChanger_diff["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_ratioTapChanger_diff["POS_DIFF"] = df_dynawo_ratioTapChanger_diff[
                "DIFF"
            ]
            df_dynawo_ratioTapChanger_diff.loc[
                df_dynawo_ratioTapChanger_diff["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_dynawo_ratioTapChanger_diff["NEG_DIFF"] = df_dynawo_ratioTapChanger_diff[
                "DIFF"
            ]
            df_dynawo_ratioTapChanger_diff.loc[
                df_dynawo_ratioTapChanger_diff["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            return df_dynawo_ratioTapChanger_diff

        if var_value == "phaseTapChanger":
            dynawo_phaseTapChanger_contgcase = dict()
            for phaseTapChanger in root.iter("{%s}phaseTapChanger" % ns):
                phaseTapChanger_id = phaseTapChanger.getparent().get("id")
                if phaseTapChanger_id not in dynawo_phaseTapChanger_contgcase:
                    dynawo_phaseTapChanger_contgcase[phaseTapChanger_id] = int(
                        phaseTapChanger.get("tapPosition")
                    )
                else:
                    raise ValueError("Tap ID repeated")

            df_dynawo_phaseTapChanger_basecase = pd.read_csv(
                save_path + "df_dynawo_phaseTapChanger_basecase.csv",
                sep=";",
                index_col=0,
            )

            data_keys = dynawo_phaseTapChanger_contgcase.keys()
            data_list = dynawo_phaseTapChanger_contgcase.values()
            df_dynawo_phaseTapChanger_contgcase = pd.DataFrame(
                data=data_list, index=data_keys, columns=["PSTAP_VAL"]
            )

            df_dynawo_phaseTapChanger_diff = copy.deepcopy(
                df_dynawo_phaseTapChanger_basecase
            )
            df_dynawo_phaseTapChanger_diff = df_dynawo_phaseTapChanger_diff.rename(
                columns={"PSTAP_VAL": "BC_VAL"}
            )
            df_dynawo_phaseTapChanger_diff[
                "CG_VAL"
            ] = df_dynawo_phaseTapChanger_contgcase["PSTAP_VAL"]

            df_dynawo_phaseTapChanger_diff["DIFF"] = (
                df_dynawo_phaseTapChanger_contgcase["PSTAP_VAL"]
                - df_dynawo_phaseTapChanger_basecase["PSTAP_VAL"]
            )

            df_dynawo_phaseTapChanger_diff["ABS_DIFF"] = df_dynawo_phaseTapChanger_diff[
                "DIFF"
            ].abs()

            df_dynawo_phaseTapChanger_diff.loc[
                df_dynawo_phaseTapChanger_diff["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_phaseTapChanger_diff.loc[
                df_dynawo_phaseTapChanger_diff["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_phaseTapChanger_diff["POS_DIFF"] = df_dynawo_phaseTapChanger_diff[
                "DIFF"
            ]
            df_dynawo_phaseTapChanger_diff.loc[
                df_dynawo_phaseTapChanger_diff["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_dynawo_phaseTapChanger_diff["NEG_DIFF"] = df_dynawo_phaseTapChanger_diff[
                "DIFF"
            ]
            df_dynawo_phaseTapChanger_diff.loc[
                df_dynawo_phaseTapChanger_diff["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            return df_dynawo_phaseTapChanger_diff

        if var_value == "shunt":
            dynawo_shunt_contgcase = dict()
            for shunt in root.iter("{%s}shunt" % ns):
                if shunt.get("bus") is not None:
                    shunt_id = shunt.get("id")
                    if shunt_id not in dynawo_shunt_contgcase:
                        dynawo_shunt_contgcase[shunt_id] = 1
                    else:
                        raise ValueError("Tap ID repeated")
                else:
                    shunt_id = shunt.get("id")
                    if shunt_id not in dynawo_shunt_contgcase:
                        dynawo_shunt_contgcase[shunt_id] = 0
                    else:
                        raise ValueError("Tap ID repeated")

            df_dynawo_shunt_basecase = pd.read_csv(
                save_path + "df_dynawo_shunt_basecase.csv", sep=";", index_col=0
            )

            data_keys = dynawo_shunt_contgcase.keys()
            data_list = dynawo_shunt_contgcase.values()
            df_dynawo_shunt_contgcase = pd.DataFrame(
                data=data_list, index=data_keys, columns=["SHUNT_CHG_VAL"]
            )

            df_dynawo_shunt_diff = copy.deepcopy(df_dynawo_shunt_basecase)

            df_dynawo_shunt_diff = df_dynawo_shunt_diff.rename(
                columns={"SHUNT_CHG_VAL": "BC_VAL"}
            )
            df_dynawo_shunt_diff["CG_VAL"] = df_dynawo_shunt_contgcase["SHUNT_CHG_VAL"]

            df_dynawo_shunt_diff["DIFF"] = (
                df_dynawo_shunt_contgcase["SHUNT_CHG_VAL"]
                - df_dynawo_shunt_basecase["SHUNT_CHG_VAL"]
            )

            df_dynawo_shunt_diff["ABS_DIFF"] = df_dynawo_shunt_diff["DIFF"].abs()

            df_dynawo_shunt_diff.loc[
                df_dynawo_shunt_diff["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_shunt_diff.loc[
                df_dynawo_shunt_diff["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_shunt_diff["POS_DIFF"] = df_dynawo_shunt_diff["DIFF"]
            df_dynawo_shunt_diff.loc[df_dynawo_shunt_diff["DIFF"] <= 0, "POS_DIFF"] = 0

            df_dynawo_shunt_diff["NEG_DIFF"] = df_dynawo_shunt_diff["DIFF"]
            df_dynawo_shunt_diff.loc[df_dynawo_shunt_diff["DIFF"] >= 0, "NEG_DIFF"] = 0

            return df_dynawo_shunt_diff

        if var_value == "branch_bus1":
            dynawo_branch_contgcase_bus1 = dict()
            dynawo_branch_contgcase_bus2 = dict()
            for line in root.iter("{%s}line" % ns):
                temp = [0, 0]
                line_id = line.get("id")
                if line.get("bus1") is not None:
                    temp[0] = 1
                if line.get("bus2") is not None:
                    temp[1] = 1
                if line_id not in dynawo_branch_contgcase_bus1:
                    dynawo_branch_contgcase_bus1[line_id] = temp[0]
                else:
                    raise ValueError("Tap ID repeated")
                if line_id not in dynawo_branch_contgcase_bus2:
                    dynawo_branch_contgcase_bus2[line_id] = temp[1]
                else:
                    raise ValueError("Tap ID repeated")

            for twoWindingsTransformer in root.iter("{%s}twoWindingsTransformer" % ns):
                temp = [0, 0]
                twoWindingsTransformer_id = twoWindingsTransformer.get("id")
                if twoWindingsTransformer.get("bus1") is not None:
                    temp[0] = 1
                if twoWindingsTransformer.get("bus2") is not None:
                    temp[1] = 1
                if twoWindingsTransformer_id not in dynawo_branch_contgcase_bus1:
                    dynawo_branch_contgcase_bus1[twoWindingsTransformer_id] = temp[0]
                else:
                    raise ValueError("Tap ID repeated")
                if twoWindingsTransformer_id not in dynawo_branch_contgcase_bus2:
                    dynawo_branch_contgcase_bus2[twoWindingsTransformer_id] = temp[1]
                else:
                    raise ValueError("Tap ID repeated")

            df_dynawo_branch_basecase_bus1 = pd.read_csv(
                save_path + "df_dynawo_branch_basecase_bus1.csv", sep=";", index_col=0
            )

            df_dynawo_branch_basecase_bus2 = pd.read_csv(
                save_path + "df_dynawo_branch_basecase_bus2.csv", sep=";", index_col=0
            )

            data_keys = dynawo_branch_contgcase_bus1.keys()
            data_list = dynawo_branch_contgcase_bus1.values()
            df_dynawo_branch_contgcase_bus1 = pd.DataFrame(
                data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_1"]
            )

            data_keys = dynawo_branch_contgcase_bus2.keys()
            data_list = dynawo_branch_contgcase_bus2.values()
            df_dynawo_branch_contgcase_bus2 = pd.DataFrame(
                data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_2"]
            )

            df_dynawo_branch_diff_1 = copy.deepcopy(df_dynawo_branch_basecase_bus1)

            df_dynawo_branch_diff_1 = df_dynawo_branch_diff_1.rename(
                columns={"TOPO_CHG_VAL_1": "BC_VAL_1"}
            )
            df_dynawo_branch_diff_1["CG_VAL_1"] = df_dynawo_branch_contgcase_bus1[
                "TOPO_CHG_VAL_1"
            ]

            df_dynawo_branch_diff_2 = copy.deepcopy(df_dynawo_branch_basecase_bus2)

            df_dynawo_branch_diff_2 = df_dynawo_branch_diff_2.rename(
                columns={"TOPO_CHG_VAL_2": "BC_VAL_2"}
            )
            df_dynawo_branch_diff_2["CG_VAL_2"] = df_dynawo_branch_contgcase_bus2[
                "TOPO_CHG_VAL_2"
            ]

            df_dynawo_branch_diff_1["DIFF"] = (
                df_dynawo_branch_contgcase_bus1["TOPO_CHG_VAL_1"]
                - df_dynawo_branch_basecase_bus1["TOPO_CHG_VAL_1"]
            )

            df_dynawo_branch_diff_1["ABS_DIFF"] = df_dynawo_branch_diff_1["DIFF"].abs()

            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_branch_diff_1["POS_DIFF"] = df_dynawo_branch_diff_1["DIFF"]
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_dynawo_branch_diff_1["NEG_DIFF"] = df_dynawo_branch_diff_1["DIFF"]
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            df_dynawo_branch_diff_2["DIFF"] = (
                df_dynawo_branch_contgcase_bus2["TOPO_CHG_VAL_2"]
                - df_dynawo_branch_basecase_bus2["TOPO_CHG_VAL_2"]
            )

            df_dynawo_branch_diff_2["ABS_DIFF"] = df_dynawo_branch_diff_2["DIFF"].abs()

            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_branch_diff_2["POS_DIFF"] = df_dynawo_branch_diff_2["DIFF"]
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_dynawo_branch_diff_2["NEG_DIFF"] = df_dynawo_branch_diff_2["DIFF"]
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            return df_dynawo_branch_diff_1

        if var_value == "branch_bus2":
            dynawo_branch_contgcase_bus1 = dict()
            dynawo_branch_contgcase_bus2 = dict()
            for line in root.iter("{%s}line" % ns):
                temp = [0, 0]
                line_id = line.get("id")
                if line.get("bus1") is not None:
                    temp[0] = 1
                if line.get("bus2") is not None:
                    temp[1] = 1
                if line_id not in dynawo_branch_contgcase_bus1:
                    dynawo_branch_contgcase_bus1[line_id] = temp[0]
                else:
                    raise ValueError("Tap ID repeated")
                if line_id not in dynawo_branch_contgcase_bus2:
                    dynawo_branch_contgcase_bus2[line_id] = temp[1]
                else:
                    raise ValueError("Tap ID repeated")

            for twoWindingsTransformer in root.iter("{%s}twoWindingsTransformer" % ns):
                temp = [0, 0]
                twoWindingsTransformer_id = twoWindingsTransformer.get("id")
                if twoWindingsTransformer.get("bus1") is not None:
                    temp[0] = 1
                if twoWindingsTransformer.get("bus2") is not None:
                    temp[1] = 1
                if twoWindingsTransformer_id not in dynawo_branch_contgcase_bus1:
                    dynawo_branch_contgcase_bus1[twoWindingsTransformer_id] = temp[0]
                else:
                    raise ValueError("Tap ID repeated")
                if twoWindingsTransformer_id not in dynawo_branch_contgcase_bus2:
                    dynawo_branch_contgcase_bus2[twoWindingsTransformer_id] = temp[1]
                else:
                    raise ValueError("Tap ID repeated")

            df_dynawo_branch_basecase_bus1 = pd.read_csv(
                save_path + "df_dynawo_branch_basecase_bus1.csv", sep=";", index_col=0
            )

            df_dynawo_branch_basecase_bus2 = pd.read_csv(
                save_path + "df_dynawo_branch_basecase_bus2.csv", sep=";", index_col=0
            )

            data_keys = dynawo_branch_contgcase_bus1.keys()
            data_list = dynawo_branch_contgcase_bus1.values()
            df_dynawo_branch_contgcase_bus1 = pd.DataFrame(
                data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_1"]
            )

            data_keys = dynawo_branch_contgcase_bus2.keys()
            data_list = dynawo_branch_contgcase_bus2.values()
            df_dynawo_branch_contgcase_bus2 = pd.DataFrame(
                data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_2"]
            )

            df_dynawo_branch_diff_1 = copy.deepcopy(df_dynawo_branch_basecase_bus1)

            df_dynawo_branch_diff_1 = df_dynawo_branch_diff_1.rename(
                columns={"TOPO_CHG_VAL_1": "BC_VAL_1"}
            )
            df_dynawo_branch_diff_1["CG_VAL_1"] = df_dynawo_branch_contgcase_bus1[
                "TOPO_CHG_VAL_1"
            ]

            df_dynawo_branch_diff_2 = copy.deepcopy(df_dynawo_branch_basecase_bus2)

            df_dynawo_branch_diff_2 = df_dynawo_branch_diff_2.rename(
                columns={"TOPO_CHG_VAL_2": "BC_VAL_2"}
            )
            df_dynawo_branch_diff_2["CG_VAL_2"] = df_dynawo_branch_contgcase_bus2[
                "TOPO_CHG_VAL_2"
            ]

            df_dynawo_branch_diff_1["DIFF"] = (
                df_dynawo_branch_contgcase_bus1["TOPO_CHG_VAL_1"]
                - df_dynawo_branch_basecase_bus1["TOPO_CHG_VAL_1"]
            )

            df_dynawo_branch_diff_1["ABS_DIFF"] = df_dynawo_branch_diff_1["DIFF"].abs()

            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_branch_diff_1["POS_DIFF"] = df_dynawo_branch_diff_1["DIFF"]
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_dynawo_branch_diff_1["NEG_DIFF"] = df_dynawo_branch_diff_1["DIFF"]
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            df_dynawo_branch_diff_2["DIFF"] = (
                df_dynawo_branch_contgcase_bus2["TOPO_CHG_VAL_2"]
                - df_dynawo_branch_basecase_bus2["TOPO_CHG_VAL_2"]
            )

            df_dynawo_branch_diff_2["ABS_DIFF"] = df_dynawo_branch_diff_2["DIFF"].abs()

            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_branch_diff_2["POS_DIFF"] = df_dynawo_branch_diff_2["DIFF"]
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_dynawo_branch_diff_2["NEG_DIFF"] = df_dynawo_branch_diff_2["DIFF"]
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            return df_dynawo_branch_diff_2

        if var_value == "branch_topo":
            dynawo_branch_contgcase_bus1 = dict()
            dynawo_branch_contgcase_bus2 = dict()
            for line in root.iter("{%s}line" % ns):
                temp = [0, 0]
                line_id = line.get("id")
                if line.get("bus1") is not None:
                    temp[0] = 1
                if line.get("bus2") is not None:
                    temp[1] = 1
                if line_id not in dynawo_branch_contgcase_bus1:
                    dynawo_branch_contgcase_bus1[line_id] = temp[0]
                else:
                    raise ValueError("Tap ID repeated")
                if line_id not in dynawo_branch_contgcase_bus2:
                    dynawo_branch_contgcase_bus2[line_id] = temp[1]
                else:
                    raise ValueError("Tap ID repeated")

            for twoWindingsTransformer in root.iter("{%s}twoWindingsTransformer" % ns):
                temp = [0, 0]
                twoWindingsTransformer_id = twoWindingsTransformer.get("id")
                if twoWindingsTransformer.get("bus1") is not None:
                    temp[0] = 1
                if twoWindingsTransformer.get("bus2") is not None:
                    temp[1] = 1
                if twoWindingsTransformer_id not in dynawo_branch_contgcase_bus1:
                    dynawo_branch_contgcase_bus1[twoWindingsTransformer_id] = temp[0]
                else:
                    raise ValueError("Tap ID repeated")
                if twoWindingsTransformer_id not in dynawo_branch_contgcase_bus2:
                    dynawo_branch_contgcase_bus2[twoWindingsTransformer_id] = temp[1]
                else:
                    raise ValueError("Tap ID repeated")

            df_dynawo_branch_basecase_bus1 = pd.read_csv(
                save_path + "df_dynawo_branch_basecase_bus1.csv", sep=";", index_col=0
            )

            df_dynawo_branch_basecase_bus2 = pd.read_csv(
                save_path + "df_dynawo_branch_basecase_bus2.csv", sep=";", index_col=0
            )

            data_keys = dynawo_branch_contgcase_bus1.keys()
            data_list = dynawo_branch_contgcase_bus1.values()
            df_dynawo_branch_contgcase_bus1 = pd.DataFrame(
                data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_1"]
            )

            data_keys = dynawo_branch_contgcase_bus2.keys()
            data_list = dynawo_branch_contgcase_bus2.values()
            df_dynawo_branch_contgcase_bus2 = pd.DataFrame(
                data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_2"]
            )

            df_dynawo_branch_diff_1 = copy.deepcopy(df_dynawo_branch_basecase_bus1)

            df_dynawo_branch_diff_1 = df_dynawo_branch_diff_1.rename(
                columns={"TOPO_CHG_VAL_1": "BC_VAL_1"}
            )
            df_dynawo_branch_diff_1["CG_VAL_1"] = df_dynawo_branch_contgcase_bus1[
                "TOPO_CHG_VAL_1"
            ]

            df_dynawo_branch_diff_2 = copy.deepcopy(df_dynawo_branch_basecase_bus2)

            df_dynawo_branch_diff_2 = df_dynawo_branch_diff_2.rename(
                columns={"TOPO_CHG_VAL_2": "BC_VAL_2"}
            )
            df_dynawo_branch_diff_2["CG_VAL_2"] = df_dynawo_branch_contgcase_bus2[
                "TOPO_CHG_VAL_2"
            ]

            df_dynawo_topo_diff = copy.deepcopy(df_dynawo_branch_basecase_bus1)
            df_dynawo_topo_diff = df_dynawo_topo_diff.rename(
                columns={"TOPO_CHG_VAL_1": "BC_VAL_TOPO"}
            )

            df_dynawo_topo_diff["BC_VAL_TOPO"] = (
                df_dynawo_branch_diff_1["BC_VAL_1"]
                + df_dynawo_branch_diff_2["BC_VAL_2"]
            )
            df_dynawo_topo_diff["CG_VAL_TOPO"] = (
                df_dynawo_branch_diff_1["CG_VAL_1"]
                + df_dynawo_branch_diff_2["CG_VAL_2"]
            )

            df_dynawo_branch_diff_1["DIFF"] = (
                df_dynawo_branch_contgcase_bus1["TOPO_CHG_VAL_1"]
                - df_dynawo_branch_basecase_bus1["TOPO_CHG_VAL_1"]
            )

            df_dynawo_branch_diff_1["ABS_DIFF"] = df_dynawo_branch_diff_1["DIFF"].abs()

            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_branch_diff_1["POS_DIFF"] = df_dynawo_branch_diff_1["DIFF"]
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_dynawo_branch_diff_1["NEG_DIFF"] = df_dynawo_branch_diff_1["DIFF"]
            df_dynawo_branch_diff_1.loc[
                df_dynawo_branch_diff_1["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            df_dynawo_branch_diff_2["DIFF"] = (
                df_dynawo_branch_contgcase_bus2["TOPO_CHG_VAL_2"]
                - df_dynawo_branch_basecase_bus2["TOPO_CHG_VAL_2"]
            )

            df_dynawo_branch_diff_2["ABS_DIFF"] = df_dynawo_branch_diff_2["DIFF"].abs()

            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_branch_diff_2["POS_DIFF"] = df_dynawo_branch_diff_2["DIFF"]
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["DIFF"] <= 0, "POS_DIFF"
            ] = 0

            df_dynawo_branch_diff_2["NEG_DIFF"] = df_dynawo_branch_diff_2["DIFF"]
            df_dynawo_branch_diff_2.loc[
                df_dynawo_branch_diff_2["DIFF"] >= 0, "NEG_DIFF"
            ] = 0

            df_dynawo_topo_diff["DIFF1"] = df_dynawo_branch_diff_1["DIFF"]
            df_dynawo_topo_diff["DIFF2"] = df_dynawo_branch_diff_2["DIFF"]

            df_dynawo_topo_diff["DIFF"] = np.select(
                [
                    (df_dynawo_topo_diff["DIFF1"] != 0)
                    | (df_dynawo_topo_diff["DIFF2"] != 0)
                ],
                [1],
                default=0,
            )

            df_dynawo_topo_diff["ABS_DIFF"] = df_dynawo_topo_diff["DIFF"].abs()

            df_dynawo_topo_diff.loc[
                df_dynawo_topo_diff["ABS_DIFF"] != 0, "HAS_CHANGED"
            ] = 1
            df_dynawo_topo_diff.loc[
                df_dynawo_topo_diff["ABS_DIFF"] == 0, "HAS_CHANGED"
            ] = 0

            df_dynawo_topo_diff["POS_DIFF"] = df_dynawo_topo_diff["DIFF"]
            df_dynawo_topo_diff.loc[df_dynawo_topo_diff["DIFF"] <= 0, "POS_DIFF"] = 0

            df_dynawo_topo_diff["NEG_DIFF"] = df_dynawo_topo_diff["DIFF"]
            df_dynawo_topo_diff.loc[df_dynawo_topo_diff["DIFF"] >= 0, "NEG_DIFF"] = 0

            return df_dynawo_topo_diff


# Generate all dropdowns of the output
def create_dropdowns(
    df,
    contg_cases,
    contgcasediffs_contgcaseinit,
    contgcasediffs_data_first_case,
    contgcasediffs_vars_case,
    netwgraph_bus_list,
    netwgraph_nodetypes,
    netwgraph_nodemetrictypes,
    netwgraph_edgetypes,
    netwgraph_edgemetrictype,
    globaltap_aut_diffs_A,
    globaltap_aut_diffs_B,
):
    globaldiffs_def_volt_level = widgets.Dropdown(
        options=["DEFAULT"] + list(df["volt_level"].unique()),
        value="DEFAULT",
        description="VOLT LEVEL",
    )

    globaldiffs_dropdownvarx = widgets.Dropdown(
        options=df.columns[1:], value="volt_level", description="X: "
    )

    globaldiffs_dropdownvary = widgets.Dropdown(
        options=df.columns[2:], value="v_p95", description="Y: "
    )

    contgcasediffs_dropdowndev = widgets.Dropdown(
        options=sorted(contg_cases),
        value=contgcasediffs_contgcaseinit,
        description="Contg. case: ",
    )

    reduced_contgcasediffs_vars_case = list(contgcasediffs_vars_case)
    reduced_contgcasediffs_vars_case.remove("ELEMENT_TYPE")
    reduced_contgcasediffs_vars_case.remove("VAR")
    contgcasediffs_dropdownx = widgets.Dropdown(
        options=reduced_contgcasediffs_vars_case, value="VALUE_A", description="X: "
    )

    contgcasediffs_dropdowny = widgets.Dropdown(
        options=reduced_contgcasediffs_vars_case, value="VALUE_B", description="Y: "
    )

    contgcasediffs_elementdropdown = widgets.Dropdown(
        options=["ALL"] + list(set(contgcasediffs_data_first_case["ELEMENT_TYPE"])),
        value="ALL",
        description="Elem. type: ",
    )

    contgcasediffs_vardropdown = widgets.Dropdown(
        options=list(set(contgcasediffs_data_first_case["VAR"])),
        value="v",
        description="Var: ",
    )

    netwgraph_graph = widgets.Dropdown(
        options=netwgraph_bus_list, value=netwgraph_bus_list[0], description="Node ID: "
    )

    netwgraph_nodetype_drop = widgets.Dropdown(
        options=netwgraph_nodetypes,
        value=netwgraph_nodetypes[0],
        description="Node var: ",
    )

    netwgraph_nodemetrictype_drop = widgets.Dropdown(
        options=netwgraph_nodemetrictypes,
        value=netwgraph_nodemetrictypes[0],
        description="Node metric var: ",
    )

    netwgraph_edgetype_drop = widgets.Dropdown(
        options=netwgraph_edgetypes,
        value=netwgraph_edgetypes[0],
        description="Edge var: ",
    )

    netwgraph_edgemetrictype_drop = widgets.Dropdown(
        options=netwgraph_edgemetrictype,
        value=netwgraph_edgemetrictype[0],
        description="Edge metric var: ",
    )
    contgcasetap_aut_diff_case = widgets.Dropdown(
        options=sorted(contg_cases),
        value=contgcasediffs_contgcaseinit,
        description="Contg. case: ",
    )

    a_var = list(globaltap_aut_diffs_A.index)
    for i in range(len(a_var)):
        a_var[i] = a_var[i].split("-")[-1]
    a_var = list(set(a_var))

    b_var = list(globaltap_aut_diffs_B.index)
    for i in range(len(b_var)):
        b_var[i] = b_var[i].split("-")[-1]
    b_var = list(set(b_var))

    contgcasetap_aut_diff_var_A = widgets.Dropdown(
        options=sorted(a_var), value="ratioTapChanger", description="Aut. var A: "
    )

    contgcasetap_aut_diff_var_B = widgets.Dropdown(
        options=sorted(b_var), value="ratioTapChanger", description="Aut. var B: "
    )

    globaltap_aut_diff_var_plot = widgets.Dropdown(
        options=["ratioTapChanger", "phaseTapChanger"],
        value="ratioTapChanger",
        description="Aut. var: ",
    )

    globaldiffs_diff_metric_type = widgets.Dropdown(
        options=["max", "p95", "mean", "ALL"],
        value="max",
        description="Metric type: ",
    )

    return (
        globaldiffs_def_volt_level,
        globaldiffs_dropdownvarx,
        globaldiffs_dropdownvary,
        contgcasediffs_dropdowndev,
        contgcasediffs_dropdownx,
        contgcasediffs_dropdowny,
        contgcasediffs_elementdropdown,
        contgcasediffs_vardropdown,
        netwgraph_graph,
        netwgraph_nodetype_drop,
        netwgraph_nodemetrictype_drop,
        netwgraph_edgetype_drop,
        netwgraph_edgemetrictype_drop,
        contgcasetap_aut_diff_case,
        contgcasetap_aut_diff_var_A,
        contgcasetap_aut_diff_var_B,
        globaltap_aut_diff_var_plot,
        globaldiffs_diff_metric_type,
    )


# Create all the containers of the output
def create_containers(
    globaldiffs_dropdownvarx,
    globaldiffs_dropdownvary,
    contgcasediffs_dropdowndev,
    contgcasediffs_dropdownx,
    contgcasediffs_dropdowny,
    contgcasediffs_elementdropdown,
    contgcasediffs_vardropdown,
    netwgraph_graph,
    netwgraph_nodetype_drop,
    netwgraph_nodemetrictype_drop,
    netwgraph_edgetype_drop,
    netwgraph_edgemetrictype_drop,
    contgcasetap_aut_diff_case,
    contgcasetap_aut_diff_var_A,
    contgcasetap_aut_diff_var_B,
    globaltap_checka,
    globaltap_checkb,
    contgcasetap_checka,
    contgcasetap_checkb,
    globaltap_aut_trace,
    contgcasediffs_individualtrace,
    contgcasediffs_legendwidget,
    netwgraph_legend1widget,
    netwgraph_legend2widget,
):
    globaldiffs_container = widgets.HBox(
        [globaldiffs_dropdownvarx, globaldiffs_dropdownvary]
    )

    contgcasediffs_container = widgets.HBox(
        [
            contgcasediffs_dropdowndev,
            contgcasediffs_elementdropdown,
            contgcasediffs_vardropdown,
            contgcasediffs_dropdownx,
            contgcasediffs_dropdowny,
        ]
    )

    netwgraph_container = widgets.HBox(
        [
            netwgraph_graph,
            netwgraph_nodetype_drop,
            netwgraph_nodemetrictype_drop,
            netwgraph_edgetype_drop,
            netwgraph_edgemetrictype_drop,
        ]
    )

    globaltap_container_aut = widgets.HBox([globaltap_checka, globaltap_checkb])
    contgcasetap_container_aut = widgets.HBox(
        [
            contgcasetap_aut_diff_case,
            contgcasetap_aut_diff_var_A,
            contgcasetap_checka,
            contgcasetap_aut_diff_var_B,
            contgcasetap_checkb,
        ]
    )

    globaltap_container_aut_trace = widgets.HBox([globaltap_aut_trace])

    contgcasediffs_individualtracecontainer = widgets.HBox(
        [contgcasediffs_individualtrace, contgcasediffs_legendwidget]
    )

    netwgraph_legendcontainer = widgets.HBox(
        [netwgraph_legend1widget, netwgraph_legend2widget]
    )
    return (
        globaldiffs_container,
        contgcasediffs_container,
        netwgraph_container,
        globaltap_container_aut,
        contgcasetap_container_aut,
        globaltap_container_aut_trace,
        contgcasediffs_individualtracecontainer,
        netwgraph_legendcontainer,
    )


def create_buttons():
    button_descriptions_aut = {
        False: "Apply selection below",
        True: "Apply selection below",
    }
    globaltap_button_aut = widgets.ToggleButton(
        False, description=button_descriptions_aut[False]
    )

    button_descriptions_case = {
        False: "Apply selection below",
        True: "Apply Selection below",
    }
    globaldiffs_button_case = widgets.ToggleButton(
        False, description=button_descriptions_case[False]
    )

    button_download_data_opts = {False: "Download Data", True: "Download Data"}
    button_download_data = widgets.ToggleButton(
        False, description=button_download_data_opts[False]
    )
    return globaltap_button_aut, globaldiffs_button_case, button_download_data


def create_check_box():
    globaltap_checka = widgets.Checkbox(
        value=True,
        description="Only cntgs with changes in Sim A",
        disabled=False,
        indent=False,
    )
    globaltap_checkb = widgets.Checkbox(
        value=True,
        description="Only cntgs with changes in Sim B",
        disabled=False,
        indent=False,
    )
    contgcasetap_checka = widgets.Checkbox(
        value=True,
        description="Only devices with changes in Sim A",
        disabled=False,
        indent=False,
    )
    contgcasetap_checkb = widgets.Checkbox(
        value=True,
        description="Only devices with changes in Sim B",
        disabled=False,
        indent=False,
    )
    return globaltap_checka, globaltap_checkb, contgcasetap_checka, contgcasetap_checkb


def create_tap_trace(df, HEIGHT):
    df = df.loc[(df.sim_A != df.sim_B)]
    trace = go.Scatter(
        name="Positions",
        x=df["sim_A"],
        y=df["sim_B"],
        mode="markers",
        text=list(df.index),
    )

    temp_sim_A = min(df["sim_A"], default=None)
    temp_sim_B = min(df["sim_B"], default=None)
    if temp_sim_A is None and temp_sim_B is None:
        min_val = 0
    else:
        min_val = min([temp_sim_A, temp_sim_B]) - 1

    temp_sim_A = max(df["sim_A"], default=None)
    temp_sim_B = max(df["sim_B"], default=None)
    if temp_sim_A is None and temp_sim_B is None:
        max_val = 1
    else:
        max_val = max([temp_sim_A, temp_sim_B]) + 1

    tracel = go.Scatter(
        name="Diagonal",
        x=[min_val, max_val],
        y=[min_val, max_val],
        mode="lines",
        marker_color="red",
        line_width=1,
        xaxis="x1",
        yaxis="y1",
    )

    layout_temp = go.Layout(
        title=dict(text="All cases"),
        xaxis=dict(
            title="SIM_A",
            range=[min_val, max_val],
            tickmode="linear",
        ),
        yaxis=dict(
            title="SIM_B",
            range=[min_val, max_val],
            tickmode="linear",
        ),
        height=HEIGHT,
        width=HEIGHT,
    )

    return go.FigureWidget(data=[trace, tracel], layout=layout_temp)


# Create all the layouts of the output
def create_layouts(
    globaldiffs_dropdownvarx,
    globaldiffs_dropdownvary,
    HEIGHT,
    WIDTH,
    contgcasediffs_contgcaseinit,
    contgcasediffs_dropdownx,
    contgcasediffs_dropdowny,
):
    globaldiffs_layout = go.Layout(
        title=dict(text="Global differences between simulator A and simulator B"),
        xaxis=dict(title=globaldiffs_dropdownvarx.value),
        yaxis=dict(title=globaldiffs_dropdownvary.value),
        height=HEIGHT,
        width=WIDTH,
    )

    contgcasediffs_layout = go.Layout(
        title=dict(text="Case: " + contgcasediffs_contgcaseinit),
        xaxis=dict(title=contgcasediffs_dropdownx.value),
        yaxis=dict(title=contgcasediffs_dropdowny.value),
        height=HEIGHT,
        width=WIDTH,
    )

    contgcasetap_layout = go.Layout(
        title=dict(text="Case: " + contgcasediffs_contgcaseinit),
        xaxis=dict(title="TIME", range=[0, 200]),
        yaxis=dict(title="EVENT"),
        height=HEIGHT,
        width=WIDTH / 2,
    )

    return globaldiffs_layout, contgcasediffs_layout, contgcasetap_layout


# Paint the node colors of the graph
def paint_graph(
    C,
    data,
    nodetype,
    netwgraph_nodemetrictype_drop,
    netwgraph_edgetype_drop,
    netwgraph_edgemetrictype_drop,
):
    # Node color
    data1 = data.loc[(data.VAR == nodetype) & (data.ELEMENT_TYPE == "bus")]
    data1_max = data1[netwgraph_nodemetrictype_drop].max()
    data1_min = data1[netwgraph_nodemetrictype_drop].min()

    data1_max -= data1_min
    for node in C.nodes:
        if (
            len(
                list(data1.loc[(data1.ID == node["id"])][netwgraph_nodemetrictype_drop])
            )
            != 0
        ):
            plasma = cm.get_cmap("plasma", 12)
            c = (
                list(
                    data1.loc[(data1.ID == node["id"])][netwgraph_nodemetrictype_drop]
                )[0]
                - data1_min
            )
            c = c / data1_max
            r = plasma(c)[0] * 256
            g = plasma(c)[1] * 256
            b = plasma(c)[2] * 256
            node["color"] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
        else:
            c = 0
            r = 255
            b = 255
            g = 255
            node["color"] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"

    rangecolor = np.array([[data1_min, data1_max + data1_min]])
    pl.figure(num=23, figsize=(10, 5))
    pl.imshow(rangecolor, cmap="plasma")
    pl.gca().set_visible(False)
    pl.colorbar(orientation="horizontal")
    pl.savefig("legend1.png")
    pl.close()

    # Edge color
    data2 = data.loc[
        (data.VAR == netwgraph_edgetype_drop) & (data.ELEMENT_TYPE != "bus")
    ]
    data2_max = data2[netwgraph_edgemetrictype_drop].max()
    data2_min = data2[netwgraph_edgemetrictype_drop].min()

    data2_max -= data2_min
    for edge in C.edges:
        if (
            len(
                list(data2.loc[(data2.ID == edge["id"])][netwgraph_edgemetrictype_drop])
            )
            != 0
        ):
            viridis = cm.get_cmap("viridis", 12)
            c = (
                list(
                    data2.loc[(data2.ID == edge["id"])][netwgraph_edgemetrictype_drop]
                )[0]
                - data2_min
            )
            c = c / data2_max
            r = viridis(c)[0] * 256
            g = viridis(c)[1] * 256
            b = viridis(c)[2] * 256

            edge["color"] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
        else:
            edge_split = edge["id"].split("_")
            if len(edge_split) > 1:
                max_edge = 0
                enter = False
                for edge_sp in edge_split:
                    if (
                        len(
                            list(
                                data2.loc[(data2.ID == edge_sp)][
                                    netwgraph_edgemetrictype_drop
                                ]
                            )
                        )
                        != 0
                    ):
                        if abs(max_edge) < abs(
                            list(
                                data2.loc[(data2.ID == edge_sp)][
                                    netwgraph_edgemetrictype_drop
                                ]
                            )[0]
                        ):
                            max_edge = list(
                                data2.loc[(data2.ID == edge_sp)][
                                    netwgraph_edgemetrictype_drop
                                ]
                            )[0]
                            enter = True
                if enter:
                    viridis = cm.get_cmap("viridis", 12)
                    c = max_edge - data2_min
                    c = c / data2_max
                    r = viridis(c)[0] * 256
                    g = viridis(c)[1] * 256
                    b = viridis(c)[2] * 256

                    edge["color"] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
                else:
                    c = 0
                    r = 255
                    b = 255
                    g = 255
                    edge["color"] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
            else:
                c = 0
                r = 255
                b = 255
                g = 255
                edge["color"] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"

    rangecolor = np.array([[data2_min, data2_max + data2_min]])
    pl.figure(num=33, figsize=(10, 5))
    pl.imshow(rangecolor, cmap="viridis")
    pl.gca().set_visible(False)
    pl.colorbar(orientation="horizontal")
    pl.savefig("legend2.png")
    pl.close()

    legend1 = pl.imread("legend1.png")
    legend2 = pl.imread("legend2.png")
    pl.imsave("legend1.png", legend1[250:, :, :])
    pl.imsave("legend2.png", legend2[250:, :, :])

    return C


# Define the structure of the output
def show_displays(
    globaltap_aut_diffs_A,
    globaltap_aut_diffs_B,
    globaltap_container_aut,
    contgcasetap_container_aut,
    globaltap_container_aut_trace,
    contgcasetap_aut_diff_dfA_grid,
    contgcasetap_aut_diff_dfB_grid,
    globaltap_trace,
    contgcasetap_groups_traceA,
    contgcasetap_groups_traceB,
    globaldiffs_def_volt_level,
    globaldiffs_diff_metric_type,
    globaldiffs_dfgrid,
    globaldiffs_container,
    globaldiffs_generaltrace,
    contgcasediffs_container,
    contgcasediffs_individualtracecontainer,
    contgcasediffs_individualgrid,
    netwgraph_container,
    netwgraph_C,
    netwgraph_legendcontainer,
    globaltap_button_aut,
    globaldiffs_button_case,
    button_download_data,
    compscore_grid_score,
    compscore_max_n_pass,
    compscore_p95_n_pass,
    compscore_mean_n_pass,
    compscore_total_n_pass,
    DATA_LIMIT,
):
    display(
        HTML(
            data="""
    <style>
        div#notebook-container    { width: 95%; }
        div#menubar-container     { width: 65%; }
        div#maintoolbar-container { width: 99%; }
    </style>
    """
        )
    )

    display(
        Markdown(
            "# RESULTS SUMMARY\n"
            "  * Number of cases that exceed the MAX threshold: "
            f"{compscore_max_n_pass/compscore_total_n_pass:.1%} ({compscore_max_n_pass} of {compscore_total_n_pass})\n"
            "  * Number of cases that exceed the P95 threshold: "
            f"{compscore_p95_n_pass/compscore_total_n_pass:.1%} ({compscore_p95_n_pass} of {compscore_total_n_pass})\n"
            f"  * Number of cases that exceed the MEAN threshold: "
            f"{compscore_mean_n_pass/compscore_total_n_pass:.1%} ({compscore_mean_n_pass} of {compscore_total_n_pass})\n"
        )
    )

    #######################################################################
    # Part I: Global ranking
    #######################################################################
    display(Markdown("# GLOBAL RANKING OF CONTINGENCY CASES"))
    display(
        Markdown(
            "Contingency cases ranked by **compound score**, which consists in a"
            " weighted sum of the norms of the differences in several classes of"
            " variables, between the A and B power flow solutions.  \nSchematically:\n"
            " > SCORE = W_v * (norm of voltage diffs)"
            " + W_p * (norm of real power diffs)"
            " + W_q * (norm of reactive power diffs)"
            " + W_t * (norm of tap position diffs)\n\n"
            "The score comes in three flavors, depending on the kind of norm used:\n"
            "  * **MAX_SCORE**: the maximum of the diffs (a.k.a. L-infinity norm)\n"
            "  * **P95_SCORE**: the 95% percentile of the diffs\n"
            "  * **MEAN_SCORE**: average of the diffs (a.k.a. L-1 norm, divided by N)\n"
        )
    )
    display(compscore_grid_score)

    #######################################################################
    # Part II: Detailed metrics
    #######################################################################
    display(Markdown("# ANALYSIS OF DIFFERENCES BETWEEN A AND B"))

    display(Markdown("## Configurable X-Y plot of PF solution diff metrics"))
    display(
        Markdown(
            "NOTE: In order to avoid performance problems in Plotly, the graph only shows a maximum of "
            + str(DATA_LIMIT)
            + " corresponding to the worst differences **according to the selected metric on the Y axis**."
        )
    )
    display(widgets.HBox([globaldiffs_def_volt_level, globaldiffs_container]))
    display(globaldiffs_generaltrace)
    display(Markdown("## PF solution diff metrics"))
    display(widgets.HBox([globaldiffs_diff_metric_type, globaldiffs_button_case]))
    display(globaldiffs_dfgrid)

    display(Markdown("## Configurable X-Y plot for all values of a given case"))
    display(contgcasediffs_container)
    display(contgcasediffs_individualtracecontainer)
    display(Markdown("## All values of a given case (choose above)"))
    display(contgcasediffs_individualgrid)
    display(button_download_data)

    display(Markdown("## Local topology (network graph around a chosen bus)"))
    display(netwgraph_container)
    netwgraph_html_graph = display(netwgraph_C.show("subgraph.html"), display_id=True)
    print("Node Legend - Edge Legend")
    display(netwgraph_legendcontainer)
    print(
        "If a node/edge is white, it means that the selected metric is not available"
        " for that node/edge."
    )

    #######################################################################
    # Part III: Discrete events
    #######################################################################
    display(Markdown("# TAPS AND CONNECTION/DISCONNECTION EVENTS"))

    display(
        Markdown(
            "## Aggregate tap changes and events per contingency case,"
            " compared to the base case\n"
            "For each contingency case, the table shows the total aggregated"
            " values of:\n"
            "  * NUM_CHANGES: total number of elements that have changed\n"
            "  * ABS_DIFF: total sum of the value differences, in absolute value\n"
            "  * POS_DIFF, NEG_DIFF: total sum of positive (resp. negative) diffs\n\n"
            "Note that the comparisons are done **w.r.t. the base case**."
            " So this provides a rough ranking of **contingencies by severity**."
            " Simulator A is on the left, Simulator B on the right.\n"
        )
    )
    display(widgets.HBox([globaltap_container_aut, globaltap_button_aut]))
    display(
        AppLayout(
            left_sidebar=globaltap_aut_diffs_A,
            right_sidebar=globaltap_aut_diffs_B,
            align_items="center",
        )
    )

    display(Markdown("## Tap values -- A vs. B"))
    display(widgets.HBox([globaltap_trace, globaltap_container_aut_trace]))

    display(
        Markdown(
            "## Details of tap changes and other events (for a contingency case)\n"
            "Select a specific contingency case in the combo box below, and"
            " a variable class, and the grids below will show several measures of"
            " the differences **with respect to the base case** "
            "(Simulator A on the left, Simulator B on the right).  \n"
            "Variable groups:\n"
            "  * branch_bus1, branch_bus2, branch_topo: branch disconnections on"
            "    the From, the To, or both ends, respectively\n"
            "  * ratioTapChanger, phaseTapChanger: changes in tap position\n"
            "  * shunt: connections and disconnections\n\n"
            "Table fields:\n"
            "  * BC_VAL: base case value\n"
            "  * CG_VAL: contingency case value\n"
            "  * DIFF, ABS_DIFF: difference and absolute value of difference, resp.\n"
            "  * HAS_CHANG: whether there has been a change (1) or not (0)\n"
            "  * POS_DIFF, NEG_DIFF: possitive and negative diff values, resp."
            " (REDUNDANT, TO BE REMOVED)\n"
        )
    )
    display(contgcasetap_container_aut)
    display(
        AppLayout(
            left_sidebar=contgcasetap_aut_diff_dfA_grid,
            right_sidebar=contgcasetap_aut_diff_dfB_grid,
            align_items="center",
        )
    )

    display(
        Markdown(
            "## Timeline of events: clustering analysis\n"
            "Events appearing in the Dynawo timeline are analyzed and grouped "
            "based on their mutual 'distance', where the distance is a combination "
            "of distance in time and in space (min impedance path)."
        )
    )
    if contgcasetap_groups_traceB is not None:
        containergroup = widgets.HBox(
            [contgcasetap_groups_traceA, contgcasetap_groups_traceB]
        )
    else:
        containergroup = widgets.HBox([contgcasetap_groups_traceA])
    display(containergroup)

    return netwgraph_html_graph


def get_renderers(MAX_THRESH, P95_THRESH, MEAN_THRESH):
    compscore_renderers = {
        "MAX_SCORE": ipydatagrid.TextRenderer(
            text_color="black",
            background_color=ipydatagrid.Expr(
                '"red" if '
                + str(MAX_THRESH + (MAX_THRESH * 0.25))
                + ' < cell.value else "orange" if '
                + str(MAX_THRESH)
                + ' < cell.value else "green"'
            ),
        ),
        "P95_SCORE": ipydatagrid.TextRenderer(
            text_color="black",
            background_color=ipydatagrid.Expr(
                '"red" if '
                + str(P95_THRESH + (P95_THRESH * 0.25))
                + ' < cell.value else "orange" if '
                + str(P95_THRESH)
                + ' < cell.value else "green"'
            ),
        ),
        "MEAN_SCORE": ipydatagrid.TextRenderer(
            text_color="black",
            background_color=ipydatagrid.Expr(
                '"red" if '
                + str(MEAN_THRESH + (MEAN_THRESH * 0.25))
                + ' < cell.value else "orange" if '
                + str(MEAN_THRESH)
                + ' < cell.value else "green"'
            ),
        ),
    }
    return compscore_renderers


def get_iidm_file(DWO_DWO, RESULTS_DIR, BASECASE):
    if DWO_DWO == 0:
        tree = etree.parse(
            RESULTS_DIR + BASECASE + "/JOB.xml", etree.XMLParser(remove_blank_text=True)
        )
        root = tree.getroot()
        ns = etree.QName(root).namespace
        jobs = root.findall("{%s}job" % ns)
        last_job = jobs[-1]
        modeler = last_job.find("{%s}modeler" % ns)
        network = modeler.find("{%s}network" % ns)
        netwgraph_iidm_file = network.get("iidmFile")
        netwgraph_iidm_file = RESULTS_DIR + BASECASE + "/" + netwgraph_iidm_file
    else:
        if DWO_DWO == 1:
            tree = etree.parse(
                RESULTS_DIR + BASECASE + "/JOB_A.xml",
                etree.XMLParser(remove_blank_text=True),
            )
            root = tree.getroot()
            ns = etree.QName(root).namespace
            jobs = root.findall("{%s}job" % ns)
            last_job = jobs[-1]
            modeler = last_job.find("{%s}modeler" % ns)
            network = modeler.find("{%s}network" % ns)
            netwgraph_iidm_file = network.get("iidmFile")
            netwgraph_iidm_file = RESULTS_DIR + BASECASE + "/" + netwgraph_iidm_file
        else:
            if DWO_DWO == 2:
                tree = etree.parse(
                    RESULTS_DIR + BASECASE + "/JOB_B.xml",
                    etree.XMLParser(remove_blank_text=True),
                )
                root = tree.getroot()
                ns = etree.QName(root).namespace
                jobs = root.findall("{%s}job" % ns)
                last_job = jobs[-1]
                modeler = last_job.find("{%s}modeler" % ns)
                network = modeler.find("{%s}network" % ns)
                netwgraph_iidm_file = network.get("iidmFile")
                netwgraph_iidm_file = RESULTS_DIR + BASECASE + "/" + netwgraph_iidm_file
            else:
                raise Exception("No valid DWO_DWO option")
    return netwgraph_iidm_file


# Run the program
def run_all(
    RESULTS_DIR,
    BASECASE,
    ELEMENTS,
    PREFIX,
    PF_SOL_DIR,
    DATA_LIMIT,
    HEIGHT,
    WIDTH,
    SUBGRAPH_TYPE,
    SUBGRAPH_VALUE,
    DWO_DWO,
    W_V,
    W_P,
    W_Q,
    W_T,
    MAX_THRESH,
    P95_THRESH,
    MEAN_THRESH,
):
    # We have to supress a numpy warning
    warnings.simplefilter(action="ignore", category=FutureWarning)

    # Management the selection of dropdown parameters and on_click options
    def globaldiffs_response(change):
        if globaldiffs_diff_metric_type.value == "max":
            df2 = globaldiffs_df[
                [
                    "contg_case",
                    "volt_level",
                    "angle_max",
                    "p_max",
                    "p1_max",
                    "p2_max",
                    "q_max",
                    "q1_max",
                    "q2_max",
                    "tap_max",
                    "v_max",
                ]
            ]
        elif globaldiffs_diff_metric_type.value == "p95":
            df2 = globaldiffs_df[
                [
                    "contg_case",
                    "volt_level",
                    "angle_p95",
                    "p_p95",
                    "p1_p95",
                    "p2_p95",
                    "q_p95",
                    "q1_p95",
                    "q2_p95",
                    "tap_p95",
                    "v_p95",
                ]
            ]
        elif globaldiffs_diff_metric_type.value == "mean":
            df2 = globaldiffs_df[
                [
                    "contg_case",
                    "volt_level",
                    "angle_mean",
                    "p_mean",
                    "p1_mean",
                    "p2_mean",
                    "q_mean",
                    "q1_mean",
                    "q2_mean",
                    "tap_mean",
                    "v_mean",
                ]
            ]
        else:
            df2 = globaldiffs_df

        if globaldiffs_def_volt_level.value == "DEFAULT":
            df1 = globaldiffs_df
        else:
            df1 = globaldiffs_df.loc[
                (globaldiffs_df.volt_level == globaldiffs_def_volt_level.value)
            ]

        # PERF: Plotly starts showing horrible performance with more than 5,000 points
        if df1.shape[0] > DATA_LIMIT:
            df1 = df1.reindex(
                df1[globaldiffs_dropdownvary.value].abs().sort_values().index
            )
            df1 = df1[-DATA_LIMIT:]

        with globaldiffs_generaltrace.batch_update():
            globaldiffs_dfgrid.data = df2
            globaldiffs_generaltrace.data[0].x = df1[globaldiffs_dropdownvarx.value]
            globaldiffs_generaltrace.data[0].y = df1[globaldiffs_dropdownvary.value]
            globaldiffs_generaltrace.data[0].name = (
                globaldiffs_dropdownvarx.value + "_" + globaldiffs_dropdownvary.value
            )
            globaldiffs_generaltrace.data[0].text = (
                df1["contg_case"] + "_(" + df1["volt_level"] + ")"
            )
            globaldiffs_generaltrace.layout.xaxis.title = globaldiffs_dropdownvarx.value
            globaldiffs_generaltrace.layout.yaxis.title = globaldiffs_dropdownvary.value

    def contgcasediffs_individual_case(case):
        df1 = read_case(case, PF_SOL_DIR, PREFIX)
        globaldiffs_dfgrid.clear_selection()
        with contgcasediffs_individualtrace.batch_update():
            if (
                contgcasediffs_elementdropdown.value != "ALL"
                and contgcasediffs_vardropdown.value != "ALL"
            ):
                df1 = df1.loc[
                    (df1.ELEMENT_TYPE == contgcasediffs_elementdropdown.value)
                    & (df1.VAR == contgcasediffs_vardropdown.value)
                ]
            else:
                if (
                    contgcasediffs_elementdropdown.value != "ALL"
                    and contgcasediffs_vardropdown.value == "ALL"
                ):
                    df1 = df1.loc[
                        (df1.ELEMENT_TYPE == contgcasediffs_elementdropdown.value)
                    ]
                else:
                    if (
                        contgcasediffs_elementdropdown.value == "ALL"
                        and contgcasediffs_vardropdown.value != "ALL"
                    ):
                        df1 = df1.loc[(df1.VAR == contgcasediffs_vardropdown.value)]

            contgcasediffs_individualgrid.data = df1.sort_values("ID")
            # PERF: Plotly starts showing horrible performance with more than 5,000 points
            contgcasediffs_individualtrace.data[0].x = df1[
                contgcasediffs_dropdownx.value
            ]
            contgcasediffs_individualtrace.data[0].y = df1[
                contgcasediffs_dropdowny.value
            ]
            contgcasediffs_individualtrace.data[0].name = (
                contgcasediffs_dropdownx.value + "_" + contgcasediffs_dropdowny.value
            )
            contgcasediffs_individualtrace.data[0].text = df1["ID"]
            colordata = create_colors(df1)
            contgcasediffs_individualtrace.data[0].marker = dict(color=colordata)
            contgcasediffs_individualtrace.layout.xaxis.title = (
                contgcasediffs_dropdownx.value
            )
            contgcasediffs_individualtrace.layout.yaxis.title = (
                contgcasediffs_dropdowny.value
            )
            contgcasediffs_individualtrace.layout.title.text = "Case: " + case
            contgcasediffs_dropdowndev.value = case

    def contgcasetap_individual_aut_group(case):
        df1, df2 = read_aut_group(case, PF_SOL_DIR, DWO_DWO, PREFIX)
        # PERF: Plotly starts showing horrible performance with more than 5,000 points
        with contgcasetap_groups_traceA.batch_update():
            df1 = df1.sort_values("GROUP", axis=0)
            color = list(df1["GROUP"])
            if len(color) != 0:
                max_val = max(color)
            else:
                max_val = 0
            plasma = cm.get_cmap("plasma", 12)
            for i in range(len(color)):
                color[i] = color[i] / (max_val + 1)
                r = plasma(color[i])[0] * 256
                g = plasma(color[i])[1] * 256
                b = plasma(color[i])[2] * 256
                color[i] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
            contgcasetap_groups_traceA.data[0].x = df1["TIME"]
            contgcasetap_groups_traceA.data[0].y = df1["DEVICE"]
            contgcasetap_groups_traceA.data[0].text = df1["EVENT_MESSAGE"]
            contgcasetap_groups_traceA.data[0].marker = dict(color=color)
            contgcasetap_groups_traceA.layout.xaxis.range = [0, 200]
            contgcasetap_groups_traceA.layout.title.text = "Case: " + case
        if df2 is not None:
            with contgcasetap_groups_traceB.batch_update():
                df2 = df2.sort_values("GROUP", axis=0)
                color = list(df2["GROUP"])
                if len(color) != 0:
                    max_val = max(color)
                else:
                    max_val = 0
                plasma = cm.get_cmap("plasma", 12)
                for i in range(len(color)):
                    color[i] = color[i] / (max_val + 1)
                    r = plasma(color[i])[0] * 256
                    g = plasma(color[i])[1] * 256
                    b = plasma(color[i])[2] * 256
                    color[i] = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"
                contgcasetap_groups_traceB.data[0].x = df2["TIME"]
                contgcasetap_groups_traceB.data[0].y = df2["DEVICE"]
                contgcasetap_groups_traceB.data[0].text = df2["EVENT_MESSAGE"]
                contgcasetap_groups_traceB.data[0].marker = dict(color=color)
                contgcasetap_groups_traceB.layout.xaxis.range = [0, 200]
                contgcasetap_groups_traceB.layout.title.text = "Case: " + case

    def contgcasediffs_update_case(trace, points, selector):
        name = trace.text[points.point_inds[0]].split("_(")
        contgcasediffs_individual_case(name[0])

    def contgcasediffs_response(change):
        contgcasediffs_individual_case(contgcasediffs_dropdowndev.value)

    def contgcasediffs_response_button(change):
        if len(globaldiffs_dfgrid.selections) != 0:
            case = globaldiffs_dfgrid.selected_cell_values[0]
            globaldiffs_dfgrid.clear_selection()

        contgcasediffs_individual_case(case)

    def contgcasetap_response_autA(change):
        contgcasetap_aut_diff_dfA_contgcase = create_aut_df(
            RESULTS_DIR,
            1,
            contgcasetap_aut_diff_case.value,
            PREFIX,
            BASECASE,
            DWO_DWO,
            contgcasetap_aut_diff_var_A.value,
        )

        if contgcasetap_checka.value:
            contgcasetap_aut_diff_dfA_contgcase = (
                contgcasetap_aut_diff_dfA_contgcase.loc[
                    (contgcasetap_aut_diff_dfA_contgcase.HAS_CHANGED != 0)
                ]
            )
            contgcasetap_aut_diff_dfA_contgcase = (
                contgcasetap_aut_diff_dfA_contgcase.drop(columns=["HAS_CHANGED"])
            )

        contgcasetap_aut_diff_dfA_grid.data = contgcasetap_aut_diff_dfA_contgcase
        contgcasetap_aut_diff_dfA_grid.base_column_size = int(
            (WIDTH / 2 / 1.1) / len(contgcasetap_aut_diff_dfA_contgcase.columns)
        )

    def contgcasetap_response_autB(change):
        contgcasetap_aut_diff_dfB_contgcase = create_aut_df(
            RESULTS_DIR,
            2,
            contgcasetap_aut_diff_case.value,
            PREFIX,
            BASECASE,
            DWO_DWO,
            contgcasetap_aut_diff_var_B.value,
        )

        if contgcasetap_checkb.value:
            contgcasetap_aut_diff_dfB_contgcase = (
                contgcasetap_aut_diff_dfB_contgcase.loc[
                    (contgcasetap_aut_diff_dfB_contgcase.HAS_CHANGED != 0)
                ]
            )
            contgcasetap_aut_diff_dfB_contgcase = (
                contgcasetap_aut_diff_dfB_contgcase.drop(columns=["HAS_CHANGED"])
            )

        contgcasetap_aut_diff_dfB_grid.data = contgcasetap_aut_diff_dfB_contgcase
        contgcasetap_aut_diff_dfB_grid.base_column_size = int(
            (WIDTH / 2 / 1.1) / len(contgcasetap_aut_diff_dfB_contgcase.columns)
        )

    def contgcasetap_response_aut_button(change):
        # Ipydatagrid does not have the option to observe events. What it does is put in a buffer the selected cells.
        # In order to solve this, a button is created and it takes the value of the buffer and applies the changes
        # manually.
        if len(globaltap_aut_diffs_A_grid.selections) != 0:
            contgcasetap_aut_diff_case.value = (
                globaltap_aut_diffs_A_grid.selected_cell_values[4][len(PREFIX) + 1 :]
            )

        elif len(globaltap_aut_diffs_B_grid.selections) != 0:
            contgcasetap_aut_diff_case.value = (
                globaltap_aut_diffs_B_grid.selected_cell_values[4][len(PREFIX) + 1 :]
            )

        contgcasetap_response_aut("")

    def contgcasetap_response_aut(change):
        globaltap_aut_diffs_A_grid.clear_selection()
        globaltap_aut_diffs_B_grid.clear_selection()
        contgcasetap_aut_diff_dfA_contgcase = create_aut_df(
            RESULTS_DIR,
            1,
            contgcasetap_aut_diff_case.value,
            PREFIX,
            BASECASE,
            DWO_DWO,
            contgcasetap_aut_diff_var_A.value,
        )
        contgcasetap_aut_diff_dfB_contgcase = create_aut_df(
            RESULTS_DIR,
            2,
            contgcasetap_aut_diff_case.value,
            PREFIX,
            BASECASE,
            DWO_DWO,
            contgcasetap_aut_diff_var_B.value,
        )

        if contgcasetap_checka.value:
            contgcasetap_aut_diff_dfA_contgcase = (
                contgcasetap_aut_diff_dfA_contgcase.loc[
                    (contgcasetap_aut_diff_dfA_contgcase.HAS_CHANGED != 0)
                ]
            )
            contgcasetap_aut_diff_dfA_contgcase = (
                contgcasetap_aut_diff_dfA_contgcase.drop(columns=["HAS_CHANGED"])
            )

        if contgcasetap_checkb.value:
            contgcasetap_aut_diff_dfB_contgcase = (
                contgcasetap_aut_diff_dfB_contgcase.loc[
                    (contgcasetap_aut_diff_dfB_contgcase.HAS_CHANGED != 0)
                ]
            )
            contgcasetap_aut_diff_dfB_contgcase = (
                contgcasetap_aut_diff_dfB_contgcase.drop(columns=["HAS_CHANGED"])
            )

        contgcasetap_aut_diff_dfA_grid.data = contgcasetap_aut_diff_dfA_contgcase
        contgcasetap_aut_diff_dfA_grid.base_column_size = int(
            (WIDTH / 2 / 1.1) / len(contgcasetap_aut_diff_dfA_contgcase.columns)
        )
        contgcasetap_aut_diff_dfB_grid.data = contgcasetap_aut_diff_dfB_contgcase
        contgcasetap_aut_diff_dfB_grid.base_column_size = int(
            (WIDTH / 2 / 1.1) / len(contgcasetap_aut_diff_dfB_contgcase.columns)
        )
        contgcasetap_individual_aut_group(contgcasetap_aut_diff_case.value)

    def response_download_data(change):
        temp_dict = {
            "text": list(globaltap_trace.data[0].text),
            "x": list(globaltap_trace.data[0].x),
            "y": list(globaltap_trace.data[0].y),
        }
        pd.DataFrame(temp_dict).to_csv("comparison_aut_states.csv", sep=";")
        temp_dict = {
            "text": list(contgcasediffs_individualtrace.data[0].text),
            "x": list(contgcasediffs_individualtrace.data[0].x),
            "y": list(contgcasediffs_individualtrace.data[0].y),
        }
        pd.DataFrame(temp_dict).to_csv("indv_case_diffs.csv", sep=";")
        temp_dict = {
            "text": list(globaldiffs_generaltrace.data[0].text),
            "x": list(globaldiffs_generaltrace.data[0].x),
            "y": list(globaldiffs_generaltrace.data[0].y),
        }
        pd.DataFrame(temp_dict).to_csv("global_case_diffs.csv", sep=";")

    def globaltap_response_general_aut_A(change):
        globaltap_aut_diffs_A, globaltap_aut_diffs_B = read_csv_aut_diffs(
            RESULTS_DIR + "/" + PREFIX + "/aut/"
        )
        if globaltap_checka.value:
            globaltap_aut_diffs_A = globaltap_aut_diffs_A.loc[
                (globaltap_aut_diffs_A.NUM_CHANGES != 0)
            ]
        globaltap_aut_diffs_A_grid.data = globaltap_aut_diffs_A
        globaltap_aut_diffs_A_grid.base_column_size = int(
            (WIDTH / 2 / 1.1) / len(globaltap_aut_diffs_A.columns)
        )

    def globaltap_response_general_aut_B(change):
        globaltap_aut_diffs_A, globaltap_aut_diffs_B = read_csv_aut_diffs(
            RESULTS_DIR + "/" + PREFIX + "/aut/"
        )
        if globaltap_checkb.value:
            globaltap_aut_diffs_B = globaltap_aut_diffs_B.loc[
                (globaltap_aut_diffs_B.NUM_CHANGES != 0)
            ]
        globaltap_aut_diffs_B_grid.data = globaltap_aut_diffs_B
        globaltap_aut_diffs_B_grid.base_column_size = int(
            (WIDTH / 2 / 1.1) / len(globaltap_aut_diffs_B.columns)
        )

    def globaltap_response_aut_plot(change):
        globaltap_df_aut = read_aut_case(
            RESULTS_DIR + "/" + PREFIX + "/aut/", globaltap_aut_diff_var_plot.value
        )
        with globaltap_trace.batch_update():
            temp_sim_A = min(globaltap_df_aut["sim_A"], default=None)
            temp_sim_B = min(globaltap_df_aut["sim_B"], default=None)
            if temp_sim_A is None and temp_sim_B is None:
                min_val = 0
            else:
                min_val = min([temp_sim_A, temp_sim_B]) - 1

            temp_sim_A = max(globaltap_df_aut["sim_A"], default=None)
            temp_sim_B = max(globaltap_df_aut["sim_B"], default=None)
            if temp_sim_A is None and temp_sim_B is None:
                max_val = 1
            else:
                max_val = max([temp_sim_A, temp_sim_B]) + 1

            globaltap_trace.data[0].x = globaltap_df_aut["sim_A"]
            globaltap_trace.data[0].y = globaltap_df_aut["sim_B"]
            globaltap_trace.data[0].text = list(globaltap_df_aut.index)
            globaltap_trace.layout.xaxis = dict(
                title="SIM_A",
                range=[min_val, max_val],
                tickmode="linear",
            )
            globaltap_trace.layout.yaxis = dict(
                title="SIM_B",
                range=[min_val, max_val],
                tickmode="linear",
            )

            globaltap_trace.data[1].x = [min_val, max_val]
            globaltap_trace.data[1].y = [min_val, max_val]

    def netwgraph_response(change):
        with contgcasediffs_individualtrace.batch_update():
            C = create_graph.get_subgraph(
                netwgraph_G, netwgraph_graph.value, SUBGRAPH_TYPE, SUBGRAPH_VALUE
            )
            C = paint_graph(
                C,
                contgcasediffs_data_first_case,
                netwgraph_nodetype_drop.value,
                netwgraph_nodemetrictype_drop.value,
                netwgraph_edgetype_drop.value,
                netwgraph_edgemetrictype_drop.value,
            )
            netwgraph_html_graph.update(C.show("subgraph.html"))
            netwgraph_file1 = open("legend1.png", "rb")
            netwgraph_legend1 = netwgraph_file1.read()
            netwgraph_file2 = open("legend2.png", "rb")
            netwgraph_legend2 = netwgraph_file2.read()
            netwgraph_legend1widget.value = netwgraph_legend1
            netwgraph_legend2widget.value = netwgraph_legend2

    def get_matching_df():
        if globaldiffs_diff_metric_type.value == "max":
            globaldiffs_matching_df = globaldiffs_df[
                [
                    "contg_case",
                    "volt_level",
                    "angle_max",
                    "p_max",
                    "p1_max",
                    "p2_max",
                    "q_max",
                    "q1_max",
                    "q2_max",
                    "tap_max",
                    "v_max",
                ]
            ]
        elif globaldiffs_diff_metric_type.value == "p95":
            globaldiffs_matching_df = globaldiffs_df[
                [
                    "contg_case",
                    "volt_level",
                    "angle_p95",
                    "p_p95",
                    "p1_p95",
                    "p2_p95",
                    "q_p95",
                    "q1_p95",
                    "q2_p95",
                    "tap_p95",
                    "v_p95",
                ]
            ]
        elif globaldiffs_diff_metric_type.value == "mean":
            globaldiffs_matching_df = globaldiffs_df[
                [
                    "contg_case",
                    "volt_level",
                    "angle_mean",
                    "p_mean",
                    "p1_mean",
                    "p2_mean",
                    "q_mean",
                    "q1_mean",
                    "q2_mean",
                    "tap_mean",
                    "v_mean",
                ]
            ]
        return globaldiffs_matching_df

    # This notebook is divided in four sections:
    # - compscore
    # - globaltap
    # - contgcasetap
    # - globaldiffs
    # - contgcasediffs
    # - netwgraph

    # Define const values
    netwgraph_nodetypes = ["v", "angle", "p", "q"]
    netwgraph_nodemetrictypes = ["DIFF", "ABS_ERR", "REL_ERR", "VALUE_A", "VALUE_B"]
    netwgraph_edgetypes = ["p1", "p2", "q1", "q2"]
    netwgraph_edgemetrictype = ["DIFF", "ABS_ERR", "REL_ERR", "VALUE_A", "VALUE_B"]

    do_displaybutton()

    # Get aut diffs
    globaltap_aut_diffs_A, globaltap_aut_diffs_B = read_csv_aut_diffs(
        RESULTS_DIR + "/" + PREFIX + "/aut/"
    )

    # Get global diffs
    globaldiffs_df = read_csv_metrics(PF_SOL_DIR)

    # Create all the checkboxes
    (
        globaltap_checka,
        globaltap_checkb,
        contgcasetap_checka,
        contgcasetap_checkb,
    ) = create_check_box()

    # Get list of contingency cases
    contg_cases = list(globaldiffs_df["contg_case"].unique())
    contgcasediffs_contgcaseinit = contg_cases[0]

    # Read the first contingency to put default data
    contgcasediffs_data_first_case = read_case(
        contgcasediffs_contgcaseinit, PF_SOL_DIR, PREFIX
    )

    # Read the groups of the different automatas
    (
        contgcasetap_aut_group_data_first_caseA,
        contgcasetap_aut_group_data_first_caseB,
    ) = read_aut_group(contgcasediffs_contgcaseinit, PF_SOL_DIR, DWO_DWO, PREFIX)

    # Get all the contingency diffs vars
    contgcasediffs_vars_case = contgcasediffs_data_first_case.columns[1:]

    # Get the bus list for subgraph selection
    netwgraph_bus_list = sorted(
        list(
            set(
                contgcasediffs_data_first_case.loc[
                    (contgcasediffs_data_first_case.ELEMENT_TYPE == "bus")
                ]["ID"]
            )
        )
    )

    # Read global aut df and create the trace
    globaltap_df_aut = read_aut_case(
        RESULTS_DIR + "/" + PREFIX + "/aut/", "ratioTapChanger"
    )
    globaltap_trace = create_tap_trace(globaltap_df_aut, HEIGHT)

    # Get all the dropdowns
    (
        globaldiffs_def_volt_level,
        globaldiffs_dropdownvarx,
        globaldiffs_dropdownvary,
        contgcasediffs_dropdowndev,
        contgcasediffs_dropdownx,
        contgcasediffs_dropdowny,
        contgcasediffs_elementdropdown,
        contgcasediffs_vardropdown,
        netwgraph_graph,
        netwgraph_nodetype_drop,
        netwgraph_nodemetrictype_drop,
        netwgraph_edgetype_drop,
        netwgraph_edgemetrictype_drop,
        contgcasetap_aut_diff_case,
        contgcasetap_aut_diff_var_A,
        contgcasetap_aut_diff_var_B,
        globaltap_aut_diff_var_plot,
        globaldiffs_diff_metric_type,
    ) = create_dropdowns(
        globaldiffs_df,
        contg_cases,
        contgcasediffs_contgcaseinit,
        contgcasediffs_data_first_case,
        contgcasediffs_vars_case,
        netwgraph_bus_list,
        netwgraph_nodetypes,
        netwgraph_nodemetrictypes,
        netwgraph_edgetypes,
        netwgraph_edgemetrictype,
        globaltap_aut_diffs_A,
        globaltap_aut_diffs_B,
    )

    # Get all the layouts
    globaldiffs_layout, contgcasediffs_layout, contgcasetap_layout = create_layouts(
        globaldiffs_dropdownvarx,
        globaldiffs_dropdownvary,
        HEIGHT,
        WIDTH,
        contgcasediffs_contgcaseinit,
        contgcasediffs_dropdownx,
        contgcasediffs_dropdowny,
    )

    globaldiffs_current_general_trace = create_general_trace(
        globaldiffs_df,
        globaldiffs_dropdownvarx.value,
        globaldiffs_dropdownvary.value,
        DATA_LIMIT,
    )

    (
        compscore_df_score,
        compscore_max_n_pass,
        compscore_p95_n_pass,
        compscore_mean_n_pass,
        compscore_total_n_pass,
    ) = calc_global_score(
        globaldiffs_df, W_V, W_P, W_Q, W_T, MAX_THRESH, MEAN_THRESH, P95_THRESH
    )

    # Paint score grid
    compscore_renderers = get_renderers(MAX_THRESH, P95_THRESH, MEAN_THRESH)

    compscore_grid_score = ipydatagrid.DataGrid(
        compscore_df_score,
        base_column_size=int((WIDTH / 2 / 1.1) / len(compscore_df_score.columns)),
        renderers=compscore_renderers,
    )

    # Individual trace for contingency diffs with filters
    if (
        contgcasediffs_elementdropdown.value != "ALL"
        and contgcasediffs_vardropdown.value != "ALL"
    ):
        contgcasediffs_data_first_case_filter = contgcasediffs_data_first_case.loc[
            (
                contgcasediffs_data_first_case.ELEMENT_TYPE
                == contgcasediffs_elementdropdown.value
            )
            & (contgcasediffs_data_first_case.VAR == contgcasediffs_vardropdown.value)
        ]
    else:
        if (
            contgcasediffs_elementdropdown.value != "ALL"
            and contgcasediffs_vardropdown.value == "ALL"
        ):
            contgcasediffs_data_first_case_filter = contgcasediffs_data_first_case.loc[
                (
                    contgcasediffs_data_first_case.ELEMENT_TYPE
                    == contgcasediffs_elementdropdown.value
                )
            ]
        else:
            if (
                contgcasediffs_elementdropdown.value == "ALL"
                and contgcasediffs_vardropdown.value != "ALL"
            ):
                contgcasediffs_data_first_case_filter = (
                    contgcasediffs_data_first_case.loc[
                        (
                            contgcasediffs_data_first_case.VAR
                            == contgcasediffs_vardropdown.value
                        )
                    ]
                )

    contgcasediffs_current_individual_trace = create_individual_trace(
        contgcasediffs_data_first_case_filter,
        contgcasediffs_dropdownx.value,
        contgcasediffs_dropdowny.value,
    )

    # Individual trace for contingency taps
    (
        contgcasetap_current_aut_group_traceA,
        contgcasetap_current_aut_group_traceB,
    ) = create_aut_group_trace(
        contgcasetap_aut_group_data_first_caseA,
        contgcasetap_aut_group_data_first_caseB,
    )

    # Individual grid for contingency taps
    contgcasetap_aut_diff_dfA_contgcase = create_aut_df(
        RESULTS_DIR,
        1,
        contgcasetap_aut_diff_case.value,
        PREFIX,
        BASECASE,
        DWO_DWO,
        contgcasetap_aut_diff_var_A.value,
    )

    contgcasetap_aut_diff_dfB_contgcase = create_aut_df(
        RESULTS_DIR,
        2,
        contgcasetap_aut_diff_case.value,
        PREFIX,
        BASECASE,
        DWO_DWO,
        contgcasetap_aut_diff_var_B.value,
    )

    if contgcasetap_checka.value:
        contgcasetap_aut_diff_dfA_contgcase = contgcasetap_aut_diff_dfA_contgcase.loc[
            (contgcasetap_aut_diff_dfA_contgcase.HAS_CHANGED != 0)
        ]
        contgcasetap_aut_diff_dfA_contgcase = contgcasetap_aut_diff_dfA_contgcase.drop(
            columns=["HAS_CHANGED"]
        )
    contgcasetap_aut_diff_dfA_grid = ipydatagrid.DataGrid(
        contgcasetap_aut_diff_dfA_contgcase,
        base_column_size=int(
            (WIDTH / 2 / 1.1) / len(contgcasetap_aut_diff_dfA_contgcase.columns)
        ),
    )

    if contgcasetap_checkb.value:
        contgcasetap_aut_diff_dfB_contgcase = contgcasetap_aut_diff_dfB_contgcase.loc[
            (contgcasetap_aut_diff_dfB_contgcase.HAS_CHANGED != 0)
        ]
        contgcasetap_aut_diff_dfB_contgcase = contgcasetap_aut_diff_dfB_contgcase.drop(
            columns=["HAS_CHANGED"]
        )
    contgcasetap_aut_diff_dfB_grid = ipydatagrid.DataGrid(
        contgcasetap_aut_diff_dfB_contgcase,
        base_column_size=int(
            (WIDTH / 2 / 1.1) / len(contgcasetap_aut_diff_dfB_contgcase.columns)
        ),
    )

    # Global grid for contingency taps
    if globaltap_checka.value:
        globaltap_aut_diffs_A = globaltap_aut_diffs_A.loc[
            (globaltap_aut_diffs_A.NUM_CHANGES != 0)
        ]
        globaltap_aut_diffs_A_grid = ipydatagrid.DataGrid(
            globaltap_aut_diffs_A,
            base_column_size=int(
                (WIDTH / 2 / 1.1) / len(globaltap_aut_diffs_A.columns)
            ),
            selection_mode="row",
        )

    if globaltap_checkb.value:
        globaltap_aut_diffs_B = globaltap_aut_diffs_B.loc[
            (globaltap_aut_diffs_B.NUM_CHANGES != 0)
        ]
        globaltap_aut_diffs_B_grid = ipydatagrid.DataGrid(
            globaltap_aut_diffs_B,
            base_column_size=int(
                (WIDTH / 2 / 1.1) / len(globaltap_aut_diffs_B.columns)
            ),
            selection_mode="row",
        )

    # Match globaldiffs_df with diffs type and creation of grid
    globaldiffs_matching_df = get_matching_df()

    globaldiffs_dfgrid = ipydatagrid.DataGrid(
        globaldiffs_matching_df,
        base_column_size=int((WIDTH / 1.03) / len(globaldiffs_matching_df.columns)),
        selection_mode="row",
    )

    # Create global and individual diffs trace widget
    globaldiffs_generaltrace = go.FigureWidget(
        data=[globaldiffs_current_general_trace], layout=globaldiffs_layout
    )

    contgcasediffs_individualtrace = go.FigureWidget(
        data=[contgcasediffs_current_individual_trace], layout=contgcasediffs_layout
    )

    # Create individual tap trace widget
    contgcasetap_groups_traceA = go.FigureWidget(
        data=[contgcasetap_current_aut_group_traceA], layout=contgcasetap_layout
    )
    if contgcasetap_current_aut_group_traceB is not None:
        contgcasetap_groups_traceB = go.FigureWidget(
            data=[contgcasetap_current_aut_group_traceB], layout=contgcasetap_layout
        )
    else:
        contgcasetap_groups_traceB = None

    # Get manual legend for contgcasediffs_individualtrace
    contgcasediffs_filelegend = open("legend0.png", "rb")
    contgcasediffs_legend = contgcasediffs_filelegend.read()
    contgcasediffs_legendwidget = widgets.Image(
        value=contgcasediffs_legend, format="png"
    )

    contgcasediffs_individualgrid = ipydatagrid.DataGrid(
        contgcasediffs_data_first_case_filter,
        base_column_size=int(
            (WIDTH / 1.03) / len(contgcasediffs_data_first_case_filter.columns)
        ),
    )

    # Graph creation
    # Get iidm file
    netwgraph_iidm_file = get_iidm_file(DWO_DWO, RESULTS_DIR, BASECASE)

    # Get default graph
    netwgraph_G, netwgraph_C = get_initial_graph(
        netwgraph_iidm_file, netwgraph_graph.value, SUBGRAPH_TYPE, SUBGRAPH_VALUE
    )

    # Paint with colors the graph
    netwgraph_C = paint_graph(
        netwgraph_C,
        contgcasediffs_data_first_case,
        netwgraph_nodetype_drop.value,
        netwgraph_nodemetrictype_drop.value,
        netwgraph_edgetype_drop.value,
        netwgraph_edgemetrictype_drop.value,
    )

    # Create manual legends for graph
    netwgraph_file1 = open("legend1.png", "rb")
    netwgraph_legend1 = netwgraph_file1.read()
    netwgraph_file2 = open("legend2.png", "rb")
    netwgraph_legend2 = netwgraph_file2.read()

    netwgraph_legend1widget = widgets.Image(
        value=netwgraph_legend1, format="png", width=WIDTH / 2, height=HEIGHT / 2
    )

    netwgraph_legend2widget = widgets.Image(
        value=netwgraph_legend2, format="png", width=WIDTH / 2, height=HEIGHT / 2
    )

    # Create all the buttons
    (
        globaltap_button_aut,
        globaldiffs_button_case,
        button_download_data,
    ) = create_buttons()

    # Get all the containers
    (
        globaldiffs_container,
        contgcasediffs_container,
        netwgraph_container,
        globaltap_container_aut,
        contgcasetap_container_aut,
        globaltap_container_aut_trace,
        contgcasediffs_individualtracecontainer,
        netwgraph_legendcontainer,
    ) = create_containers(
        globaldiffs_dropdownvarx,
        globaldiffs_dropdownvary,
        contgcasediffs_dropdowndev,
        contgcasediffs_dropdownx,
        contgcasediffs_dropdowny,
        contgcasediffs_elementdropdown,
        contgcasediffs_vardropdown,
        netwgraph_graph,
        netwgraph_nodetype_drop,
        netwgraph_nodemetrictype_drop,
        netwgraph_edgetype_drop,
        netwgraph_edgemetrictype_drop,
        contgcasetap_aut_diff_case,
        contgcasetap_aut_diff_var_A,
        contgcasetap_aut_diff_var_B,
        globaltap_checka,
        globaltap_checkb,
        contgcasetap_checka,
        contgcasetap_checkb,
        globaltap_aut_diff_var_plot,
        contgcasediffs_individualtrace,
        contgcasediffs_legendwidget,
        netwgraph_legend1widget,
        netwgraph_legend2widget,
    )

    # Display all the objects and get html subgraph id
    netwgraph_html_graph = show_displays(
        globaltap_aut_diffs_A_grid,
        globaltap_aut_diffs_B_grid,
        globaltap_container_aut,
        contgcasetap_container_aut,
        globaltap_container_aut_trace,
        contgcasetap_aut_diff_dfA_grid,
        contgcasetap_aut_diff_dfB_grid,
        globaltap_trace,
        contgcasetap_groups_traceA,
        contgcasetap_groups_traceB,
        globaldiffs_def_volt_level,
        globaldiffs_diff_metric_type,
        globaldiffs_dfgrid,
        globaldiffs_container,
        globaldiffs_generaltrace,
        contgcasediffs_container,
        contgcasediffs_individualtracecontainer,
        contgcasediffs_individualgrid,
        netwgraph_container,
        netwgraph_C,
        netwgraph_legendcontainer,
        globaltap_button_aut,
        globaldiffs_button_case,
        button_download_data,
        compscore_grid_score,
        compscore_max_n_pass,
        compscore_p95_n_pass,
        compscore_mean_n_pass,
        compscore_total_n_pass,
        DATA_LIMIT,
    )

    # Observe selection events to update graphics
    globaldiffs_def_volt_level.observe(globaldiffs_response, names="value")
    globaldiffs_diff_metric_type.observe(globaldiffs_response, names="value")
    globaldiffs_dropdownvarx.observe(globaldiffs_response, names="value")
    globaldiffs_dropdownvary.observe(globaldiffs_response, names="value")

    globaldiffs_scatter = globaldiffs_generaltrace.data[0]
    globaldiffs_scatter.on_click(contgcasediffs_update_case)

    contgcasediffs_dropdowndev.observe(contgcasediffs_response, names="value")
    contgcasediffs_dropdownx.observe(contgcasediffs_response, names="value")
    contgcasediffs_dropdowny.observe(contgcasediffs_response, names="value")
    contgcasediffs_elementdropdown.observe(contgcasediffs_response, names="value")
    contgcasediffs_vardropdown.observe(contgcasediffs_response, names="value")

    netwgraph_graph.observe(netwgraph_response, names="value")
    netwgraph_nodetype_drop.observe(netwgraph_response, names="value")
    netwgraph_nodemetrictype_drop.observe(netwgraph_response, names="value")
    netwgraph_edgetype_drop.observe(netwgraph_response, names="value")
    netwgraph_edgemetrictype_drop.observe(netwgraph_response, names="value")

    contgcasetap_aut_diff_var_A.observe(contgcasetap_response_autA, names="value")
    contgcasetap_aut_diff_var_B.observe(contgcasetap_response_autB, names="value")
    contgcasetap_aut_diff_case.observe(contgcasetap_response_aut, names="value")

    globaldiffs_button_case.observe(contgcasediffs_response_button, "value")
    globaltap_button_aut.observe(contgcasetap_response_aut_button, "value")
    button_download_data.observe(response_download_data, "value")

    globaltap_aut_diff_var_plot.observe(globaltap_response_aut_plot, names="value")
    globaltap_checka.observe(globaltap_response_general_aut_A, names="value")
    globaltap_checkb.observe(globaltap_response_general_aut_B, names="value")
    contgcasetap_checka.observe(contgcasetap_response_autA, names="value")
    contgcasetap_checkb.observe(contgcasetap_response_autB, names="value")
