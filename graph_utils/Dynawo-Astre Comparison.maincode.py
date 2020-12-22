import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import seaborn as sns
import qgrid
from ipywidgets import widgets
from IPython.display import display, HTML
from IPython.display import Markdown as md

T_sta = 870


# Auxiliary function for calculating delta levelK at the auto_tw points
def getDeltaLevelK(df_ast, df_dwo, df_m):
    df_ast = df_ast.merge(df_m)
    cols = df_ast.columns
    colsk = cols.str.contains("_levelK_")
    dak = df_ast[cols[colsk]]
    dks = -dak.sum(axis=1)
    ddk = pd.DataFrame([df_ast["time"], dks]).T

    dwo_ = pd.concat([df_dwo.time, df_dwo[cols[colsk]]], axis=1)
    dwo_ = dwo_.merge(ddk).drop_duplicates("time")

    ts = dwo_.time
    dwo_ = dwo_.drop(["time"], axis=1)

    lks = abs(dwo_.sum(axis=1))

    deltak = pd.concat([ts, lks], axis=1)
    deltak.columns = ["time", "deltaLevelK"]

    return deltak


# Auxiliary function for reading curve data of each individual case
def get_curve_dfs(crv_dir, prefix, contg_case):
    TFIN_TIME_OFFSET = 4000  # Dynawo's time offset w.r.t. Astre
    ast_case = crv_dir + "/" + prefix + contg_case + "-AstreCurves.csv.xz"
    dwo_case = crv_dir + "/" + prefix + contg_case + "-DynawoCurves.csv.xz"
    df_ast = pd.read_csv(ast_case, sep=";", index_col=False, compression="infer")
    df_dwo = pd.read_csv(dwo_case, sep=";", index_col=False, compression="infer")
    df_dwo = df_dwo.iloc[:, :-1]  # because of extra ";" at end-of-lines
    df_dwo["time"] = round(df_dwo.time - TFIN_TIME_OFFSET)

    df_m = auto_tw[auto_tw.contg_case == contg_case].copy()
    df_m.loc[len(df_m)] = [contg_case, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    da = df_ast.copy()
    dd = df_dwo.copy()

    df_lk = getDeltaLevelK(da, dd, df_m)

    return df_ast, df_dwo, df_lk


# Callbacks
def response(change):
    df = delta

    if check.value:
        stable = np.where((df.TT_ast < T_sta) & (df.TT_dwo < T_sta))
        df = df.iloc[stable]
    mask_ = [mask.value in x for x in df.vars]
    df = df[mask_]

    with g.batch_update():
        g.data[0].x = df[var.value + "_ast"]
        g.data[0].y = df[var.value + "_dwo"]
        g.data[6].x = df[var.value + "_ast"]
        g.data[6].y = df[var.value + "_ast"]

        g.data[0].marker.color = df.TT_ast
        g.data[0].marker.size = (
            (df.dPP_ast - min(df.dPP_ast)) / (max(df.dPP_ast) - min(df.dPP_ast)) * 50
        )
        g.data[0].text = df["dev"] + "<br>" + df["vars"]
        g.layout.xaxis.title = var.value + " Astre"
        g.layout.yaxis.title = var.value + " Dynawo"


def response2(change):
    df_ast, df_dwo, _ = get_curve_dfs(CRV_DIR, PREFIX, dev.value)
    vars_ast = df_ast.columns[1:]
    var2.options = vars_ast
    var2.value = vars_ast[0]
    with g.batch_update():
        g.data[1].x = df_ast["time"]
        g.data[1].y = df_ast[var2.value]
        g.data[2].x = df_dwo["time"]
        g.data[2].y = df_dwo[var2.value] - df_dwo[var2.value][0] + df_ast[var2.value][1]
        g.layout.yaxis2.title = var2.value


def response3(change):
    df_ast, df_dwo, df_lk = get_curve_dfs(CRV_DIR, PREFIX, dev.value)
    df_m = auto_tw[auto_tw.contg_case == dev.value].copy()
    df_m.loc[len(df_m)] = [dev.value, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    with g.batch_update():
        g.data[1].y = df_ast[var2.value]
        g.data[2].y = df_dwo[var2.value] - df_dwo[var2.value][0] + df_ast[var2.value][1]
        g.data[3].x = df_m["time"]
        g.data[4].x = df_m["time"]
        g.data[5].x = df_m["time"]
        g.data[6].x = df_lk["time"]
        g.data[3].y = df_m["ldtap_netchanges"]
        g.data[4].y = df_m["tap_netchanges"]
        g.data[5].y = df_m["shunt_netchanges"]
        g.data[6].y = df_lk["deltaLevelK"]
        g.layout.yaxis2.title = var2.value


def update_serie(trace, points, selector):
    # t = list(scatter.text)
    for i in points.point_inds:
        # print(scatter.text[i])
        with g.batch_update():
            dev0 = scatter.text[i].split("<")[0]
            dev1 = scatter.text[i].split(">")[1]
            dev.value = dev0
            var2.value = dev1


def calc_scores_bycasevar(delta):
    # The scores consist in relative change in metrics (keeping the sign).
    # The global one consists in the (weighted) abs-sum of all the others.
    scores = delta[["dev", "vars", "dSS_pass", "dPP_pass"]].copy()
    scores.columns = ["contg_case", "Variable", "dSS_pass", "dPP_pass"]
    scores["global_crv"] = 0
    metrics = ["dSS", "dPP", "TT", "period", "damp"]
    wmetric = [0.6, 0.2, 0.1, 0.05, 0.05]
    for metr in metrics:
        scores[metr] = (delta[metr + "_ast"] - delta[metr + "_dwo"]) / abs(
            delta[[metr + "_ast", metr + "_dwo"]].abs().max(axis=1)
        )
    scores = scores.fillna(0)
    for i, metr in enumerate(metrics):
        scores["global_crv"] += abs(scores[metr]) * wmetric[i]

    scores["pre_ast"] = delta.TT_ast >= 0
    scores["pre_dwo"] = delta.TT_dwo >= 0

    scores["post_ast"] = delta.TT_ast < T_sta
    scores["post_dwo"] = delta.TT_dwo < T_sta

    scores = scores.set_index(["contg_case", "Variable"])
    return scores


def calc_scores_bycase(scores):
    # For each case, we keep the mean scores found accross the monitored variables.
    scores[["dSS", "dPP", "TT", "period", "damp"]] = scores[
        ["dSS", "dPP", "TT", "period", "damp"]
    ].abs()
    scores_mean = scores.groupby(["contg_case"]).mean()
    scores_sum = scores[["dSS_pass", "dPP_pass"]].groupby(["contg_case"]).sum()
    scores_count = scores[["dSS_pass", "dPP_pass"]].groupby(["contg_case"]).count()
    scores_mean["dSS_viol"] = scores_count.dSS_pass - scores_sum.dSS_pass
    scores_mean["dPP_viol"] = scores_count.dPP_pass - scores_sum.dPP_pass
    scores_mean["dSS_pass_"] = scores_mean.dSS_pass > 0.999
    scores_mean["dPP_pass_"] = scores_mean.dPP_pass > 0.999

    scores_mean["Stable_ini"] = np.where(
        ((scores_mean.pre_ast > 0.999) & ((scores_mean.pre_dwo > 0.999))), True, False
    )
    scores_mean["Stable_fin"] = np.where(
        ((scores_mean.post_ast > 0.999) & ((scores_mean.post_dwo > 0.999))), True, False
    )

    scores_mean = scores_mean.merge(auto, on="contg_case")
    alpha = 0.5
    scores_mean["global"] = (
        alpha * scores_mean["global_crv"] + (1 - alpha) * scores_mean["global_aut"]
    )
    return scores_mean


def get_grid_bycase(scores_mean):
    cols = [
        "contg_case",
        "Stable_ini",
        "Stable_fin",
        "dSS_pass_",
        "dSS_viol",
        "dPP_pass_",
        "dPP_viol",
        "global",
        "global_crv",
        "global_aut",
        "dSS",
        "dPP",
        "TT",
        "period",
        "damp",
        "shunt_netchanges",
        "any_shunt_evt",
        "tap_netchanges",
        "any_xfmr_tap",
        "ldtap_netchanges",
        "any_ldxfmr_tap",
    ]
    scores_mean_g = scores_mean[cols].set_index(["contg_case"])
    grid_bycase = qgrid.show_grid(scores_mean_g.sort_values("global", ascending=False))
    return grid_bycase


# Heatmap
def plot_heatmap(scores_mean):
    sns.set(rc={"figure.figsize": (20, 60)})
    cols = [
        "global",
        "global_crv",
        "global_aut",
        "dSS",
        "dPP",
        "TT",
        "period",
        "damp",
        "shunt_netchanges",
        "shunt_numchanges",
        "tap_netchanges",
        "tap_p2pchanges",
        "tap_numchanges",
        "ldtap_netchanges",
        "ldtap_p2pchanges",
        "ldtap_numchanges",
    ]
    scores_mean = scores_mean.set_index(["contg_case"])
    return sns.heatmap(scores_mean[cols].sort_values(["global"], ascending=False))


# For hiding code cells
def toggle_code(state):
    """
    Toggles the JavaScript show()/hide() function on the div.input element.
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


###################################################
# NOTEBOOK MAIN CODE STARTS HERE
###################################################

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

do_displaybutton()

# This is just to stop flake8 complaining
try:
    CRV_DIR
except NameError:
    CRV_DIR = None

try:
    PREFIX
except NameError:
    PREFIX = None

# Read the metrics
metrics_dir = CRV_DIR + "/../metrics"
ast_metrics = metrics_dir + "/curve_metrics_ast.csv"
dwo_metrics = metrics_dir + "/curve_metrics_dwo.csv"
diff_metrics = metrics_dir + "/curve_diffmetrics.csv"
auto_metrics = metrics_dir + "/aut_diffmetrics.csv"
auto_tw_metrics = metrics_dir + "/aut_tw_diffmetrics.csv"

if not (
    os.path.isdir(metrics_dir)
    and os.path.isfile(ast_metrics)
    and os.path.isfile(dwo_metrics)
    and os.path.isfile(diff_metrics)
):
    raise ValueError("Input datafiles (metrics) not found for %s" % CRV_DIR)

all_ast = pd.read_csv(ast_metrics, sep=";", index_col=False, compression="infer")
all_dwo = pd.read_csv(dwo_metrics, sep=";", index_col=False, compression="infer")
delta = pd.read_csv(diff_metrics, sep=";", index_col=False, compression="infer")
delta.fillna(-1, inplace=True)

auto = pd.read_csv(auto_metrics, sep=";", index_col=False, compression="infer")
auto["global_aut"] = auto[auto.columns[1:]].mean(axis=1)
auto_tw = pd.read_csv(auto_tw_metrics, sep=";", index_col=False, compression="infer")

# Calculate pass/fail type of measurements for threshold
delta["typevar"] = ""
delta.loc[delta.vars.str.contains("_U_IMPIN"), "typevar"] = "V"
delta.loc[delta.vars.str.contains("_Upu_"), "typevar"] = "V"
delta.loc[delta.vars.str.contains("_levelK_"), "typevar"] = "K"
delta.loc[delta.vars.str.contains("_PGen"), "typevar"] = "P"
delta.loc[delta.vars.str.contains("_QGen"), "typevar"] = "Q"
d_threshold = {"V": 0.01, "K": 0.1, "P": 5, "Q": 10}
delta["threshold"] = delta.typevar.replace(d_threshold)
delta["delta_dSS"] = delta["dSS_ast"] - delta["dSS_dwo"]
delta["dSS_pass"] = delta.delta_dSS.abs() < delta.threshold
delta["delta_dPP"] = delta["dPP_ast"] - delta["dPP_dwo"]
delta["dPP_pass"] = delta.delta_dPP.abs() < delta.threshold


# Combo Boxes
check = widgets.Checkbox(
    value=False, description="Only Stable contingencies", disabled=False, indent=False
)

mask_n = ["NETWORK" in x for x in all_dwo.vars]
df = delta[mask_n]
var = widgets.Dropdown(
    options=list(["dSS", "dPP", "TT", "period", "damp"]),
    value="dSS",
    description="Metric: ",
)
mask = widgets.Dropdown(
    options=list(["NETWORK", "U_IMPIN", "levelK", "PGen", "QGen"]),
    value="NETWORK",
    description="Var. group: ",
)
contg_cases = list(delta["dev"].unique())
contg_case0 = contg_cases[0]
dev = widgets.Dropdown(
    options=contg_cases, value=contg_case0, description="Contg. case: "
)


# Load the curve data for the first case
df_ast, df_dwo, df_lk = get_curve_dfs(CRV_DIR, PREFIX, contg_case0)
vars_ast = df_ast.columns[1:]
vars_dwo = df_dwo.columns[1:]
var0 = vars_ast[0]
var2 = widgets.Dropdown(options=vars_ast, value=var0, description="Variable: ")
df_m = auto_tw[auto_tw.contg_case == dev.value].copy()
df_m.loc[len(df_m)] = [dev.value, 0, 0, 0, 0, 0, 0, 0, 0, 0]


# Traces
trace = go.Scatter(
    name="Dynawo vs Astre",
    x=df["dSS_ast"],
    y=df["dSS_dwo"],
    mode="markers",
    marker_color=df["TT_ast"],
    marker_size=(df.dPP_ast - min(df.dPP_ast))
    / (max(df.dPP_ast) - min(df.dPP_ast))
    * 100,
    text=df["dev"] + "<br>" + df["vars"],
    xaxis="x1",
    yaxis="y1",
)
tracel = go.Scatter(
    name="Diagonal",
    x=df["dSS_ast"],
    y=df["dSS_ast"],
    mode="lines",
    marker_color="red",
    line_width=0.2,
    xaxis="x1",
    yaxis="y1",
)
trace1 = go.Scatter(
    name="Astre",
    x=df_ast["time"],
    y=df_ast[var0],
    mode="lines+markers",
    marker_color="black",
    xaxis="x2",
    yaxis="y2",
)
trace2 = go.Scatter(
    name="Dynawo",
    x=df_dwo["time"],
    y=df_dwo[var0] - df_dwo[var0][0] + df_ast[var0][1],
    mode="lines",
    marker_color="red",
    xaxis="x2",
    yaxis="y2",
)
trace3 = go.Scatter(
    name="Transf. Load Tap Changes",
    x=df_m["time"],
    y=df_m["ldtap_netchanges"],
    stackgroup="one",
    xaxis="x3",
    yaxis="y3",
)
trace4 = go.Scatter(
    name="Transf. Tap Changes",
    x=df_m["time"],
    y=df_m["tap_netchanges"],
    stackgroup="one",
    xaxis="x3",
    yaxis="y3",
)
trace5 = go.Scatter(
    name="Shunt Changes",
    x=df_m["time"],
    y=df_m["shunt_netchanges"],
    stackgroup="one",
    xaxis="x3",
    yaxis="y3",
)
trace6 = go.Scatter(
    name="delta Level K",
    x=df_lk["time"],
    y=df_lk["deltaLevelK"],
    stackgroup="one",
    xaxis="x3",
    yaxis="y3",
)

# Plot layout
HEIGHT = 600  # Adapt as needed
WIDTH = 1600  # but make sure that width > height
aspect_ratio = HEIGHT / WIDTH
layout = go.Layout(
    title=dict(text="Astre vs Dynawo"),
    xaxis=dict(title="dSS Astre", domain=[0, aspect_ratio - 0.05]),
    yaxis=dict(title="dSS Dynawo", scaleanchor="x", scaleratio=1),
    xaxis2=dict(title="t", domain=[aspect_ratio + 0.05, 1], range=[0, 1200]),
    yaxis2=dict(title=var0, anchor="x2", domain=[0, 0.7]),
    xaxis3=dict(title="t", domain=[aspect_ratio + 0.05, 1], range=[0, 1200]),
    yaxis3=dict(title="% changes", anchor="x3", domain=[0.8, 1]),
    height=HEIGHT,
    width=WIDTH,
)
g = go.FigureWidget(
    data=[trace, trace1, trace2, trace3, trace4, trace5, trace6, tracel], layout=layout
)
scatter = g.data[0]
# Wire-in the plot callbacks
var.observe(response, names="value")
mask.observe(response, names="value")
dev.observe(response2, names="value")
var2.observe(response3, names="value")
check.observe(response, names="value")
scatter.on_click(update_serie)


########################################################
# COMPOUND SCORING
########################################################

# Calculate scores by contingency case and and variable.
scores = calc_scores_bycasevar(delta)
grid_bycasevar = qgrid.show_grid(scores)

# Main plot
container = widgets.HBox([check, mask, var, dev, var2])

# Calculate scores by contingency case, and save to file
scores_mean = calc_scores_bycase(scores)
grid_bycase = get_grid_bycase(scores_mean)
name = CRV_DIR.split("/")
ln = len(name)
filename = name[ln - 3] + "_" + PREFIX + ".csv"
scores_mean.to_csv(filename)

stable = np.where(scores_mean.Stable_ini & scores_mean.Stable_fin)
per_ss = round(scores_mean.dSS_pass_.mean() * 100, 1)
per_pp = round(scores_mean.dPP_pass_.mean() * 100, 1)
per1_ss = round(scores_mean.iloc[stable].dSS_pass_.mean() * 100, 1)
per1_pp = round(scores_mean.iloc[stable].dPP_pass_.mean() * 100, 1)

text = "# Percentage of all contingency passing: \n \
## Steady State Thresholds: %.1f%% \n \
## Peak to Peak Thresholds: %.1f%% \n \
# Percentage of stable  contingency passing: \n \
## Steady State Thresholds: %.1f%% \n \
## Peak to Peak Thresholds: %.1f%% \n"

md(text % (per_ss, per_pp, per1_ss, per1_pp))
