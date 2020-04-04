from bokeh.plotting import figure
from bokeh.plotting import ColumnDataSource, curdoc
from bokeh.io import output_file, show
from bokeh.layouts import column, row
from bokeh.models import Band, DateRangeSlider, DatetimeTickFormatter, HoverTool, NumeralTickFormatter, Select, Span
import numpy as np
import pandas as pd
import datetime

# data read
data = pd.read_csv("plots/data/transformed_data.csv", parse_dates=["date"])
data["date_string"] = data.date.dt.strftime("%Y-%0m-%0d")
data["x_col"] = data.date
data["smooth_new_cases"] = data.new_cases
data["smooth_new_deaths"] = data.new_deaths
data["smooth_accel_cases"] = data.acceleration_cases
data["smooth_accel_deaths"] = data.acceleration_deaths

forecasts = pd.read_csv("plots/data/forecasts.csv", parse_dates=["date"])
forecasts["date_string"] = forecasts.date.dt.strftime("%Y-%0m-%0d")
forecasts["x_col"] = forecasts.date

countries = list(data.country.unique())
countries.sort()
countries.remove("World")
countries = ["World", "None"] + countries

dates = list(data.date.unique())
dates.sort()

source = ColumnDataSource(data.loc[data.country == "World", :])
source2 = ColumnDataSource(data.loc[data.country == "None", :])
fc_source_cases = ColumnDataSource(forecasts.loc[(forecasts.country == "World") & (forecasts.metric == "cases"), :])
fc_source_deaths = ColumnDataSource(forecasts.loc[(forecasts.country == "World") & (forecasts.metric == "deaths"), :])


# defining plots
def line_plot(source, p, color, country, metric):
    """data = ColumnDataSource, country = country name, p = bokeh figure"""
    p.line('x_col', metric, source=source, color=color)
    return p

def forecast_plot(fc_source, data_source, p, actual_color, fc_color, metric):
    p.line("date", metric, source=data_source, color=actual_color, name="actual")
    p.line("date", "point_forecast", source=fc_source, color=fc_color, name="forecast")
    p.line("date", "lo_80", source=fc_source, color=fc_color, name="lo_80", line_alpha=0)
    p.line("date", "hi_80", source=fc_source, color=fc_color, name="hi_80", line_alpha=0)
    p.line("date", "lo_95", source=fc_source, color=fc_color, name="lo_95", line_alpha=0)
    p.line("date", "hi_95", source=fc_source, color=fc_color, name="hi_95", line_alpha=0)
    p.varea(x="date", y1="lo_80", y2="hi_80", fill_alpha=0.5, fill_color="#6666ff", source=fc_source)
    p.varea(x="date", y1="lo_95", y2="hi_95", fill_alpha=0.5, fill_color="#ccccff", source=fc_source)
    return p

def add_plot(plot_function, metric, title):
    p = figure(tools=["reset", "pan", "zoom_in", "zoom_out","save"], title=title)
    plot_function(source, p, "#21618C", select1.value, metric)
    plot_function(source2, p, "#ff4d4d", select1.value, metric)
    p.add_tools(
        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), (title,'@' + metric + '{,}')])
    )
    p.xaxis.major_label_orientation = 3.14/4
    p.renderers.extend([Span(location=0, dimension='width', line_color='black', line_width=1)]) # adding a horizontal black line at 0
    p.yaxis.formatter=NumeralTickFormatter(format=",")

    return p

def add_forecast_plot(fc_source, data_source, p, metric):
    if metric == "confirmed":
        metric_word = "Cases"
    elif metric == "deaths":
        metric_word = "Deaths"
    p = forecast_plot(fc_source=fc_source, data_source=data_source, p=p, actual_color="#21618C", fc_color="#0000ff", metric=metric)
    p.add_tools(
        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), (f"{metric_word} Actual",'@' + metric + '{,}')], names=["actual"]),
        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), (f"{metric_word} Forecast",'@point_forecast{,}')], names=["forecast"]),
        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), ("Lower 80% Confidence Interval",'@lo_80{,}')], names=["lo_80"]),
        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), ("Upper 80% Confidence Interval",'@hi_80{,}')], names=["hi_80"]),
        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), ("Lower 95% Confidence Interval",'@lo_95{,}')], names=["lo_95"]),
        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), ("Upper 95% Confidence Interval",'@hi_95{,}')], names=["hi_95"]),
    )
    p.xaxis.major_label_orientation = 3.14/4
    p.renderers.extend([Span(location=0, dimension='width', line_color='black', line_width=1)]) # adding a horizontal black line at 0
    p.yaxis.formatter=NumeralTickFormatter(format=",")
    return p


