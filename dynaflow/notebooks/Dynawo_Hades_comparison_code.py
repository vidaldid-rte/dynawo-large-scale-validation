import glob
import pandas as pd
from tqdm.notebook import tqdm
import plotly.graph_objects as go

def read_csv_metrics(pf_dir):
    data = pd.read_csv(pf_dir+'/pf_metrics/metrics.csv.xz', index_col=0)
    return data


    