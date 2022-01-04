import pandas as pd
import plotly.graph_objects as go
from dynawo_validation.dynaflow.notebooks import create_graph
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
def get_initial_graph(xiidm_file, value, t, c):
    return create_graph.get_graph(xiidm_file, value, t, c)


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
    file_name = PF_SOL_DIR + "/pf_sol/" + PREFIX + "_" + name + "-pfsolution_AB.csv.xz"
    data = pd.read_csv(file_name, sep=";", index_col=False, compression="infer")
    data["DIFF"] = data.VALUE_A - data.VALUE_B
    data = calculate_error(data)
    return data


def read_aut_group(name, PF_SOL_DIR, DWO_DWO, PREFIX):
    if DWO_DWO == 0:
        file_name = PF_SOL_DIR + "/aut/" + PREFIX + "_" + name + "-aut-groups.csv"
        data = pd.read_csv(file_name, sep=";")
        return data, None
    else:
        file_name = PF_SOL_DIR + "/aut/" + PREFIX + "_" + name + "-autA-groups.csv"
        data1 = pd.read_csv(file_name, sep=";")
        file_name = PF_SOL_DIR + "/aut/" + PREFIX + "_" + name + "-autB-groups.csv"
        data2 = pd.read_csv(file_name, sep=";")
        return data1, data2


# Create the general graphic of simulator A vs B
def create_general_trace(data, x, y, DATA_LIMIT):
    if data.shape[0] > DATA_LIMIT:
        data = data.sample(DATA_LIMIT)
    trace = go.Scatter(
        x=data[x],
        y=data[y],
        mode="markers",
        text=data["contg_case"] + "_(" + data["volt_level"] + ")",
        name=x + "_" + y,
    )
    return trace


# Calculate global contingencies score
def calc_global_score(df, W_V, W_P, W_Q, W_T, MAX_THRESH, MEAN_THRESH, P95_THRESH):
    df_all = df.loc[(df.volt_level == "ALL")]
    name_score = list(df_all["contg_case"])
    score_max = []
    score_mean = []
    score_p95 = []
    max_n_pass = 0
    mean_n_pass = 0
    p95_n_pass = 0
    total_n_pass = len(df_all.index)

    for i in range(len(df_all.index)):
        max_val = (
            abs(df_all.iloc[i, 3]) * W_P
            + abs((df_all.iloc[i, 4] * 0.5 + df_all.iloc[i, 5] * 0.5)) * W_P
            + abs(df_all.iloc[i, 6]) * W_T
            + abs(df_all.iloc[i, 7]) * W_Q
            + abs((df_all.iloc[i, 8] * 0.5 + df_all.iloc[i, 9] * 0.5)) * W_Q
            + abs(df_all.iloc[i, 10]) * W_T
            + abs(df_all.iloc[i, 11]) * W_V
        )
        if max_val > MAX_THRESH:
            max_n_pass += 1

        score_max.append(max_val)

        p95_val = (
            abs(df_all.iloc[i, 13]) * W_P
            + abs((df_all.iloc[i, 14] * 0.5 + df_all.iloc[i, 15] * 0.5)) * W_P
            + abs(df_all.iloc[i, 16]) * W_T
            + abs(df_all.iloc[i, 17]) * W_Q
            + abs((df_all.iloc[i, 18] * 0.5 + df_all.iloc[i, 19] * 0.5)) * W_Q
            + abs(df_all.iloc[i, 20]) * W_T
            + abs(df_all.iloc[i, 21]) * W_V
        )
        if p95_val > P95_THRESH:
            p95_n_pass += 1
        score_p95.append(p95_val)

        mean_val = (
            abs(df_all.iloc[i, 23]) * W_P
            + abs((df_all.iloc[i, 24] * 0.5 + df_all.iloc[i, 25] * 0.5)) * W_P
            + abs(df_all.iloc[i, 26]) * W_T
            + abs(df_all.iloc[i, 27]) * W_Q
            + abs((df_all.iloc[i, 28] * 0.5 + df_all.iloc[i, 29] * 0.5)) * W_Q
            + abs(df_all.iloc[i, 30]) * W_T
            + abs(df_all.iloc[i, 31]) * W_V
        )
        if mean_val > MEAN_THRESH:
            mean_n_pass += 1
        score_mean.append(mean_val)

    dict_score = {
        "CONTG": name_score,
        "MAX_SCORE": score_max,
        "P95_SCORE": score_p95,
        "MEAN_SCORE": score_mean,
    }
    df_score = pd.DataFrame(dict_score)
    df_score = df_score.sort_values("MAX_SCORE", axis=0, ascending=False)

    return df_score, max_n_pass, p95_n_pass, mean_n_pass, total_n_pass


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
    legend0 = pl.imread("legend0.png")[40:170, 300:385, :]
    addwhite0 = np.zeros((100, legend0.shape[1], legend0.shape[2]))
    addwhite1 = np.zeros((300, legend0.shape[1], legend0.shape[2]))
    legend0 = np.concatenate((addwhite0, legend0, addwhite1), axis=0)
    pl.imsave("legend0.png", legend0)
    return colordata


