"""
AI Trade Tracker — Interactive Bokeh application for visualizing
U.S. imports of AI-related products.

Usage:
    bokeh serve --show main.py
"""
import datetime as dt
import pandas as pd
import io
import base64

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (ColumnDataSource, HoverTool, MultiChoice, Select,
                          NumeralTickFormatter, Div, Button, CustomJS)
from bokeh.plotting import figure

###############################################################################
# Configuration
###############################################################################

background = "#ffffff"

SERIES = {
    "AI Related":          {"col": "ai_related",          "color": "#00008B", "dash": "solid",  "width": 6},
    "Non-AI Related":      {"col": "non_ai_related",      "color": "#d62728", "dash": "solid",  "width": 6},
    "Compute Hardware":    {"col": "compute_hardware",     "color": "#2ca02c", "dash": [8, 4],   "width": 6},
    "Electrical Power":    {"col": "electrical_power",     "color": "#ff7f0e", "dash": [8, 4],   "width": 6},
    "Networking Telecom":  {"col": "networking_telecom",   "color": "#9467bd", "dash": [8, 4],   "width": 6},
    "Cooling HVAC":        {"col": "cooling_hvac",         "color": "#8c564b", "dash": [8, 4],   "width": 6},
    "Building Structure":  {"col": "building_structure",   "color": "#e377c2", "dash": [8, 4],   "width": 6},
    "Fire Safety Security":{"col": "fire_safety_security", "color": "#7f7f7f", "dash": [8, 4],   "width": 6},
    "Specialty Materials": {"col": "specialty_materials",   "color": "#bcbd22", "dash": [8, 4],   "width": 6},
}

series_options = list(SERIES.keys())
default_series = ["AI Related", "Non-AI Related"]
default_mode = "Index (2023 = 100)"

###############################################################################
# Load data
###############################################################################

df = pd.read_parquet("./data/ai_trade_series.parquet")

# Determine date range for plot
first_date = dt.datetime(2023, 1, 1)
last_date = df.index[-1] + pd.DateOffset(months=2)

###############################################################################
# Build plot
###############################################################################

def make_plot():

    height = int(1.15 * 533)
    width = int(1.15 * 750)

    selected = series_select.value
    mode = mode_select.value
    suffix = "_index" if "Index" in mode else "_dollars"

    if not selected:
        plot = figure(x_axis_type="datetime", height=height, width=width,
                      toolbar_location="below",
                      tools="box_zoom, reset, pan, xwheel_zoom, save",
                      title="Select one or more series",
                      x_range=(first_date, last_date))
        plot.sizing_mode = "scale_both"
        plot.max_height = height
        plot.max_width = width
        plot.min_height = int(0.25 * height)
        plot.min_width = int(0.25 * width)
        return plot

    title = "U.S. Imports of AI-Related Products"
    plot = figure(x_axis_type="datetime", height=height, width=width,
                  toolbar_location="below",
                  tools="box_zoom, reset, pan, xwheel_zoom, save",
                  title=title,
                  x_range=(first_date, last_date))

    for name in selected:
        meta = SERIES[name]
        col = meta["col"] + suffix
        y_values = df[col].values

        source = ColumnDataSource(data=dict(
            x=df.index,
            y=y_values,
            series=[name] * len(df),
        ))

        plot.line("x", "y", source=source,
                  line_width=meta["width"], line_alpha=0.75,
                  line_color=meta["color"], line_dash=meta["dash"],
                  legend_label=name)

    # Axis labels
    plot.xaxis.axis_label = None
    if "Index" in mode:
        plot.yaxis.axis_label = "Monthly Index (2023 = 100)"
    else:
        plot.yaxis.axis_label = "Imports ($B)"

    plot.axis.axis_label_text_font_style = "bold"
    plot.axis.axis_label_text_font_size = "14pt"
    plot.grid.grid_line_alpha = 0.3

    # Tooltips
    if "Index" in mode:
        val_fmt = "@y{0.1f}"
    else:
        val_fmt = "@y{0.00}"

    TOOLTIPS = f"""
    <div style="background-color:#F5F5F5; opacity: 0.95; padding: 6px;">
    <div style="text-align:left;">
    <span style="font-size: 13px; font-weight: bold">@series</span>
    </div>
    <div style="text-align:left;">
    <span style="font-size: 13px;">@x{{%b %Y}}:  {val_fmt}</span>
    </div>
    </div>
    """

    plot.add_tools(HoverTool(tooltips=TOOLTIPS, line_policy="nearest",
                             formatters={"@x": "datetime"}))

    # Legend
    plot.legend.location = "top_left"
    plot.legend.click_policy = "hide"
    plot.legend.label_text_font_size = "10pt"
    plot.legend.spacing = 2
    plot.legend.padding = 5

    # Styling
    plot.title.text_font_size = "14pt"
    plot.background_fill_color = background
    plot.background_fill_alpha = 0.75
    plot.border_fill_color = background

    plot.xaxis.major_label_text_font_style = "bold"
    plot.xaxis.major_label_text_font_size = "12pt"
    plot.xaxis.major_label_orientation = 0.785
    plot.yaxis.major_label_text_font_style = "bold"
    plot.yaxis.major_label_text_font_size = "12pt"

    if "Dollars" in mode:
        plot.yaxis.formatter = NumeralTickFormatter(format="$0.0")

    plot.sizing_mode = "scale_both"
    plot.max_height = height
    plot.max_width = width
    plot.min_height = int(0.25 * height)
    plot.min_width = int(0.25 * width)

    return plot

