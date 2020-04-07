from bokeh.plotting import ColumnDataSource, curdoc, figure
from bokeh.io import output_file, show
from bokeh.layouts import column, row, gridplot
from bokeh.models import Band, DateRangeSlider, DatetimeTickFormatter, HoverTool, NumeralTickFormatter, Select, Span
from bokeh.models.widgets import Tabs, Panel
from bokeh.transform import dodge
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
data = data.sort_values(["country", "date"]).reset_index(drop=True)
data.days_since_100 = data.days_since_100.replace(0, np.nan)
data.days_since_10 = data.days_since_10.replace(0, np.nan)

forecasts = pd.read_csv("plots/data/forecasts.csv", parse_dates=["date"])
forecasts["date_string"] = forecasts.date.dt.strftime("%Y-%0m-%0d")
forecasts["x_col"] = forecasts.date

groups = pd.read_csv("plots/data/country_groups.csv")
groups = list(groups.group.unique())
groups.sort()

countries = list(data.country.unique())
countries.sort()
countries = [x for x in countries if x not in groups]
countries.remove("World")
countries = ["World", "None"] + groups + ["---"] + countries

dates = list(data.date.unique())
dates.sort()

source = ColumnDataSource(data.loc[data.country == "World", :])
source2 = ColumnDataSource(data.loc[data.country == "None", :])
fc_source_cases = ColumnDataSource(forecasts.loc[(forecasts.country == "World") & (forecasts.metric == "cases"), :])
fc_source_deaths = ColumnDataSource(forecasts.loc[(forecasts.country == "World") & (forecasts.metric == "deaths"), :])
fc_source_cases2 = ColumnDataSource(forecasts.loc[(forecasts.country == "None") & (forecasts.metric == "cases"), :])
fc_source_deaths2 = ColumnDataSource(forecasts.loc[(forecasts.country == "None") & (forecasts.metric == "deaths"), :])


# defining plots
def line_plot(source, p, color, country, metric, dodge_value=None, name=None):
    """data = ColumnDataSource, country = country name, p = bokeh figure"""
    p.line('x_col', metric, source=source, color=color, name=name)
    return p

def change_width(source_data, source_2_data, date):
    if date:
        n_points = max([len(source_data), len(source_2_data)])
        width = 24*60*60*10000/n_points
    else:
        n_points = max([len(source_data), len(source_2_data)])
        width = 10.0/n_points
    return width

def bar_plot(source, p, color, country, metric, dodge_value, name=None):
    p.vbar(x=dodge('x_col', value=dodge_value), width=change_width(source.data, source2.data, True), top=metric, source=source, color=color, name='bar')
    return p

def forecast_plot(fc_source, data_source, p, actual_color, fc_color, metric, color_80, color_95):
    p.line("date", metric, source=data_source, color=actual_color, name="actual")
    p.line("date", "point_forecast", source=fc_source, color=fc_color, name="forecast")
    p.line("date", "lo_80", source=fc_source, color=fc_color, name="lo_80", line_alpha=0)
    p.line("date", "hi_80", source=fc_source, color=fc_color, name="hi_80", line_alpha=0)
    p.line("date", "lo_95", source=fc_source, color=fc_color, name="lo_95", line_alpha=0)
    p.line("date", "hi_95", source=fc_source, color=fc_color, name="hi_95", line_alpha=0)
    p.varea(x="date", y1="lo_80", y2="hi_80", fill_alpha=0.5, fill_color=color_80, source=fc_source)
    p.varea(x="date", y1="lo_95", y2="hi_95", fill_alpha=0.5, fill_color=color_95, source=fc_source)
    return p

def add_plot(plot_function, metric, title, y_axis_type, name=None):
    p = figure(tools=["save"], title=title, y_axis_type=y_axis_type)
    plot_function(source, p, "#21618C", select1.value, metric, 0.25, name)
    plot_function(source2, p, "#ff4d4d", select1.value, metric, -0.25, name)
    p.xaxis.major_label_orientation = 3.14/4
    p.renderers.extend([Span(location=0, dimension='width', line_color='black', line_width=1)]) # adding a horizontal black line at 0
    p.yaxis.formatter=NumeralTickFormatter(format=",")

    return p