# Create the individual graphic of simulator A vs B
def create_individual_trace(data, x, y, DATA_LIMIT):
    if data.shape[0] > DATA_LIMIT:
        data = data.sample(DATA_LIMIT)
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


def create_aut_group_trace(data1, data2, DATA_LIMIT):
    if data1.shape[0] > DATA_LIMIT:
        data1 = data1.sample(DATA_LIMIT)

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
        if data2.shape[0] > DATA_LIMIT:
            data2 = data2.sample(DATA_LIMIT)
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
                + "_"
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
                    + "_"
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
                    + "_"
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
                + "_"
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
                    + "_"
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
                    + "_"
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
    contg_case0,
    data_first_case,
    vars_case,
    bus_list,
    nodetypes,
    nodemetrictypes,
    edgetypes,
    edgemetrictypes,
    aut_diffs_A,
    aut_diffs_B,
):
    def_volt_level = widgets.Dropdown(
        options=["DEFAULT"] + list(df["volt_level"].unique()),
        value="DEFAULT",
        description="VOLTAGE LEVEL",
    )

    varx = widgets.Dropdown(
        options=df.columns[1:], value=df.columns[1], description="X: "
    )

    vary = widgets.Dropdown(
        options=df.columns[1:], value=df.columns[2], description="Y: "
    )

    dev = widgets.Dropdown(
        options=sorted(contg_cases), value=contg_case0, description="Contg. case: "
    )

    dropdown1 = widgets.Dropdown(
        options=vars_case, value=vars_case[3], description="X: "
    )

    dropdown2 = widgets.Dropdown(
        options=vars_case, value=vars_case[4], description="Y: "
    )

    dropdown3 = widgets.Dropdown(
        options=["ALL"] + list(set(data_first_case["ELEMENT_TYPE"])),
        value="ALL",
        description="Element Type: ",
    )

    dropdown4 = widgets.Dropdown(
        options=["ALL"] + list(set(data_first_case["VAR"])),
        value="ALL",
        description="Var: ",
    )

    graph = widgets.Dropdown(
        options=bus_list, value=bus_list[0], description="Node ID: "
    )

    nodetype = widgets.Dropdown(
        options=nodetypes, value=nodetypes[0], description="Node var: "
    )

    nodemetrictype = widgets.Dropdown(
        options=nodemetrictypes,
        value=nodemetrictypes[0],
        description="Node metric var: ",
    )

    edgetype = widgets.Dropdown(
        options=edgetypes, value=edgetypes[0], description="Edge var: "
    )

    edgemetrictype = widgets.Dropdown(
        options=edgemetrictypes,
        value=edgemetrictypes[0],
        description="Edge metric var: ",
    )
    aut_diff_case = widgets.Dropdown(
        options=sorted(contg_cases), value=contg_case0, description="Contg. case: "
    )

    a_var = list(aut_diffs_A.index)
    for i in range(len(a_var)):
        a_var[i] = a_var[i].split("-")[-1]
    a_var = list(set(a_var))

    b_var = list(aut_diffs_B.index)
    for i in range(len(b_var)):
        b_var[i] = b_var[i].split("-")[-1]
    b_var = list(set(b_var))

    aut_diff_var_A = widgets.Dropdown(
        options=sorted(a_var), value=a_var[0], description="Aut. var A: "
    )

    aut_diff_var_B = widgets.Dropdown(
        options=sorted(b_var), value=b_var[0], description="Aut. var B: "
    )

    aut_diff_var_plot = widgets.Dropdown(
        options=["ratioTapChanger", "phaseTapChanger"],
        value="ratioTapChanger",
        description="Aut. var: ",
    )

    diff_metric_type = widgets.Dropdown(
        options=["max", "p95", "mean", "ALL"],
        value="max",
        description="Metric type: ",
    )

    return (
        def_volt_level,
        varx,
        vary,
        dev,
        dropdown1,
        dropdown2,
        dropdown3,
        dropdown4,
        graph,
        nodetype,
        nodemetrictype,
        edgetype,
        edgemetrictype,
        aut_diff_case,
        aut_diff_var_A,
        aut_diff_var_B,
        aut_diff_var_plot,
        diff_metric_type,
    )


# Create all the containers of the output
def create_containers(
    varx,
    vary,
    dev,
    dropdown1,
    dropdown2,
    dropdown3,
    dropdown4,
    graph,
    nodetype,
    nodemetrictype,
    edgetype,
    edgemetrictype,
    aut_diff_case,
    aut_diff_var_A,
    aut_diff_var_B,
    check1a,
    check1b,
    check2a,
    check2b,
    aut_trace,
):
    container1 = widgets.HBox([varx, vary])

    container2 = widgets.HBox([dev, dropdown1, dropdown2, dropdown3, dropdown4])

    container3 = widgets.HBox(
        [graph, nodetype, nodemetrictype, edgetype, edgemetrictype]
    )

    container_aut_gen = widgets.HBox([check1a, check1b])
    container_aut = widgets.HBox(
        [aut_diff_case, aut_diff_var_A, check2a, aut_diff_var_B, check2b]
    )
    container_aut_trace = widgets.HBox([aut_trace])
    return (
        container1,
        container2,
        container3,
        container_aut_gen,
        container_aut,
        container_aut_trace,
    )