###############################################################################
# Download
###############################################################################

def download_csv():
    """Generate CSV for currently selected series and mode."""
    selected = series_select.value
    mode = mode_select.value
    suffix = "_index" if "Index" in mode else "_dollars"

    data_list = []
    for name in selected:
        meta = SERIES[name]
        col = meta["col"] + suffix
        for date, value in zip(df.index, df[col].values):
            data_list.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Series": name,
                "Value": round(value, 4),
            })

    export_df = pd.DataFrame(data_list)
    csv_string = export_df.to_csv(index=False)

    b64 = base64.b64encode(csv_string.encode()).decode()
    data_uri = f"data:text/csv;base64,{b64}"

    download_link_div.text = f'''
    <a href="{data_uri}" download="ai_trade_data.csv"
       style="display:inline-block; padding:10px 20px; background-color:#28a745;
              color:white; text-decoration:none; border-radius:4px; font-weight:bold;">
       Click Here to Download CSV
    </a>
    '''

###############################################################################
# Callbacks
###############################################################################

def update_plot(attrname, old, new):
    layout.children[0] = make_plot()

###############################################################################
# Widgets
###############################################################################

series_select = MultiChoice(value=default_series, title="Series",
                            options=series_options, width=325)
series_select.on_change("value", update_plot)

mode_select = Select(value=default_mode, title="Display",
                     options=["Index (2023 = 100)", "Dollars ($B)"], width=325)
mode_select.on_change("value", update_plot)

download_button = Button(label="Generate CSV Download Link",
                         button_type="success", width=325)
download_button.on_click(download_csv)

download_link_div = Div(text="", width=325, height=50)

###############################################################################
# Info divs
###############################################################################

div_title = Div(text="""
<h2 style="margin:0;">AI Trade Tracker</h2>
<p style="margin-top:4px; font-size:13px;">
Interactive visualization of U.S. imports of AI-related products.
Data from the U.S. Census Bureau, classified using an LLM-based tool
that maps HS10 commodity codes to AI data center infrastructure.
</p>
""", width=325)

div_series = Div(text="""
<b>AI Related</b>: All High-relevance products (645 HS10 codes).<br>
<b>Non-AI Related</b>: Low-relevance products.<br>
<b>Subcategories</b>: Compute Hardware, Electrical Power, Networking Telecom,
Cooling HVAC, Building Structure, Fire Safety Security, Specialty Materials.
""", width=325)

div_help = Div(text="""
<b>Download Chart:</b> Use the save icon in the chart toolbar to download as PNG.<br>
<b>Download Data:</b> Click the button to generate a CSV download link.<br>
<b>Legend:</b> Click legend entries to hide/show individual series.
""", width=325)

div_cite = Div(text="""
<p style="font-size:11px; color:#666; margin-top:12px;">
<b>Source:</b> Waugh, Michael E. "Trade in AI-Related Products."
Working Paper, Federal Reserve Bank of Minneapolis, March 2026.
</p>
""", width=325)

###############################################################################
# Layout
###############################################################################

controls = column(div_title, mode_select, series_select, div_series,
                  download_button, download_link_div, div_help, div_cite)

height = int(1.95 * 533)
width = int(1.95 * 675)

layout = row(make_plot(), controls, sizing_mode="scale_height",
             max_height=height, max_width=width,
             min_height=int(0.25 * height), min_width=int(0.25 * width))

curdoc().add_root(layout)
curdoc().title = "AI Trade Tracker"
