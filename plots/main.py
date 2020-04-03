from bokeh.plotting import figure
from bokeh.plotting import ColumnDataSource, curdoc
from bokeh.io import output_file, show
from bokeh.layouts import column, row
from bokeh.models import DatetimeTickFormatter, HoverTool, Select
import pandas as pd

# data read
data = pd.read_csv("data/transformed_data.csv")
data.date = pd.to_datetime(data.date)
forecasts = pd.read_csv("data/forecasts.csv")
forecasts.date = pd.to_datetime(forecasts.date)

source = ColumnDataSource(data.loc[data.country == "Italy", :])
source2 = ColumnDataSource(data.loc[data.country == "US", :])

# defining plots
def line_plot(source, p, color, country):
    """data = ColumnDataSource, country = country name, p = bokeh figure"""
    
    p.left[0].formatter.use_scientific = False
    p.line('date', 'confirmed', source=source, color=color)
    p.xaxis.formatter=DatetimeTickFormatter(
            days=["%d %B %Y"],
            months=["%d %B %Y"],
            years=["%d %B %Y"],
        )
    p.xaxis.major_label_orientation = 3.14/4
    return p


def country_1_update_plot(attr, old, new):
    source.data = data.loc[data.country == new, :].reset_index(drop=True)
    
def country_2_update_plot(attr, old, new):
    source2.data = data.loc[data.country == new, :].reset_index(drop=True)

select1 = Select(title="Country 1", options=["Italy", "US"], value="Italy")
select1.on_change("value", country_1_update_plot)

select2 = Select(title="Country 2", options=["Italy", "US"], value="US")
select2.on_change("value", country_2_update_plot)

p = figure(tools=["reset", "pan", "zoom_in", "zoom_out","save"])
line_plot(source, p, 'blue', select1.value)
line_plot(source2, p, 'orange', select2.value)
p.add_tools(
        HoverTool(tooltips=[('Country', '@country'), ('Confirmed Cases','@confirmed')])
    )

layout = column(row(select1, select2), p, name="line_plot")
curdoc().add_root(layout)
curdoc().title = "COVID-19 Status Report"