# selector/dropdown functions
def country_1_update_plot(attr, old, new):
    source.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000)) & 
        (data.date <= datetime.datetime.fromtimestamp(date_range.value[1]/1000)) &
        (data.country == new)
    , :].reset_index(drop=True)
    fc_source_cases.data = forecasts.loc[
        (forecasts.country == new) & 
        (forecasts.metric == "cases") &
        (forecasts.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000))
    , :].reset_index(drop=True)
    fc_source_deaths.data = forecasts.loc[
        (forecasts.country == new) & 
        (forecasts.metric == "deaths") &
        (forecasts.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000))
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
        for p in all_plots[:-2]:
            p.xaxis.formatter=DatetimeTickFormatter(days=["%d %B %Y"],months=["%d %B %Y"],years=["%d %B %Y"])
    elif new == "Days since 100th case":
        x_col = "days_since_100"
        for p in all_plots[:-2]:
            p.xaxis.formatter=NumeralTickFormatter(format="0,0")
    elif new == "Days since 10th death":
        x_col = "days_since_10"
        for p in all_plots[:-2]: 
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

def movingaverage (values, window):
    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'valid')
    return sma

# for some reason world smoothing gives weird curves with rolling.mean
def world_fix(metric, smooth_name, window):
    proper = pd.Series(movingaverage(data.loc[data.country == "World", metric], window))
    proper = pd.Series([np.nan] * (window-1)).append(proper)
    proper.index = data.loc[data.country == "World", smooth_name].index
    data.loc[data.country == "World", smooth_name] = proper

def smoothing_update(attr, old, new):
    if new != "0":
        data.smooth_new_cases = data.groupby('country')['new_cases'].rolling(int(new)).mean().reset_index(drop=True)
        data.smooth_new_deaths = data.groupby('country')['new_deaths'].rolling(int(new)).mean().reset_index(drop=True)
        data.smooth_accel_cases = data.groupby('country')['acceleration_cases'].rolling(int(new)).mean().reset_index(drop=True)
        data.smooth_accel_deaths = data.groupby('country')['acceleration_deaths'].rolling(int(new)).mean().reset_index(drop=True)
        if select1.value == "World":
            world_fix("new_cases", "smooth_new_cases", int(new))
            world_fix("new_deaths", "smooth_new_deaths", int(new))
            world_fix("acceleration_cases", "smooth_accel_cases", int(new))
            world_fix("acceleration_deaths", "smooth_accel_deaths", int(new))
    else:
        data["smooth_new_cases"] = data.new_cases
        data["smooth_new_deaths"] = data.new_deaths
        data["smooth_accel_cases"] = data.acceleration_cases
        data["smooth_accel_deaths"] = data.acceleration_deaths
    source.data =  data.loc[
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

date_range = DateRangeSlider(title="Date Range", end=dates[len(dates)-1], start=dates[0], value=(
    dates[0].astype('datetime64[s]').astype('int') * 1000,
    dates[len(dates)-1].astype('datetime64[s]').astype('int') * 1000 
))
date_range.on_change("value", date_range_update_plot)

smoothing = Select(title="# Days for moving average smoothing", options=["0","3","5", "7", "9"], value="0")
smoothing.on_change("value", smoothing_update)

# plots
confirmed = add_plot(line_plot, 'confirmed', 'Confirmed Cases')
deaths = add_plot(line_plot, 'deaths', 'Deaths')
new_cases = add_plot(line_plot, 'smooth_new_cases', 'New Cases')
new_deaths = add_plot(line_plot, 'smooth_new_deaths', 'New Deaths')
case_accel = add_plot(line_plot, 'smooth_accel_cases', 'Cases Acceleration')
death_accel = add_plot(line_plot, 'smooth_accel_deaths', 'Deaths Acceleration')

#forecast plots
cases_fc_plot = figure(tools=["reset", "pan", "zoom_in", "zoom_out","save"], title="Cases Forecast")
cases_fc_plot = add_forecast_plot(fc_source_cases, source, cases_fc_plot, "confirmed")
deaths_fc_plot = figure(tools=["reset", "pan", "zoom_in", "zoom_out","save"], title="Deaths Forecast")
deaths_fc_plot = add_forecast_plot(fc_source_deaths, source, deaths_fc_plot, "deaths")

# initialize plots with date format
all_plots = [confirmed, deaths, new_cases, new_deaths, case_accel, death_accel, cases_fc_plot, deaths_fc_plot]
for p in all_plots:
    p.xaxis.formatter=DatetimeTickFormatter(days=["%d %B %Y"],months=["%d %B %Y"],years=["%d %B %Y"])


# final layout
layout = column(
    row(select1, select2),
    row(date_range),
    row(x_col, smoothing),
    row(confirmed, deaths),
    row(new_cases, new_deaths),
    row(case_accel, death_accel),
    row(cases_fc_plot, deaths_fc_plot)
)
curdoc().add_root(layout)
curdoc().title = "COVID-19 Status Report"