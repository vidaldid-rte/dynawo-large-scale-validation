import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import seaborn as sns
import qgrid
from ipywidgets import widgets
from IPython.display import display, HTML, Markdown

PLOTLY_MAXPOINTS = 5000  # Plotly becomes *very* slow when charts exceed this


# Auxiliary function for calculating delta levelK at the aut_tw_metrics points
def getDeltaLevelK(df_ast, df_dwo, t_end):
    df_m = pd.DataFrame(np.linspace(0, t_end, 41))  # same no. of points as aut_tw
    df_m.columns = ["time"]
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
def get_curve_dfs(crv_dir, prefix, contg_case, IS_DWO_DWO):
    if IS_DWO_DWO == 0:
        ast_case = crv_dir + "/" + prefix + contg_case + "-AstreCurves.csv.xz"
        dwo_case = crv_dir + "/" + prefix + contg_case + "-DynawoCurves.csv.xz"
    elif IS_DWO_DWO == 1:
        ast_case = crv_dir + "/" + prefix + contg_case + "-DynawoCurvesA.csv.xz"
        dwo_case = crv_dir + "/" + prefix + contg_case + "-DynawoCurvesB.csv.xz"

    df_ast = pd.read_csv(ast_case, sep=";", index_col=False, compression="infer")
    df_dwo = pd.read_csv(dwo_case, sep=";", index_col=False, compression="infer")
    # TODO: ASTDWO/DWODWO DEPENDENCY:
    if IS_DWO_DWO == 1:
        df_ast = df_ast.iloc[:, :-1]  # because of extra ";" at end-of-lines
    df_dwo = df_dwo.iloc[:, :-1]  # because of extra ";" at end-of-lines
    if IS_DWO_DWO == 1:
        TFIN_TIME_OFFSET = df_ast["time"][0]  # Dynawo's time offset
        df_ast["time"] = round(df_ast.time - TFIN_TIME_OFFSET)
    TFIN_TIME_OFFSET = df_dwo["time"][0]  # Dynawo's time offset
    df_dwo["time"] = round(df_dwo.time - TFIN_TIME_OFFSET)

    da = df_ast.copy()
    dd = df_dwo.copy()

    t_end = df_dwo["time"].iat[-1]
    df_lk = getDeltaLevelK(da, dd, t_end)

    return df_ast, df_dwo, df_lk, t_end


def calc_scores_bycasevar(delta):
    # The scores consist in relative change in metrics (keeping the sign).
    # The global one consists in the (weighted) abs-sum of all the others.
    scores = delta[
        [
            "dev",
            "vars",
            "is_preStab_ast",
            "is_preStab_dwo",
            "is_postStab_ast",
            "is_postStab_dwo",
            "dSS_pass",
            "dPP_pass",
        ]
    ].copy()
    scores.columns = [
        "Contg_case",
        "Variable",
        "pre_ast",
        "pre_dwo",
        "post_ast",
        "post_dwo",
        "dSS_pass",
        "dPP_pass",
    ]
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

    scores = scores.set_index(["Contg_case", "Variable"])
    return scores


def calc_scores_bycase(scores, aut_metrics):
    # For each case, we keep the mean scores found accross the monitored variables.
    scores[["dSS", "dPP", "TT", "period", "damp"]] = scores[
        ["dSS", "dPP", "TT", "period", "damp"]
    ].abs()
    scores_mean = scores.groupby(["Contg_case"]).mean()
    scores_sum = scores[["dSS_pass", "dPP_pass"]].groupby(["Contg_case"]).sum()
    scores_count = scores[["dSS_pass", "dPP_pass"]].groupby(["Contg_case"]).count()
    scores_mean["dSS_viol"] = scores_count.dSS_pass - scores_sum.dSS_pass
    scores_mean["dPP_viol"] = scores_count.dPP_pass - scores_sum.dPP_pass
    scores_mean["dSS_pass_"] = scores_mean.dSS_pass > 0.999
    scores_mean["dPP_pass_"] = scores_mean.dPP_pass > 0.999

    scores_mean["Stable_pre"] = np.where(
        ((scores_mean.pre_ast > 0.999) & (scores_mean.pre_dwo > 0.999)), True, False
    )
    scores_mean["Stable_post"] = np.where(
        ((scores_mean.post_ast > 0.999) & (scores_mean.post_dwo > 0.999)), True, False
    )

    scores_mean = scores_mean.merge(aut_metrics, on="Contg_case")
    alpha = 0.5
    scores_mean["global"] = (
        alpha * scores_mean["global_crv"] + (1 - alpha) * scores_mean["global_aut"]
    )
    return scores_mean