def create_check_box():
    check1a = widgets.Checkbox(
        value=True,
        description="Only cntgs with changes in sim A",
        disabled=False,
        indent=False,
    )
    check1b = widgets.Checkbox(
        value=True,
        description="Only cntgs with changes in sim B",
        disabled=False,
        indent=False,
    )
    check2a = widgets.Checkbox(
        value=False,
        description="Only devices with changes in sim A",
        disabled=False,
        indent=False,
    )
    check2b = widgets.Checkbox(
        value=False,
        description="Only devices with changes in sim B",
        disabled=False,
        indent=False,
    )
    return check1a, check1b, check2a, check2b


def create_tap_trace(df, HEIGHT, WIDTH):
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
        title=dict(text="FINAL COMPARISON OF AUT STATES - A vs B"),
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
def create_layouts(varx, vary, HEIGHT, WIDTH, contg_case0, dropdown1, dropdown2):
    layout1 = go.Layout(
        title=dict(text="Global differences between simulator A and simulator B"),
        xaxis=dict(title=varx.value),
        yaxis=dict(title=vary.value),
        height=HEIGHT,
        width=WIDTH,
    )

    layout2 = go.Layout(
        title=dict(text="Case: " + contg_case0),
        xaxis=dict(title=dropdown1.value),
        yaxis=dict(title=dropdown2.value),
        height=HEIGHT,
        width=WIDTH,
    )

    layout3 = go.Layout(
        title=dict(text="Case: " + contg_case0),
        xaxis=dict(title="TIME", range=[0, 200]),
        yaxis=dict(title="EVENT"),
        height=HEIGHT,
        width=WIDTH / 2,
    )

    return layout1, layout2, layout3