def add_forecast_plot(fc_source, data_source, p, metric, actual_color, fc_color, color_80, color_95):
    if metric == "confirmed":
        metric_word = "Cases"
    elif metric == "deaths":
        metric_word = "Deaths"
    p = forecast_plot(fc_source=fc_source, data_source=data_source, p=p, actual_color=actual_color, fc_color=fc_color, metric=metric, color_80=color_80, color_95=color_95)
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
    fc_source_cases2.data = forecasts.loc[
        (forecasts.country == new) & 
        (forecasts.metric == "cases") &
        (forecasts.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000))
    , :].reset_index(drop=True)
    fc_source_deaths2.data = forecasts.loc[
        (forecasts.country == new) & 
        (forecasts.metric == "deaths") &
        (forecasts.date >= datetime.datetime.fromtimestamp(date_range.value[0]/1000))
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
    for p in ["confirmedbar", "deathsbar", "smooth_new_casesbar", "smooth_new_deathsbar", "smooth_accel_casesbar", "smooth_accel_deathsbar"]:
        for glyph in plots[p].select({'name': 'bar'}):
            if x_col.value == "Date":
                glyph.glyph.width = change_width(source.data, source2.data, True)
            else:
                glyph.glyph.width = change_width(source.data, source2.data, False)

def x_axis_update_plot(attr, old, new):
    ["Date", "Days since 100th case", "Days since 10th death"]
    x_col = "date"
    if new == "Date":
        x_col = "date"
        for p in all_plots[:-4]:
            p.xaxis.formatter=DatetimeTickFormatter(days=["%d %B %Y"],months=["%d %B %Y"],years=["%d %B %Y"])
    elif new == "Days since 100th case":
        x_col = "days_since_100"
        for p in all_plots[:-4]:
            p.xaxis.formatter=NumeralTickFormatter(format="0,0")
    elif new == "Days since 10th death":
        x_col = "days_since_10"
        for p in all_plots[:-4]: 
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
    for p in ["confirmedbar", "deathsbar", "smooth_new_casesbar", "smooth_new_deathsbar", "smooth_accel_casesbar", "smooth_accel_deathsbar"]:
        for glyph in plots[p].select({'name': 'bar'}):
            if new == "Date":
                glyph.glyph.width = change_width(source.data, source2.data, True)
            else:
                glyph.glyph.width = change_width(source.data, source2.data, False)

def smoothing_update(attr, old, new):
    if new != "0":
        data.smooth_new_cases = data.groupby('country')['new_cases'].rolling(int(new)).mean().reset_index().sort_values(['country', 'level_1'])['new_cases'].reset_index(drop=True)
        data.smooth_new_deaths = data.groupby('country')['new_deaths'].rolling(int(new)).mean().reset_index().sort_values(['country', 'level_1'])['new_deaths'].reset_index(drop=True)
        data.smooth_accel_cases = data.groupby('country')['acceleration_cases'].rolling(int(new)).mean().reset_index().sort_values(['country', 'level_1'])['acceleration_cases'].reset_index(drop=True)
        data.smooth_accel_deaths = data.groupby('country')['acceleration_deaths'].rolling(int(new)).mean().reset_index().sort_values(['country', 'level_1'])['acceleration_deaths'].reset_index(drop=True)
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
plots = {}
metrics = {'confirmed':'Confirmed Cases', 'deaths':'Deaths', 'smooth_new_cases':'New Cases', 'smooth_new_deaths':'New Deaths', 'smooth_accel_cases':'Cases Acceleration', 'smooth_accel_deaths':'Deaths Acceleration'}
axis_types = ['linear', 'log', 'bar']
for metric, title in metrics.items():
    for axis_type in axis_types:
        if axis_type != 'bar':
            # log dotted lines
            if (metric in ['confirmed', 'deaths']) & (axis_type == 'log'):
                p = add_plot(line_plot, metric, title, axis_type, "first")
                if metric == 'confirmed':
                    p.line('x_col', 'double_3_cases', source=source, color='grey', line_dash='dashed', name="double_3_cases")
                    p.line('x_col', 'double_5_cases', source=source, color='grey', line_dash='dashed', name="double_5_cases")
                    p.line('x_col', 'double_10_cases', source=source, color='grey', line_dash='dashed', name="double_10_cases")
                    p.add_tools(
                        HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), (title,'@' + metric + '{,}')], names=["first"]),
                        HoverTool(tooltips=[('Country', '@country'), ("Days since 100th Case", '@days_since_100'), ("Double every 3 days", "@double_3_cases{,}")], names=["double_3_cases"]),
                        HoverTool(tooltips=[('Country', '@country'), ("Days since 100th Case", '@days_since_100'), ("Double every 5 days", "@double_5_cases{,}")], names=["double_5_cases"]),
                        HoverTool(tooltips=[('Country', '@country'), ("Days since 100th Case", '@days_since_100'), ("Double every 10 days", "@double_10_cases{,}")], names=["double_10_cases"])
                    )
                else:
                    p.line('x_col', 'double_3_deaths', source=source, color='grey', line_dash='dashed', name="double_3_deaths")
                    p.line('x_col', 'double_5_deaths', source=source, color='grey', line_dash='dashed', name="double_5_deaths")
                    p.line('x_col', 'double_10_deaths', source=source, color='grey', line_dash='dashed', name="double_10_deaths")
                    p.add_tools(
                        HoverTool(tooltips=[('Country', '@country'), ("Days since 10th Death", '@days_since_10'), ("Date", "@date_string"), (title,'@' + metric + '{,}')], names=["first"]),
                        HoverTool(tooltips=[('Country', '@country'), ("Days since 10th Death", '@days_since_10'), ("Double every 3 days", "@double_3_deaths{,}")], names=["double_3_deaths"]),
                        HoverTool(tooltips=[('Country', '@country'), ("Days since 10th Death", '@days_since_10'), ("Double every 5 days", "@double_5_deaths{,}")], names=["double_5_deaths"]),
                        HoverTool(tooltips=[('Country', '@country'), ("Days since 10th Death", '@days_since_10'), ("Double every 10 days", "@double_10_deaths{,}")], names=["double_10_deaths"])
                    )
                plots[metric + axis_type] = p
            else:
                p = add_plot(line_plot, metric, title, axis_type, "first")
                p.add_tools(HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), (title,'@' + metric + '{,}')], names=["first"]))
                plots[metric + axis_type] = p
        else:
            p = add_plot(bar_plot, metric, title, 'linear', "bar")
            p.add_tools(HoverTool(tooltips=[('Country', '@country'), ("Date", "@date_string"), (title,'@' + metric + '{,}')], names=["bar"]))
            plots[metric + axis_type] = p

