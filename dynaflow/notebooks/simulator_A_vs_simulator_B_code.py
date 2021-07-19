import pandas as pd
import plotly.graph_objects as go
import create_graph
from IPython.display import display, HTML
import qgrid
from ipywidgets import widgets
import networkx as nx
from pyvis.network import Network
import warnings


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
    data["diff"] = abs(data.VALUE_A - data.VALUE_B)
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
    df, contg_cases, contg_case0, data_first_case, vars_case, bus_list
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

    graph = widgets.Dropdown(options=bus_list, value=bus_list[0], description="Var: ")

    return varx, vary, dev, dropdown1, dropdown2, dropdown3, dropdown4, graph


# Create all the containers of the output
def create_containers(
    varx, vary, dev, dropdown1, dropdown2, dropdown3, dropdown4, graph
):
    container1 = widgets.HBox([varx, vary])

    container2 = widgets.HBox([dev, dropdown1, dropdown2, dropdown3, dropdown4])

    container3 = widgets.HBox([graph])

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


# Show the output
def show_displays(sdf, container1, g, container2, c, s, container3, C, dev):
    display(sdf)
    display(container1)
    display(g)
    display(container2)
    display(c)
    display(s)
    display(container3)
    html_graph = display(C.show("subgraph.html"), display_id=True)
    return html_graph


# Run the program
def run_all(RESULTS_DIR, ELEMENTS, PREFIX, PF_SOL_DIR, DATA_LIMIT):
    warnings.simplefilter(action="ignore", category=FutureWarning)

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

    # Management the selection of dropdown parameters and on_click options
    def response(change):
        df1 = df
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
            s.df = df1
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
        with g.batch_update():
            C = create_graph.get_subgraph(G, graph.value, 0, 4)
            html_graph.update(C.show("subgraph.html"))

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
    ) = create_dropdowns(
        df, contg_cases, contg_case0, data_first_case, vars_case, bus_list
    )

    # Get all the containers
    container1, container2, container3 = create_containers(
        varx, vary, dev, dropdown1, dropdown2, dropdown3, dropdown4, graph
    )

    HEIGHT = 600  # Adapt as needed
    WIDTH = 1600  # but make sure that width > height

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

    xiidm_file = (
        "../../../cases/"
        + "20210422_0930.BASECASE"
        + "/recollement_20210422_0930.xiidm"
    )
    # Get default graph
    G, C = get_initial_graph(xiidm_file, graph.value, 0, 4)

    # Display all the objects and get html subgraph id
    html_graph = show_displays(sdf, container1, g, container2, c, s, container3, C, dev)

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
