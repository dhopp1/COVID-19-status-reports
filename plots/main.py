from bokeh.plotting import figure
from bokeh.plotting import ColumnDataSource, curdoc
from bokeh.io import output_file, show
from bokeh.layouts import column, row
from bokeh.models import DateRangeSlider, DatetimeTickFormatter, HoverTool, NumeralTickFormatter, Select, Span
import pandas as pd
import datetime

# data read
data = pd.read_csv("plots/data/transformed_data.csv", parse_dates=["date"])
data["date_string"] = data.date.dt.strftime("%Y-%0m-%0d")
data.date = [x.to_pydatetime() for x in data.date]
data["x_col"] = data.date
forecasts = pd.read_csv("plots/data/forecasts.csv", parse_dates=["date"])
forecasts["date_string"] = forecasts.date.dt.strftime("%Y-%0m-%0d")
forecasts.date = [x.to_pydatetime() for x in forecasts.date]
forecasts["x_col"] = forecasts.date
countries = list(data.country.unique())
countries.sort()
countries.remove("World")
countries = ["World", "None"] + countries
#dates = list(data.date.dt.strftime("%Y-%0m-%0d").unique())
dates = list(data.date.unique())
dates.sort()

source = ColumnDataSource(data.loc[data.country == "World", :])
source2 = ColumnDataSource(data.loc[data.country == "None", :])


# defining plots
def line_plot(source, p, color, country, metric):
    """data = ColumnDataSource, country = country name, p = bokeh figure"""
    p.line('x_col', metric, source=source, color=color)
    return p

def add_plot(plot_function, metric, title):
    p = figure(tools=["reset", "pan", "zoom_in", "zoom_out","save"], title=title)
    plot_function(source, p, "#21618C", select1.value, metric)
    plot_function(source2, p, "#ff4d4d", select1.value, metric)
    p.add_tools(
        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), (title,f'@{metric}')])
    )
    p.xaxis.major_label_orientation = 3.14/4
    p.renderers.extend([Span(location=0, dimension='width', line_color='black', line_width=1)]) # adding a horizontal black line at 0
    p.left[0].formatter.use_scientific = False
    return p


# selector/dropdown functions
def country_1_update_plot(attr, old, new):
    source.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000)) &
        (data.date <= datetime.datetime.fromtimestamp(date_range.value[1]/1000)) &
        (data.country == new)
    , :].reset_index(drop=True)
    
def country_2_update_plot(attr, old, new):
    source2.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000)) &
        (data.date <= datetime.datetime.fromtimestamp(date_range.value[1]/1000)) &
        (data.country == new)
    , :].reset_index(drop=True)

def date_range_update_plot(attr, old, new):
    source.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(new[0]/1000)) &
        (data.date <= datetime.datetime.fromtimestamp(new[1]/1000)) &
        (data.country == select1.value)
    , :].reset_index(drop=True)
    source2.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(new[0]/1000)) &
        (data.date <= datetime.datetime.fromtimestamp(new[1]/1000)) &
        (data.country == select2.value)
    , :].reset_index(drop=True)

def x_axis_update_plot(attr, old, new):
    ["Date", "Days since 100th case", "Days since 10th death"]
    x_col = "date"
    if new == "Date":
        x_col = "date"
        for p in all_plots:
            p.xaxis.formatter=DatetimeTickFormatter(days=["%d %B %Y"],months=["%d %B %Y"],years=["%d %B %Y"])
    elif new == "Days since 100th case":
        x_col = "days_since_100"
        for p in all_plots:
            p.xaxis.formatter=NumeralTickFormatter(format="0,0")
    elif new == "Days since 10th death":
        x_col = "days_since_10"
        for p in all_plots: 
            p.xaxis.formatter=NumeralTickFormatter(format="0,0")
    data.x_col = data[x_col]
    source.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000)) & 
        (data.date <= datetime.datetime.fromtimestamp(date_range.value[1]/1000)) &
        (data.country == select1.value)
    , :].reset_index(drop=True)
    source2.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000)) & 
        (data.date <= datetime.datetime.fromtimestamp(date_range.value[1]/1000)) &
        (data.country == select2.value)
    , :].reset_index(drop=True)


# dropdowns
select1 = Select(title="Country 1", options=countries, value="World", css_classes=["country_1"])
select1.on_change("value", country_1_update_plot)

select2 = Select(title="Country 2", options=countries, value="None", css_classes=["country_2"])
select2.on_change("value", country_2_update_plot)

x_col = Select(title="X Axis", options=["Date", "Days since 100th case", "Days since 10th death"], value="Date")
x_col.on_change("value", x_axis_update_plot)

date_range = DateRangeSlider(title="Date Range", end=dates[len(dates)-1], start=dates[0], value=(dates[0], dates[len(dates)-1]))
date_range.on_change("value", date_range_update_plot)


# plots
confirmed = add_plot(line_plot, 'confirmed', 'Confirmed Cases')
deaths = add_plot(line_plot, 'deaths', 'Deaths')
new_cases = add_plot(line_plot, 'new_cases', 'New Cases')
new_deaths = add_plot(line_plot, 'new_deaths', 'New Deaths')
case_accel = add_plot(line_plot, 'acceleration_cases', 'Cases Acceleration')
death_accel = add_plot(line_plot, 'acceleration_deaths', 'Deaths Acceleration')
all_plots = [confirmed, deaths, new_cases, new_deaths, case_accel, death_accel]

# initialize plots with date format
for p in all_plots:
    p.xaxis.formatter=DatetimeTickFormatter(days=["%d %B %Y"],months=["%d %B %Y"],years=["%d %B %Y"])


# final layout
layout = column(
    row(select1, select2),
    row(date_range, x_col),
    row(confirmed, deaths),
    row(new_cases, new_deaths),
    row(case_accel, death_accel)
)
curdoc().add_root(layout)
curdoc().title = "COVID-19 Status Report"