# Paint the node colors of the graph
def paint_graph(C, data, nodetype, nodemetrictype, edgetype, edgemetrictype):
    # Node color
    data1 = data.loc[(data.VAR == nodetype) & (data.ELEMENT_TYPE == "bus")]
    data1_max = data1[nodemetrictype].max()
    data1_min = data1[nodemetrictype].min()

    data1_max -= data1_min
    for node in C.nodes:
        if len(list(data1.loc[(data1.ID == node["id"])][nodemetrictype])) != 0:
            plasma = cm.get_cmap("plasma", 12)
            c = list(data1.loc[(data1.ID == node["id"])][nodemetrictype])[0] - data1_min
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
    data2 = data.loc[(data.VAR == edgetype) & (data.ELEMENT_TYPE != "bus")]
    data2_max = data2[edgemetrictype].max()
    data2_min = data2[edgemetrictype].min()

    data2_max -= data2_min
    for edge in C.edges:
        if len(list(data2.loc[(data2.ID == edge["id"])][edgemetrictype])) != 0:
            viridis = cm.get_cmap("viridis", 12)
            c = list(data2.loc[(data2.ID == edge["id"])][edgemetrictype])[0] - data2_min
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
                    if len(list(data2.loc[(data2.ID == edge_sp)][edgemetrictype])) != 0:
                        if abs(max_edge) < abs(
                            list(data2.loc[(data2.ID == edge_sp)][edgemetrictype])[0]
                        ):
                            max_edge = list(
                                data2.loc[(data2.ID == edge_sp)][edgemetrictype]
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
    aut_diffs_A,
    aut_diffs_B,
    container_aut_gen,
    container_aut,
    container_aut_trace,
    aut_diff_dfA_contgcase_grid,
    aut_diff_dfB_contgcase_grid,
    t_r,
    groups_traceA,
    groups_traceB,
    def_volt_level,
    diff_metric_type,
    sdf,
    container1,
    g,
    container2,
    container0,
    s,
    container3,
    C,
    dev,
    container4,
    button_aut,
    button_case,
    button_download_data,
    grid_score,
    max_n_pass,
    p95_n_pass,
    mean_n_pass,
    total_n_pass,
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
    display(Markdown("# CONTINGENCIES SCORE"))
    text_score = widgets.Output()
    text_score.append_stdout(
        "Number of cases that have exceeded the max threshold: "
        + str((max_n_pass / total_n_pass) * 100)
        + "% ("
        + str(max_n_pass)
        + ")"
        + "\nNumber of cases that have exceeded the p95 threshold: "
        + str((p95_n_pass / total_n_pass) * 100)
        + "% ("
        + str(p95_n_pass)
        + ")"
        + "\nNumber of cases that have exceeded the mean threshold: "
        + str((mean_n_pass / total_n_pass) * 100)
        + "% ("
        + str(mean_n_pass)
        + ")"
    )
    containerscore = widgets.HBox(
        [
            grid_score,
            text_score,
        ]
    )
    display(containerscore)
    aut_diffs = AppLayout(
        left_sidebar=aut_diffs_A, right_sidebar=aut_diffs_B, align_items="center"
    )
    display(
        Markdown("# GLOBAL AGGREGATE EVENTS W.R.T. BASECASE (CONTINGENCIES SEVERITY)")
    )
    display(container_aut_gen)
    display(aut_diffs)
    display(button_aut)
    aut_diffs_contgcase = AppLayout(
        left_sidebar=aut_diff_dfA_contgcase_grid,
        right_sidebar=aut_diff_dfB_contgcase_grid,
        align_items="center",
    )
    display(Markdown("# EVENT DETAILS"))
    display(container_aut)
    display(aut_diffs_contgcase)
    display(container_aut_trace)
    if groups_traceB is not None:
        containergroup = widgets.HBox([groups_traceA, groups_traceB])
    else:
        containergroup = widgets.HBox([groups_traceA])
    display(t_r)
    display(containergroup)
    container_general = widgets.HBox(
        [
            def_volt_level,
            diff_metric_type,
        ]
    )
    display(container_general)
    display(sdf)
    display(button_case)
    display(container1)
    display(g)
    display(container2)
    display(container0)
    display(s)
    display(button_download_data)
    display(container3)
    html_graph = display(C.show("subgraph.html"), display_id=True)
    print("Node Legend - Edge Legend")
    display(container4)
    print(
        "If a node/edge is white it means that the selected metric is not available",
        "for that node/edge.",
    )
    return html_graph


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
    def response(change):
        if diff_metric_type.value == "max":
            df2 = df[
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
        elif diff_metric_type.value == "p95":
            df2 = df[
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
        elif diff_metric_type.value == "mean":
            df2 = df[
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
            df2 = df

        if def_volt_level.value == "DEFAULT":
            df1 = df
        else:
            df1 = df.loc[(df.volt_level == def_volt_level.value)]

        # PERF: Plotly starts showing horrible performance with more than 5,000 points
        if df1.shape[0] > DATA_LIMIT:
            df1 = df1.sample(DATA_LIMIT)
        with g.batch_update():
            sdf.data = df2
            g.data[0].x = df1[varx.value]
            g.data[0].y = df1[vary.value]
            g.data[0].name = varx.value + "_" + vary.value
            g.data[0].text = df1["contg_case"] + "_(" + df1["volt_level"] + ")"
            g.layout.xaxis.title = varx.value
            g.layout.yaxis.title = vary.value

    def individual_case(case):
        if len(sdf.selections) != 0:
            case = sdf.data.loc[sdf.selections[0]["r1"], "contg_case"]
            sdf.clear_selection()

        df1 = read_case(case, PF_SOL_DIR, PREFIX)
        # PERF: Plotly starts showing horrible performance with more than 5,000 points
        with c.batch_update():
            if dropdown3.value != "ALL" and dropdown4.value != "ALL":
                df1 = df1.loc[
                    (df1.ELEMENT_TYPE == dropdown3.value) & (df1.VAR == dropdown4.value)
                ]
            else:
                if dropdown3.value != "ALL" and dropdown4.value == "ALL":
                    df1 = df1.loc[(df1.ELEMENT_TYPE == dropdown3.value)]
                else:
                    if dropdown3.value == "ALL" and dropdown4.value != "ALL":
                        df1 = df1.loc[(df1.VAR == dropdown4.value)]
            if df1.shape[0] > DATA_LIMIT:
                df1 = df1.sample(DATA_LIMIT)
            s.data = df1.sort_values("ID")
            c.data[0].x = df1[dropdown1.value]
            c.data[0].y = df1[dropdown2.value]
            c.data[0].name = dropdown1.value + "_" + dropdown2.value
            c.data[0].text = df1["ID"]
            colordata = create_colors(df1)
            c.data[0].marker = dict(color=colordata)
            c.layout.xaxis.title = dropdown1.value
            c.layout.yaxis.title = dropdown2.value
            c.layout.title.text = "Case: " + case
            dev.value = case

    def individual_aut_group(case):
        df1, df2 = read_aut_group(case, PF_SOL_DIR, DWO_DWO, PREFIX)
        # PERF: Plotly starts showing horrible performance with more than 5,000 points
        with groups_traceA.batch_update():
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
            groups_traceA.data[0].x = df1["TIME"]
            groups_traceA.data[0].y = df1["DEVICE"]
            groups_traceA.data[0].text = df1["EVENT_MESSAGE"]
            groups_traceA.data[0].marker = dict(color=color)
            groups_traceA.layout.xaxis.range = [0, 200]
            groups_traceA.layout.title.text = "Case: " + case
        if df2 is not None:
            with groups_traceB.batch_update():
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
                groups_traceB.data[0].x = df2["TIME"]
                groups_traceB.data[0].y = df2["DEVICE"]
                groups_traceB.data[0].text = df2["EVENT_MESSAGE"]
                groups_traceB.data[0].marker = dict(color=color)
                groups_traceB.layout.xaxis.range = [0, 200]
                groups_traceB.layout.title.text = "Case: " + case

    def update_case(trace, points, selector):
        name = trace.text[points.point_inds[0]].split("_(")
        individual_case(name[0])

    def response2(change):
        individual_case(dev.value)

    def response_autA(change):
        with c.batch_update():
            aut_diff_dfA_contgcase = create_aut_df(
                RESULTS_DIR,
                1,
                aut_diff_case.value,
                PREFIX,
                BASECASE,
                DWO_DWO,
                aut_diff_var_A.value,
            )

            if check2a.value:
                aut_diff_dfA_contgcase = aut_diff_dfA_contgcase.loc[
                    (aut_diff_dfA_contgcase.HAS_CHANGED != 0)
                ]
                aut_diff_dfA_contgcase = aut_diff_dfA_contgcase.drop(
                    columns=["HAS_CHANGED"]
                )

            aut_diff_dfA_contgcase_grid.data = aut_diff_dfA_contgcase
            aut_diff_dfA_contgcase_grid.base_column_size = int(
                (WIDTH / 2 / 1.1) / len(aut_diff_dfA_contgcase.columns)
            )

    def response_autB(change):
        with c.batch_update():
            aut_diff_dfB_contgcase = create_aut_df(
                RESULTS_DIR,
                2,
                aut_diff_case.value,
                PREFIX,
                BASECASE,
                DWO_DWO,
                aut_diff_var_B.value,
            )

            if check2b.value:
                aut_diff_dfB_contgcase = aut_diff_dfB_contgcase.loc[
                    (aut_diff_dfB_contgcase.HAS_CHANGED != 0)
                ]
                aut_diff_dfB_contgcase = aut_diff_dfB_contgcase.drop(
                    columns=["HAS_CHANGED"]
                )

            aut_diff_dfB_contgcase_grid.data = aut_diff_dfB_contgcase
            aut_diff_dfB_contgcase_grid.base_column_size = int(
                (WIDTH / 2 / 1.1) / len(aut_diff_dfB_contgcase.columns)
            )

    def response_aut(change):
        with c.batch_update():
            if len(aut_diffs_A_grid.selections) != 0:
                aut_diff_case.value = aut_diffs_A_grid.data.iloc[
                    aut_diffs_A_grid.selections[0]["r1"], 4
                ][len(PREFIX) + 1 :]
                aut_diffs_A_grid.clear_selection()
                aut_diffs_B_grid.clear_selection()

            elif len(aut_diffs_B_grid.selections) != 0:
                aut_diff_case.value = aut_diffs_B_grid.data.iloc[
                    aut_diffs_B_grid.selections[0]["r1"], 4
                ][len(PREFIX) + 1 :]
                aut_diffs_A_grid.clear_selection()
                aut_diffs_B_grid.clear_selection()

            aut_diff_dfA_contgcase = create_aut_df(
                RESULTS_DIR,
                1,
                aut_diff_case.value,
                PREFIX,
                BASECASE,
                DWO_DWO,
                aut_diff_var_A.value,
            )
            aut_diff_dfB_contgcase = create_aut_df(
                RESULTS_DIR,
                2,
                aut_diff_case.value,
                PREFIX,
                BASECASE,
                DWO_DWO,
                aut_diff_var_B.value,
            )

            if check2a.value:
                aut_diff_dfA_contgcase = aut_diff_dfA_contgcase.loc[
                    (aut_diff_dfA_contgcase.HAS_CHANGED != 0)
                ]
                aut_diff_dfA_contgcase = aut_diff_dfA_contgcase.drop(
                    columns=["HAS_CHANGED"]
                )

            if check2b.value:
                aut_diff_dfB_contgcase = aut_diff_dfB_contgcase.loc[
                    (aut_diff_dfB_contgcase.HAS_CHANGED != 0)
                ]
                aut_diff_dfB_contgcase = aut_diff_dfB_contgcase.drop(
                    columns=["HAS_CHANGED"]
                )

            aut_diff_dfA_contgcase_grid.data = aut_diff_dfA_contgcase
            aut_diff_dfA_contgcase_grid.base_column_size = int(
                (WIDTH / 2 / 1.1) / len(aut_diff_dfA_contgcase.columns)
            )
            aut_diff_dfB_contgcase_grid.data = aut_diff_dfB_contgcase
            aut_diff_dfB_contgcase_grid.base_column_size = int(
                (WIDTH / 2 / 1.1) / len(aut_diff_dfB_contgcase.columns)
            )
            individual_aut_group(aut_diff_case.value)

    def response_download_data(change):
        temp_dict = {
            "text": list(t_r.data[0].text),
            "x": list(t_r.data[0].x),
            "y": list(t_r.data[0].y),
        }
        pd.DataFrame(temp_dict).to_csv("comparison_aut_states.csv", sep=";")
        temp_dict = {
            "text": list(c.data[0].text),
            "x": list(c.data[0].x),
            "y": list(c.data[0].y),
        }
        pd.DataFrame(temp_dict).to_csv("indv_case_diffs.csv", sep=";")
        temp_dict = {
            "text": list(g.data[0].text),
            "x": list(g.data[0].x),
            "y": list(g.data[0].y),
        }
        pd.DataFrame(temp_dict).to_csv("global_case_diffs.csv", sep=";")

    def response_general_aut_A(change):
        aut_diffs_A, aut_diffs_B = read_csv_aut_diffs(
            RESULTS_DIR + "/" + PREFIX + "/aut/"
        )
        if check1a.value:
            aut_diffs_A = aut_diffs_A.loc[(aut_diffs_A.NUM_CHANGES != 0)]
        aut_diffs_A_grid.data = aut_diffs_A
        aut_diffs_A_grid.base_column_size = int(
            (WIDTH / 2 / 1.1) / len(aut_diffs_A.columns)
        )

    def response_general_aut_B(change):
        aut_diffs_A, aut_diffs_B = read_csv_aut_diffs(
            RESULTS_DIR + "/" + PREFIX + "/aut/"
        )
        if check1b.value:
            aut_diffs_B = aut_diffs_B.loc[(aut_diffs_B.NUM_CHANGES != 0)]
        aut_diffs_B_grid.data = aut_diffs_B
        aut_diffs_B_grid.base_column_size = int(
            (WIDTH / 2 / 1.1) / len(aut_diffs_B.columns)
        )

    def response_aut_plot(change):
        df_aut = read_aut_case(
            RESULTS_DIR + "/" + PREFIX + "/aut/", aut_diff_var_plot.value
        )
        with t_r.batch_update():
            temp_sim_A = min(df_aut["sim_A"], default=None)
            temp_sim_B = min(df_aut["sim_B"], default=None)
            if temp_sim_A is None and temp_sim_B is None:
                min_val = 0
            else:
                min_val = min([temp_sim_A, temp_sim_B]) - 1

            temp_sim_A = max(df_aut["sim_A"], default=None)
            temp_sim_B = max(df_aut["sim_B"], default=None)
            if temp_sim_A is None and temp_sim_B is None:
                max_val = 1
            else:
                max_val = max([temp_sim_A, temp_sim_B]) + 1

            t_r.data[0].x = df_aut["sim_A"]
            t_r.data[0].y = df_aut["sim_B"]
            t_r.data[0].text = list(df_aut.index)
            t_r.layout.xaxis = dict(
                title="SIM_A",
                range=[min_val, max_val],
                tickmode="linear",
            )
            t_r.layout.yaxis = dict(
                title="SIM_B",
                range=[min_val, max_val],
                tickmode="linear",
            )

            t_r.data[1].x = [min_val, max_val]
            t_r.data[1].y = [min_val, max_val]

    def response3(change):
        with c.batch_update():
            C = create_graph.get_subgraph(G, graph.value, SUBGRAPH_TYPE, SUBGRAPH_VALUE)
            C = paint_graph(
                C,
                data_first_case,
                nodetype.value,
                nodemetrictype.value,
                edgetype.value,
                edgemetrictype.value,
            )
            html_graph.update(C.show("subgraph.html"))
            file1 = open("legend1.png", "rb")
            legend1 = file1.read()
            file2 = open("legend2.png", "rb")
            legend2 = file2.read()
            legend1widget.value = legend1
            legend2widget.value = legend2

    nodetypes = ["v", "angle", "p", "q"]
    nodemetrictypes = ["DIFF", "ABS_ERR", "REL_ERR", "VALUE_A", "VALUE_B"]
    edgetypes = ["p1", "p2", "q1", "q2"]
    edgemetrictypes = ["DIFF", "ABS_ERR", "REL_ERR", "VALUE_A", "VALUE_B"]

    do_displaybutton()

    df = read_csv_metrics(PF_SOL_DIR)

    aut_diffs_A, aut_diffs_B = read_csv_aut_diffs(RESULTS_DIR + "/" + PREFIX + "/aut/")

    check1a, check1b, check2a, check2b = create_check_box()

    # Get list of contingency cases
    contg_cases = list(df["contg_case"].unique())
    contg_case0 = contg_cases[0]

    # Read the first contingency to put default data
    data_first_case = read_case(contg_case0, PF_SOL_DIR, PREFIX)

    aut_group_data_first_caseA, aut_group_data_first_caseB = read_aut_group(
        contg_case0, PF_SOL_DIR, DWO_DWO, PREFIX
    )

    vars_case = data_first_case.columns[1:]

    # Get the bus list for subgraph selection
    bus_list = sorted(
        list(set(data_first_case.loc[(data_first_case.ELEMENT_TYPE == "bus")]["ID"]))
    )

    df_aut = read_aut_case(RESULTS_DIR + "/" + PREFIX + "/aut/", "ratioTapChanger")
    t_r = create_tap_trace(df_aut, HEIGHT, WIDTH)

    # Get all the dropdowns
    (
        def_volt_level,
        varx,
        vary,
        dev,
        dropdown1,
        dropdown2,
        dropdown3,
        dropdown4,
        graph,
        nodetype,
        nodemetrictype,
        edgetype,
        edgemetrictype,
        aut_diff_case,
        aut_diff_var_A,
        aut_diff_var_B,
        aut_diff_var_plot,
        diff_metric_type,
    ) = create_dropdowns(
        df,
        contg_cases,
        contg_case0,
        data_first_case,
        vars_case,
        bus_list,
        nodetypes,
        nodemetrictypes,
        edgetypes,
        edgemetrictypes,
        aut_diffs_A,
        aut_diffs_B,
    )

    # Get all the containers
    (
        container1,
        container2,
        container3,
        container_aut_gen,
        container_aut,
        container_aut_trace,
    ) = create_containers(
        varx,
        vary,
        dev,
        dropdown1,
        dropdown2,
        dropdown3,
        dropdown4,
        graph,
        nodetype,
        nodemetrictype,
        edgetype,
        edgemetrictype,
        aut_diff_case,
        aut_diff_var_A,
        aut_diff_var_B,
        check1a,
        check1b,
        check2a,
        check2b,
        aut_diff_var_plot,
    )

    # Get all the layouts
    layout1, layout2, layout3 = create_layouts(
        varx, vary, HEIGHT, WIDTH, contg_case0, dropdown1, dropdown2
    )

    current_general_trace = create_general_trace(df, varx.value, vary.value, DATA_LIMIT)

    df_score, max_n_pass, p95_n_pass, mean_n_pass, total_n_pass = calc_global_score(
        df, W_V, W_P, W_Q, W_T, MAX_THRESH, MEAN_THRESH, P95_THRESH
    )

    renderers = {
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

    grid_score = ipydatagrid.DataGrid(
        df_score,
        base_column_size=int((WIDTH / 2 / 1.1) / len(df_score.columns)),
        renderers=renderers,
    )

    current_individual_trace = create_individual_trace(
        data_first_case, dropdown1.value, dropdown2.value, DATA_LIMIT
    )

    current_aut_group_traceA, current_aut_group_traceB = create_aut_group_trace(
        aut_group_data_first_caseA, aut_group_data_first_caseB, DATA_LIMIT
    )

    aut_diff_dfA_contgcase = create_aut_df(
        RESULTS_DIR,
        1,
        aut_diff_case.value,
        PREFIX,
        BASECASE,
        DWO_DWO,
        aut_diff_var_A.value,
    )

    aut_diff_dfB_contgcase = create_aut_df(
        RESULTS_DIR,
        2,
        aut_diff_case.value,
        PREFIX,
        BASECASE,
        DWO_DWO,
        aut_diff_var_B.value,
    )

    if check2a.value:
        aut_diff_dfA_contgcase = aut_diff_dfA_contgcase.loc[
            (aut_diff_dfA_contgcase.HAS_CHANGED != 0)
        ]
        aut_diff_dfA_contgcase = aut_diff_dfA_contgcase.drop(columns=["HAS_CHANGED"])
    aut_diff_dfA_contgcase_grid = ipydatagrid.DataGrid(
        aut_diff_dfA_contgcase,
        base_column_size=int((WIDTH / 2 / 1.1) / len(aut_diff_dfA_contgcase.columns)),
    )

    if check2b.value:
        aut_diff_dfB_contgcase = aut_diff_dfB_contgcase.loc[
            (aut_diff_dfB_contgcase.HAS_CHANGED != 0)
        ]
        aut_diff_dfB_contgcase = aut_diff_dfB_contgcase.drop(columns=["HAS_CHANGED"])
    aut_diff_dfB_contgcase_grid = ipydatagrid.DataGrid(
        aut_diff_dfB_contgcase,
        base_column_size=int((WIDTH / 2 / 1.1) / len(aut_diff_dfB_contgcase.columns)),
    )

    # Create the required widgets for visualization
    if check1a.value:
        aut_diffs_A = aut_diffs_A.loc[(aut_diffs_A.NUM_CHANGES != 0)]
        aut_diffs_A_grid = ipydatagrid.DataGrid(
            aut_diffs_A,
            base_column_size=int((WIDTH / 2 / 1.1) / len(aut_diffs_A.columns)),
            selection_mode="row",
        )

    if check1b.value:
        aut_diffs_B = aut_diffs_B.loc[(aut_diffs_B.NUM_CHANGES != 0)]
        aut_diffs_B_grid = ipydatagrid.DataGrid(
            aut_diffs_B,
            base_column_size=int((WIDTH / 2 / 1.1) / len(aut_diffs_B.columns)),
            selection_mode="row",
        )

    # Matching df
    if diff_metric_type.value == "max":
        df3 = df[
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
    elif diff_metric_type.value == "p95":
        df3 = df[
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
    elif diff_metric_type.value == "mean":
        df3 = df[
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
    sdf = ipydatagrid.DataGrid(
        df3,
        base_column_size=int((WIDTH / 1.03) / len(df3.columns)),
        selection_mode="row",
    )

    g = go.FigureWidget(data=[current_general_trace], layout=layout1)

    c = go.FigureWidget(data=[current_individual_trace], layout=layout2)

    groups_traceA = go.FigureWidget(data=[current_aut_group_traceA], layout=layout3)
    if current_aut_group_traceB is not None:
        groups_traceB = go.FigureWidget(data=[current_aut_group_traceB], layout=layout3)
    else:
        groups_traceB = None

    file0 = open("legend0.png", "rb")
    legend0 = file0.read()
    legend0widget = widgets.Image(value=legend0, format="png")

    container0 = widgets.HBox([c, legend0widget])

    s = ipydatagrid.DataGrid(
        data_first_case,
        base_column_size=int((WIDTH / 1.03) / len(data_first_case.columns)),
    )

    # Get iidm file
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
        xiidm_file = network.get("iidmFile")
        xiidm_file = RESULTS_DIR + BASECASE + "/" + xiidm_file
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
            xiidm_file = network.get("iidmFile")
            xiidm_file = RESULTS_DIR + BASECASE + "/" + xiidm_file
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
                xiidm_file = network.get("iidmFile")
                xiidm_file = RESULTS_DIR + BASECASE + "/" + xiidm_file
            else:
                raise Exception("No valid DWO_DWO option")

    # Get default graph
    G, C = get_initial_graph(xiidm_file, graph.value, SUBGRAPH_TYPE, SUBGRAPH_VALUE)

    C = paint_graph(
        C,
        data_first_case,
        nodetype.value,
        nodemetrictype.value,
        edgetype.value,
        edgemetrictype.value,
    )

    file1 = open("legend1.png", "rb")
    legend1 = file1.read()
    file2 = open("legend2.png", "rb")
    legend2 = file2.read()

    legend1widget = widgets.Image(
        value=legend1, format="png", width=WIDTH / 2, height=HEIGHT / 2
    )

    legend2widget = widgets.Image(
        value=legend2, format="png", width=WIDTH / 2, height=HEIGHT / 2
    )

    container4 = widgets.HBox([legend1widget, legend2widget])

    button_descriptions_aut = {False: "Apply Selection", True: "Apply Selection"}
    button_aut = widgets.ToggleButton(False, description=button_descriptions_aut[False])

    button_descriptions_case = {False: "Apply Selection", True: "Apply Selection"}
    button_case = widgets.ToggleButton(
        False, description=button_descriptions_case[False]
    )

    button_download_data_opts = {False: "Download Data", True: "Download Data"}
    button_download_data = widgets.ToggleButton(
        False, description=button_download_data_opts[False]
    )

    # Display all the objects and get html subgraph id
    html_graph = show_displays(
        aut_diffs_A_grid,
        aut_diffs_B_grid,
        container_aut_gen,
        container_aut,
        container_aut_trace,
        aut_diff_dfA_contgcase_grid,
        aut_diff_dfB_contgcase_grid,
        t_r,
        groups_traceA,
        groups_traceB,
        def_volt_level,
        diff_metric_type,
        sdf,
        container1,
        g,
        container2,
        container0,
        s,
        container3,
        C,
        dev,
        container4,
        button_aut,
        button_case,
        button_download_data,
        grid_score,
        max_n_pass,
        p95_n_pass,
        mean_n_pass,
        total_n_pass,
    )

    # Observe selection events to update graphics
    def_volt_level.observe(response, names="value")
    diff_metric_type.observe(response, names="value")
    varx.observe(response, names="value")
    vary.observe(response, names="value")

    scatter = g.data[0]
    scatter.on_click(update_case)

    dev.observe(response2, names="value")

    dropdown1.observe(response2, names="value")
    dropdown2.observe(response2, names="value")
    dropdown3.observe(response2, names="value")
    dropdown4.observe(response2, names="value")

    graph.observe(response3, names="value")

    nodetype.observe(response3, names="value")
    nodemetrictype.observe(response3, names="value")
    edgetype.observe(response3, names="value")
    edgemetrictype.observe(response3, names="value")

    aut_diff_var_A.observe(response_autA, names="value")
    aut_diff_var_B.observe(response_autB, names="value")
    aut_diff_case.observe(response_aut, names="value")

    button_case.observe(response2, "value")
    button_aut.observe(response_aut, "value")
    button_download_data.observe(response_download_data, "value")

    aut_diff_var_plot.observe(response_aut_plot, names="value")
    check1a.observe(response_general_aut_A, names="value")
    check1b.observe(response_general_aut_B, names="value")
    check2a.observe(response_autA, names="value")
    check2b.observe(response_autB, names="value")