def get_grid_bycase(scores_mean):
    cols = [
        "Contg_case",
        "Stable_pre",
        "Stable_post",
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
    scores_mean_g = scores_mean[cols].set_index(["Contg_case"])
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
    scores_mean = scores_mean.set_index(["Contg_case"])
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
    state = True
    toggle_code(state)
    button_descriptions = {False: "Show code", True: "Hide code"}
    button = widgets.ToggleButton(state, description=button_descriptions[state])
    button.observe(button_action, "value")
    display(button)


###################################################
# NOTEBOOK MAIN CODE STARTS HERE
###################################################


def main(
    CRV_DIR,
    PREFIX,
    IS_DWO_DWO,
    MATCH_CRV_AT_PRECONTG_TIME,
    V_THRESH,
    K_THRESH,
    P_THRESH,
    Q_THRESH,
):
    # Callbacks
    def response(change):
        df = delta
        if check.value:
            stable = np.where(
                df.is_preStab_ast
                & df.is_preStab_dwo
                & df.is_postStab_ast
                & df.is_postStab_dwo
            )
            df = df.iloc[stable]
        mask_ = [mask.value in x for x in df.vars]
        df = df[mask_]
        if df.shape[0] > PLOTLY_MAXPOINTS:
            df = reduce_xyscatter_points(df)
        with g.batch_update():
            g.data[0].x = df[var.value + "_ast"]
            g.data[0].y = df[var.value + "_dwo"]
            xymin = min(df[var.value + "_ast"].min(), df[var.value + "_dwo"].min())
            xymax = max(df[var.value + "_ast"].max(), df[var.value + "_dwo"].max())
            g.data[7].x = [xymin, xymax]
            g.data[7].y = [xymin, xymax]
            g.data[0].marker.color = df.TT_ast
            g.data[0].marker.size = 5 + 45 * (df.dPP_ast - min(df.dPP_ast)) / max(
                1.0e-6, max(df.dPP_ast) - min(df.dPP_ast)
            )
            g.data[0].text = df["dev"] + "<br>" + df["vars"]
            if IS_DWO_DWO == 0:
                g.layout.xaxis.title = var.value + " Astre"
                g.layout.yaxis.title = var.value + " Dynawo"
            elif IS_DWO_DWO == 1:
                g.layout.xaxis.title = var.value + " Dynawo A"
                g.layout.yaxis.title = var.value + " Dynawo B"
            else:
                raise ValueError("IS_DWO_DWO must be 0 or 1.")
        print_subfig_globalscatter()

    def reduce_xyscatter_points(df):
        # Plotly's performance is horrible past ~5000 points in a
        # chart. So we eliminate these non-interesting points:
        #   * points too close to the diagonal --> by looking at the tangent
        #   * points too close to (0,0) --> relative to the scale
        diagdist_df = abs(df[var.value + "_dwo"] / df[var.value + "_ast"] - 1)
        xorigdist_df = abs(df[var.value + "_ast"])
        yorigdist_df = abs(df[var.value + "_dwo"])
        data_scale = max(xorigdist_df.max(), yorigdist_df.max())
        for r1, r2 in np.linspace([0.005, 0.00005], [0.1, 0.005], num=10):
            filter = (
                (diagdist_df > r1)
                & (xorigdist_df > r2 * data_scale)
                & (yorigdist_df > r2 * data_scale)
            )
            if filter.sum() < PLOTLY_MAXPOINTS:
                break
        print(f"Warning: reducing the number of shown points to: {filter.sum()}")
        print(
            f"(not showing points with abs(1-x/y) < {r1}"
            f" and abs(x),abs(y) < {r2}*data_scale)"
        )
        return df.loc[filter]

    def response2(change):
        df_ast, df_dwo, df_lk, _ = get_curve_dfs(CRV_DIR, PREFIX, dev.value, IS_DWO_DWO)
        vars_dwo = df_dwo.columns[1:]
        var2.options = vars_dwo
        var2.value = vars_dwo[0]
        df_m = aut_tw_metrics[aut_tw_metrics.Contg_case == dev.value].copy()
        df_m.loc[len(df_m)] = [dev.value, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        if MATCH_CRV_AT_PRECONTG_TIME:
            idx_match_ast = abs(df_ast["time"] - MATCH_CRV_AT_PRECONTG_TIME).idxmin()
            idx_match_dwo = abs(df_dwo["time"] - MATCH_CRV_AT_PRECONTG_TIME).idxmin()
            yoffset = (
                df_ast[var2.value][idx_match_ast] - df_dwo[var2.value][idx_match_dwo]
            )
        else:
            yoffset = 0
        with g.batch_update():
            g.data[1].y = df_ast[var2.value]
            g.data[2].y = df_dwo[var2.value] + yoffset
            g.data[3].x = df_m["time"]
            g.data[4].x = df_m["time"]
            g.data[5].x = df_m["time"]
            g.data[6].x = df_lk["time"]
            g.data[3].y = df_m["ldtap_netchanges"]
            g.data[4].y = df_m["tap_netchanges"]
            g.data[5].y = df_m["shunt_netchanges"]
            g.data[6].y = df_lk["deltaLevelK"]
            g.layout.yaxis2.title = var2.value
        print_subfig_curve()
        print_subfig_eventdiffs()
        print_subfig_curve_and_events()

    def response3(change):
        df_ast, df_dwo, df_lk, _ = get_curve_dfs(CRV_DIR, PREFIX, dev.value, IS_DWO_DWO)
        df_m = aut_tw_metrics[aut_tw_metrics.Contg_case == dev.value].copy()
        df_m.loc[len(df_m)] = [dev.value, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        if MATCH_CRV_AT_PRECONTG_TIME:
            idx_match_ast = abs(df_ast["time"] - MATCH_CRV_AT_PRECONTG_TIME).idxmin()
            idx_match_dwo = abs(df_dwo["time"] - MATCH_CRV_AT_PRECONTG_TIME).idxmin()
            yoffset = (
                df_ast[var2.value][idx_match_ast] - df_dwo[var2.value][idx_match_dwo]
            )
        else:
            yoffset = 0
        with g.batch_update():
            g.data[1].y = df_ast[var2.value]
            g.data[2].y = df_dwo[var2.value] + yoffset
            g.data[3].x = df_m["time"]
            g.data[4].x = df_m["time"]
            g.data[5].x = df_m["time"]
            g.data[6].x = df_lk["time"]
            g.data[3].y = df_m["ldtap_netchanges"]
            g.data[4].y = df_m["tap_netchanges"]
            g.data[5].y = df_m["shunt_netchanges"]
            g.data[6].y = df_lk["deltaLevelK"]
            g.layout.yaxis2.title = var2.value
        print_subfig_curve()
        print_subfig_curve_and_events()

    def update_serie(trace, points, selector):
        # t = list(scatter.text)
        for i in points.point_inds:
            # print(scatter.text[i])
            with g.batch_update():
                dev0 = scatter.text[i].split("<")[0]
                dev1 = scatter.text[i].split(">")[1]
                dev.value = dev0
                var2.value = dev1
        print_subfig_curve()
        print_subfig_eventdiffs()
        print_subfig_curve_and_events()

    # Functions for printing figs to PDF (from the callbacks)
    def print_subfig_globalscatter():
        subfig_globalscatter = go.Figure(
            data=[g.data[0]],
            layout=go.Layout(
                xaxis=dict(title=g.layout.xaxis.title),
                yaxis=dict(
                    title=g.layout.yaxis.title,
                    scaleanchor="x",
                    scaleratio=1,
                ),
                height=800,
                width=820,
                margin=dict(l=5, r=5, t=5, b=5, autoexpand=True),
                font=dict(family="Arial", size=24),
            ),
        )
        subfig_globalscatter.write_image("fig_globalscatter.pdf", engine="kaleido")

    def print_subfig_curve():
        subfig_curve = go.Figure(
            data=[g.data[1], g.data[2]],
            layout=go.Layout(
                xaxis2=dict(title="t / s"),
                yaxis2=dict(title=g.layout.yaxis2.title),
                showlegend=False,
                height=600,
                width=820,
                margin=dict(l=5, r=5, t=5, b=5, autoexpand=True),
                font=dict(family="Arial", size=22),
            ),
        )
        subfig_curve.write_image("fig_curve.pdf", engine="kaleido")

    def print_subfig_eventdiffs():
        subfig_eventdiffs = go.Figure(
            data=[g.data[3], g.data[4], g.data[5]],
            layout=go.Layout(
                xaxis3=dict(title="t / s"),
                yaxis3=dict(title=g.layout.yaxis3.title),
                showlegend=False,
                height=400,
                width=820,
                margin=dict(l=5, r=5, t=5, b=5, autoexpand=True),
                font=dict(family="Arial", size=22),
            ),
        )
        subfig_eventdiffs.write_image("fig_eventdiffs.pdf", engine="kaleido")

    def print_subfig_curve_and_events():
        subfig_curve_and_events = go.Figure(
            data=[g.data[1], g.data[2], g.data[3], g.data[4], g.data[5]],
            layout=go.Layout(
                xaxis2=dict(title="t / s"),
                yaxis2=dict(title=g.layout.yaxis2.title, domain=[0, 0.7]),
                xaxis3=dict(scaleanchor="x2"),
                yaxis3=dict(title=g.layout.yaxis3.title, domain=[0.8, 1]),
                showlegend=True,
                height=550,
                width=820,
                margin=dict(l=5, r=5, t=5, b=5, autoexpand=True),
                font=dict(family="Arial", size=18),
            ),
        )
        subfig_curve_and_events.write_image(
            "fig_curve_and_events.pdf", engine="kaleido"
        )

    ###########################################################
    # END OF INNER FUNCTIONS; MAIN CODE STARTS HERE
    ###########################################################

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

    # Read the metrics
    metrics_dir = CRV_DIR + "/../metrics"
    crv_reducedparams_file = metrics_dir + "/crv_reducedparams.csv"
    aut_metrics_file = metrics_dir + "/aut_diffmetrics.csv"
    aut_tw_metrics_file = metrics_dir + "/aut_tw_diffmetrics.csv"

    if not (
        os.path.isdir(metrics_dir)
        and os.path.isfile(crv_reducedparams_file)
        and os.path.isfile(aut_metrics_file)
        and os.path.isfile(aut_tw_metrics_file)
    ):
        raise ValueError("Input datafiles (metrics) not found for %s" % CRV_DIR)

    delta = pd.read_csv(
        crv_reducedparams_file, sep=";", index_col=False, compression="infer"
    )
    delta.fillna(-1, inplace=True)

    aut_metrics = pd.read_csv(
        aut_metrics_file, sep=";", index_col=False, compression="infer"
    )
    aut_metrics["global_aut"] = aut_metrics[aut_metrics.columns[1:]].mean(axis=1)

    aut_tw_metrics = pd.read_csv(
        aut_tw_metrics_file, sep=";", index_col=False, compression="infer"
    )

    # Determine pass/fail for each type of magnitude, according to thresholds
    delta["typevar"] = ""
    delta.loc[delta.vars.str.contains("_U_IMPIN"), "typevar"] = "V"
    delta.loc[delta.vars.str.contains("_Upu_"), "typevar"] = "V"
    delta.loc[delta.vars.str.contains("_levelK_"), "typevar"] = "K"
    delta.loc[delta.vars.str.contains("_PGen"), "typevar"] = "P"
    delta.loc[delta.vars.str.contains("_QGen"), "typevar"] = "Q"
    d_threshold = {"V": V_THRESH, "K": K_THRESH, "P": P_THRESH, "Q": Q_THRESH}
    delta["threshold"] = delta.typevar.replace(d_threshold)
    delta["delta_dSS"] = delta["dSS_ast"] - delta["dSS_dwo"]
    delta["dSS_pass"] = delta.delta_dSS.abs() < delta.threshold
    delta["delta_dPP"] = delta["dPP_ast"] - delta["dPP_dwo"]
    delta["dPP_pass"] = delta.delta_dPP.abs() < delta.threshold

    # Load the curve data for the first case
    contg_cases = list(delta["dev"].unique())
    contg_case0 = contg_cases[0]
    df_ast, df_dwo, df_lk, T_END = get_curve_dfs(
        CRV_DIR, PREFIX, contg_case0, IS_DWO_DWO
    )
    vars_dwo = df_dwo.columns[1:]  # Astre's var names are assumed to be the same
    var0 = vars_dwo[0]
    var2 = widgets.Dropdown(options=vars_dwo, value=var0, description="Variable: ")
    df_m = aut_tw_metrics[aut_tw_metrics.Contg_case == contg_case0].copy()
    df_m.loc[len(df_m)] = [contg_case0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    if MATCH_CRV_AT_PRECONTG_TIME:
        idx_match_ast = abs(df_ast["time"] - MATCH_CRV_AT_PRECONTG_TIME).idxmin()
        idx_match_dwo = abs(df_dwo["time"] - MATCH_CRV_AT_PRECONTG_TIME).idxmin()
        yoffset = df_ast[var2.value][idx_match_ast] - df_dwo[var2.value][idx_match_dwo]
    else:
        yoffset = 0

    # Initialize Combo Boxes
    check = widgets.Checkbox(
        value=False,
        description="Only Stable contingencies",
        disabled=False,
        indent=False,
    )
    mask_n = ["NETWORK" in x for x in delta.vars]
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
    dev = widgets.Dropdown(
        options=contg_cases, value=contg_case0, description="Contg. case: "
    )
    container = widgets.HBox([check, mask, var, dev, var2])

    # Initialize Plot Traces
    if df.shape[0] > PLOTLY_MAXPOINTS:
        df = reduce_xyscatter_points(df)
    trace = go.Scatter(
        name="A/B var scatter",
        x=df[var.value + "_ast"],
        y=df[var.value + "_dwo"],
        mode="markers",
        marker_color=df.TT_ast,
        marker_size=5
        + 45
        * (df.dPP_ast - min(df.dPP_ast))
        / max(1.0e-6, max(df.dPP_ast) - min(df.dPP_ast)),
        text=df["dev"] + "<br>" + df["vars"],
        xaxis="x1",
        yaxis="y1",
    )

    xymin = min(df[var.value + "_ast"].min(), df[var.value + "_dwo"].min())
    xymax = max(df[var.value + "_ast"].max(), df[var.value + "_dwo"].max())
    tracel = go.Scatter(
        name="Diagonal",
        x=[xymin, xymax],
        y=[xymin, xymax],
        mode="lines",
        marker_color="red",
        line_width=0.2,
        xaxis="x1",
        yaxis="y1",
    )

    if IS_DWO_DWO == 0:
        curve_nameA = "Astre"
        curve_modeA = "lines+markers"
        curve_colorA = "black"
        curve_nameB = "Dynawo"
        curve_modeB = "lines"
        curve_colorB = "red"
    elif IS_DWO_DWO == 1:
        curve_nameA = "Dynawo A"
        curve_modeA = "lines"
        curve_colorA = "blue"
        curve_nameB = "Dynawo B"
        curve_modeB = "lines"
        curve_colorB = "red"
    else:
        raise ValueError("IS_DWO_DWO must be 0 or 1.")
    trace1 = go.Scatter(
        name=curve_nameA,
        x=df_ast["time"],
        y=df_ast[var0],
        mode=curve_modeA,
        marker_color=curve_colorA,
        xaxis="x2",
        yaxis="y2",
    )
    trace2 = go.Scatter(
        name=curve_nameB,
        x=df_dwo["time"],
        y=df_dwo[var0] + yoffset,
        mode=curve_modeB,
        marker_color=curve_colorB,
        xaxis="x2",
        yaxis="y2",
    )

    trace3 = go.Scatter(
        name="Load tap changes",
        x=df_m["time"],
        y=df_m["ldtap_netchanges"],
        stackgroup="one",
        xaxis="x3",
        yaxis="y3",
    )
    trace4 = go.Scatter(
        name="Xfmr tap changes",
        x=df_m["time"],
        y=df_m["tap_netchanges"],
        stackgroup="one",
        xaxis="x3",
        yaxis="y3",
    )
    trace5 = go.Scatter(
        name="Shunt changes",
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
    if IS_DWO_DWO == 0:
        xaxis_title = var.value + " Astre"
        yaxis_title = var.value + " Dynawo"
    elif IS_DWO_DWO == 1:
        xaxis_title = var.value + " DynawoA"
        yaxis_title = var.value + " DynawoB"
    else:
        raise ValueError("IS_DWO_DWO must be 0 or 1.")
    layout = go.Layout(
        xaxis=dict(title=xaxis_title, domain=[0, aspect_ratio - 0.05]),
        yaxis=dict(title=yaxis_title, scaleanchor="x", scaleratio=1),
        xaxis2=dict(title="t", domain=[aspect_ratio + 0.05, 1], range=[0, T_END]),
        yaxis2=dict(title=var0, anchor="x2", domain=[0, 0.7]),
        xaxis3=dict(
            scaleanchor="x2",
            scaleratio=1,
            domain=[aspect_ratio + 0.05, 1],
            range=[0, T_END],
        ),
        yaxis3=dict(title="% changes", anchor="x3", domain=[0.8, 1]),
        height=HEIGHT,
        width=WIDTH,
    )

    # Main plot
    g = go.FigureWidget(
        data=[trace, trace1, trace2, trace3, trace4, trace5, trace6, tracel],
        layout=layout,
    )

    # Wire-in the plot callbacks
    var.observe(response, names="value")
    mask.observe(response, names="value")
    dev.observe(response2, names="value")
    var2.observe(response3, names="value")
    check.observe(response, names="value")
    scatter = g.data[0]
    scatter.on_click(update_serie)

    ########################################################
    # COMPOUND SCORING
    ########################################################

    # Calculate scores by contingency case and and variable.
    scores = calc_scores_bycasevar(delta)
    grid_bycasevar = qgrid.show_grid(scores)

    # Calculate scores by contingency case, and save to file
    scores_mean = calc_scores_bycase(scores, aut_metrics)
    grid_bycase = get_grid_bycase(scores_mean)
    name = CRV_DIR.split("/")
    ln = len(name)
    filename = name[ln - 3] + "_" + PREFIX + ".csv"
    scores_mean.to_csv(filename)

    stable = np.where(scores_mean.Stable_pre & scores_mean.Stable_post)
    per_ss = round(scores_mean.dSS_pass_.mean() * 100, 1)
    per_pp = round(scores_mean.dPP_pass_.mean() * 100, 1)
    per1_ss = round(scores_mean.iloc[stable].dSS_pass_.mean() * 100, 1)
    per1_pp = round(scores_mean.iloc[stable].dPP_pass_.mean() * 100, 1)

    display(
        Markdown(
            f"# Analyzing data from: {CRV_DIR}\n"
            "## Percentage of contingency cases where all variables pass: \n"
            f"  * by Steady-State diff thresholds: {per_ss:.1f}% \n"
            f"  * by Peak-to-Peak diff thresholds: {per_pp:.1f}% \n\n"
            "## Percentage of *stable* contingency cases where all variables pass: \n"
            f"  * by Steady-State diff thresholds: {per1_ss:.1f}% \n"
            f"  * by Peak-to-Peak diff thresholds: {per1_pp:.1f}% \n\n"
            "Using threshold parameters:\n"
            f"  * V_THRESH: {V_THRESH:.2f} pu\n"
            f"  * K_THRESH: {K_THRESH:.2f}\n"
            f"  * P_THRESH: {P_THRESH:.2f} MW\n"
            f"  * Q_THRESH: {Q_THRESH:.2f} MW\n"
        )
    )

    display(Markdown("# SCORING BY VARIABLE"))
    display(grid_bycasevar)
    display(Markdown("## Graphical analysis of variables"))
    display(widgets.VBox([container, g]))

    display(Markdown("# SCORING BY CONTINGENCY"))
    display(grid_bycase)
    display(Markdown("## Heatmap"))
    display(plot_heatmap(scores_mean))