# forecast plots
metrics = {'confirmed':'Cases Forecast', 'deaths':'Deaths Forecast'}
for metric, title in metrics.items():
    for axis_type in axis_types[:-1]:
        if metric == 'confirmed':
            sc = fc_source_cases
            sc2 = fc_source_cases2
        else:
            sc = fc_source_deaths
            sc2 = fc_source_deaths2
        p = figure(tools=["save"], title=title, y_axis_type=axis_type)
        p = add_forecast_plot(sc, source, p, metric, actual_color="#21618C", fc_color="#0000ff", color_80="#6666ff", color_95="#ccccff")
        p = add_forecast_plot(sc2, source2, p, metric, actual_color="#ff4d4d", fc_color="#990000", color_80="#ff9999", color_95="#ffcccc")
        plots['forecast_' + metric + axis_type] = p

# log-linear tabs
linear_tab_layout = column(
    row(plots['confirmedlinear'], plots['deathslinear']),
    row(plots['smooth_new_caseslinear'], plots['smooth_new_deathslinear']),
    row(plots['smooth_accel_caseslinear'], plots['smooth_accel_deathslinear']),
    row(plots['forecast_confirmedlinear'], plots['forecast_deathslinear'])
)
log_tab_layout = column(
    row(plots['confirmedlog'], plots['deathslog']),
    row(plots['smooth_new_caseslog'], plots['smooth_new_deathslog']),
    row(plots['smooth_accel_caseslog'], plots['smooth_accel_deathslog']),
    row(plots['forecast_confirmedlog'], plots['forecast_deathslog'])
)
bar_tab_layout = column(
    row(plots['confirmedbar'], plots['deathsbar']),
    row(plots['smooth_new_casesbar'], plots['smooth_new_deathsbar']),
    row(plots['smooth_accel_casesbar'], plots['smooth_accel_deathsbar']),
    row(plots['forecast_confirmedlinear'], plots['forecast_deathslinear'])
)
linear_tab = Panel(child=linear_tab_layout, title='Linear Scale')
log_tab = Panel(child=log_tab_layout, title='Log Scale')
bar_tab = Panel(child=bar_tab_layout, title='Bar Graphs')
tabs = Tabs(tabs=[linear_tab, log_tab, bar_tab])

# initialize plots with date format
all_plots = list(plots.values())
for p in all_plots:
    p.xaxis.formatter=DatetimeTickFormatter(days=["%d %B %Y"],months=["%d %B %Y"],years=["%d %B %Y"])


# final layout
layout = column(
    row(select1, select2),
    row(x_col, smoothing),
    row(date_range),
    row(tabs)
)
curdoc().add_root(layout)
curdoc().title = "COVID-19 Status Report"