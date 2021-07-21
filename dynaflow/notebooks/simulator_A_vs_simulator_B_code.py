import pandas as pd
import plotly.graph_objects as go
import create_graph
from IPython.display import display, HTML
import qgrid
from ipywidgets import widgets
import networkx as nx
from pyvis.network import Network
import warnings
from matplotlib import pylab, cm
import pylab as pl
import numpy as np


# Read the metric file
def read_csv_metrics(pf_dir):
    data = pd.read_csv(pf_dir + "/pf_metrics/metrics.csv.xz", index_col=0)
    return data


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


# Create the general graphic of simulator A vs B
def create_general_trace(data, x, y):
    trace = go.Scatter(
        x=data[x], y=data[y], mode="markers", text=data["cont"], name=x + "_" + y
    )
    return trace


# Create the individual graphic of simulator A vs B
def create_individual_trace(data, x, y, DATA_LIMIT):
    if data.shape[0] > DATA_LIMIT:
        data = data.sample(DATA_LIMIT)
    trace = go.Scatter(
        x=data[x], y=data[y], mode="markers", text=data["ID"], name=x + "_" + y
    )
    return trace


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
):

    varx = widgets.Dropdown(
        options=df.columns[1:],
        value=df.columns[1],
        description="X: ",
    )

    vary = widgets.Dropdown(
        options=df.columns[1:],
        value=df.columns[2],
        description="Y: ",
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

    return (
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
):
    container1 = widgets.HBox([varx, vary])

    container2 = widgets.HBox([dev, dropdown1, dropdown2, dropdown3, dropdown4])

    container3 = widgets.HBox(
        [graph, nodetype, nodemetrictype, edgetype, edgemetrictype]
    )

    return container1, container2, container3


# Create all the layouts of the output
def create_layouts(varx, vary, HEIGHT, WIDTH, contg_case0, dropdown1, dropdown2):
    layout1 = go.Layout(
        title=dict(text="Simulator A vs Simulator B"),
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

    return layout1, layout2


# Paint the node colors of the graph
def paint_graph(C, data, nodetype, nodemetrictype, edgetype, edgemetrictype):
    # Node color
    data1 = data.loc[(data.VAR == nodetype) & (data.ELEMENT_TYPE == "bus")]
    """
    data1_max = 0
    data1_min = 99999999
    for node in C.nodes:
        value = list(data1.loc[(data1.ID == node["id"])][nodemetrictype])[0]
        if value > data1_max:
            data1_max = value
        if value < data1_min:
            data1_min = value
    """
    data1_max = data1[nodemetrictype].max()
    data1_min = data1[nodemetrictype].min()

    data1_max -= data1_min
    for node in C.nodes:
        if len(list(data1.loc[(data1.ID == node["id"])][nodemetrictype])) != 0:
            plasma = cm.get_cmap('plasma', 12)
            c = list(data1.loc[(data1.ID == node["id"])][nodemetrictype])[0] - data1_min
            c = c / data1_max
            r = plasma(c)[0]*256
            g = plasma(c)[1]*256
            b = plasma(c)[2]*256
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
    """
    data2_max = 0
    data2_min = 99999999
    for edge in C.edges:
        value = list(data2.loc[(data2.ID == edge["id"])][edgemetrictype])[0]
        if value > data2_max:
            data2_max = value
        if value < data2_min:
            data2_min = value
    """
    data2_max = data2[edgemetrictype].max()
    data2_min = data2[edgemetrictype].min()

    data2_max -= data2_min
    for edge in C.edges:
        if len(list(data2.loc[(data2.ID == edge["id"])][edgemetrictype])) != 0:
            viridis = cm.get_cmap('viridis', 12)
            c = list(data2.loc[(data2.ID == edge["id"])][edgemetrictype])[0] - data2_min
            c = c / data2_max
            r = viridis(c)[0]*256
            g = viridis(c)[1]*256
            b = viridis(c)[2]*256
            
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
def show_displays(sdf, container1, g, container2, c, s, container3, C, dev, container4):
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
    display(sdf)
    display(container1)
    display(g)
    display(container2)
    display(c)
    display(s)
    display(container3)
    html_graph = display(C.show("subgraph.html"), display_id=True)
    display(container4)
    print(
        "If a node is white it means that the selected metric is not available",
        "for that node.",
    )
    print(
        "If an edge is white it means that the metric does not exist or it is a "
        "double/triple, edge and should be calculated manually."
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
):

    # We have to supress a numpy warning
    warnings.simplefilter(action="ignore", category=FutureWarning)

    # Management the selection of dropdown parameters and on_click options
    def response(change):
        # PERF: Plotly starts showing horrible performance with more than 5,000 points
        if df1.shape[0] > DATA_LIMIT:
            df1 = df1.sample(DATA_LIMIT)
        with g.batch_update():
            g.data[0].x = df1[varx.value]
            g.data[0].y = df1[vary.value]
            g.data[0].name = varx.value + "_" + vary.value
            g.data[0].text = df1["cont"]
            g.layout.xaxis.title = varx.value
            g.layout.yaxis.title = vary.value

    def individual_case(case):
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
            s.df = df1.sort_values("ID")
            c.data[0].x = df1[dropdown1.value]
            c.data[0].y = df1[dropdown2.value]
            c.data[0].name = dropdown1.value + "_" + dropdown2.value
            c.data[0].text = df1["ID"]
            c.layout.xaxis.title = dropdown1.value
            c.layout.yaxis.title = dropdown2.value
            c.layout.title.text = "Case: " + case
            dev.value = case

    def update_case(trace, points, selector):
        individual_case(contg_cases[points.point_inds[0]])

    def response2(change):
        individual_case(dev.value)

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

    do_displaybutton()

    df = read_csv_metrics(PF_SOL_DIR)

    # Get list of contingency cases
    contg_cases = list(df["cont"].unique())
    contg_case0 = contg_cases[0]

    # Read the first contingency to put default data
    data_first_case = read_case(contg_case0, PF_SOL_DIR, PREFIX)

    vars_case = data_first_case.columns[1:]

    # Get the bus list for subgraph selection
    bus_list = sorted(
        list(set(data_first_case.loc[(data_first_case.ELEMENT_TYPE == "bus")]["ID"]))
    )

    nodetypes = ["v", "angle", "p", "q"]

    nodemetrictypes = ["DIFF", "ABS_ERR", "REL_ERR", "VALUE_A", "VALUE_B"]

    edgetypes = ["p1", "p2", "q1", "q2"]

    edgemetrictypes = ["DIFF", "ABS_ERR", "REL_ERR", "VALUE_A", "VALUE_B"]

    # Get all the dropdowns
    (
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
    )

    # Get all the containers
    container1, container2, container3 = create_containers(
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
    )

    # Get all the layouts
    layout1, layout2 = create_layouts(
        varx, vary, HEIGHT, WIDTH, contg_case0, dropdown1, dropdown2
    )

    current_general_trace = create_general_trace(df, varx.value, vary.value)

    current_individual_trace = create_individual_trace(
        data_first_case, dropdown1.value, dropdown2.value, DATA_LIMIT
    )

    # Create the required widgets for visualization
    sdf = qgrid.QgridWidget(df=df)

    g = go.FigureWidget(data=[current_general_trace], layout=layout1)

    c = go.FigureWidget(data=[current_individual_trace], layout=layout2)

    s = qgrid.QgridWidget(df=data_first_case)

    xiidm_file = RESULTS_DIR + BASECASE + "/recollement_20210422_0930.xiidm"
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
        value=legend1,
        format="png",
        width=WIDTH / 2,
        height=HEIGHT / 2,
    )

    legend2widget = widgets.Image(
        value=legend2,
        format="png",
        width=WIDTH / 2,
        height=HEIGHT / 2,
    )

    container4 = widgets.HBox([legend1widget, legend2widget])

    # Display all the objects and get html subgraph id
    html_graph = show_displays(
        sdf, container1, g, container2, c, s, container3, C, dev, container4
    )

    # Observe selection events to update graphics
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
