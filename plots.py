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

# defining plots
def line_plot(source, p):
    """data = ColumnDataSource, country = country name, p = bokeh figure"""
    
    p.left[0].formatter.use_scientific = False
    p.line('date', 'confirmed', source=source)
    p.xaxis.formatter=DatetimeTickFormatter(
            days=["%d %B %Y"],
            months=["%d %B %Y"],
            years=["%d %B %Y"],
        )
    p.xaxis.major_label_orientation = 3.14/4
    p.add_tools(
        HoverTool(tooltips=[('Country', '@country'), ('Confirmed Cases','@confirmed')])
    )
    return p


def update_plot(attr, old, new):
    source.data = data.loc[data.country == new, :].reset_index(drop=True)

select = Select(title="Country", options=["Italy", "US"], value="Italy")
select.on_change("value", update_plot)

p = figure()
line_plot(source, p)
layout = column(select, p)
curdoc().add_root(layout)

#output_file('test.html')
#show(p)