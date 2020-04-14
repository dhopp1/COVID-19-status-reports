from bokeh.models.annotations import Title
from bokeh.plotting import ColumnDataSource, curdoc, figure
from bokeh.io import output_file, show
from bokeh.layouts import column, row, gridplot, Spacer
from bokeh.models import (
    Band,
    DateRangeSlider,
    DatetimeTickFormatter,
    Div,
    HoverTool,
    NumeralTickFormatter,
    Select,
    Span,
)
from bokeh.models.widgets import (
    Tabs,
    Panel,
    DataTable,
    TableColumn,
    HTMLTemplateFormatter,
)
from bokeh.transform import dodge
import numpy as np
import pandas as pd
import datetime

import source.aesthetics as aesthetics


# data read
data = pd.read_csv("plots/data/transformed_data.csv", parse_dates=["date"])
data["date_string"] = data.date.dt.strftime("%Y-%0m-%0d")
data["x_col"] = data.date
data["metric"] = data.confirmed
data["metric_1st_der"] = data.new_cases
data["metric_2nd_der"] = data.acceleration_cases
data["smooth_1st_der"] = data.new_cases
data["smooth_2nd_der"] = data.acceleration_cases
data["double_3"] = data.double_3_cases
data["double_5"] = data.double_5_cases
data["double_10"] = data.double_10_cases
data["new_active_cases"] = data.new_cases - data.new_deaths - data.new_recoveries
data["acceleration_active_cases"] = data.new_active_cases.diff(1)
data["acceleration_recoveries"] = data.new_recoveries.diff(1)
data = data.sort_values(["country", "date"]).reset_index(drop=True)
data.days_since_100 = data.days_since_100.replace(0, np.nan)
data.days_since_10 = data.days_since_10.replace(0, np.nan)

forecasts = pd.read_csv("plots/data/forecasts.csv", parse_dates=["date"])
forecasts["date_string"] = forecasts.date.dt.strftime("%Y-%0m-%0d")
forecasts["x_col"] = forecasts.date

acceleration_data = pd.read_csv("plots/data/acceleration_data.csv")

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

metric_options = ["Cases", "Deaths", "Active Cases", "Recovered Cases"]
metric_options_count = {"Cases":"confirmed", "Deaths":"deaths", "Active Cases":"active_cases", "Recovered Cases":"recovered"}
metric_options_1st_der = {"Cases":"new_cases", "Deaths":"new_deaths", "Active Cases":"new_active_cases", "Recovered Cases":"new_recoveries"}
metric_options_2nd_der = {"Cases":"acceleration_cases", "Deaths":"acceleration_deaths", "Active Cases":"acceleration_active_cases", "Recovered Cases":"acceleration_recoveries"}
metric_forecast_name = {"Cases":"cases", "Deaths":"deaths", "Active Cases":"active_cases", "Recovered Cases":"recovered"}

# data for data table
templatebold = """
<strong style="font-size: 115%">
<%= value %>
</strong>
"""
templatenormal = """
<em style="font-size: 115%">
<%= value %>
</em>
"""


def gen_table(country1, country2):
    df1 = data.loc[data.country == country1, :].reset_index(drop=True)
    df2 = data.loc[data.country == country2, :].reset_index(drop=True)
    overview_df_names = [
        "Country/Region",
        "Data as of",
        "Confirmed Cases",
        "Recovered Cases",
        "Active Cases",
        "Deaths",
        "Death Rate",
        "New Cases Yesterday",
        "Deaths Yesterday",
    ]
    if len(df1) > 0:
        overview_df_values1 = [
            country1,
            max(df1.date).strftime("%Y-%m-%d"),
            "{:,.0f}".format(max(df1.confirmed)),
            "{:,.0f}".format(max(df1.recovered)),
            "{:,.0f}".format(df1.active_cases[len(df1)-1]),
            "{:,.0f}".format(max(df1.deaths)),
            "{:.2f}".format(df1.death_rate[len(df1) - 1] * 100) + "%",
            "{:,.0f}".format(df1.new_cases[len(df1) - 1]),
            "{:,.0f}".format(df1.new_deaths[len(df1) - 1]),
        ]
    else:
        overview_df_values1 = ["", "", "", "", "", "", "", "", ""]
    if len(df2) > 0:
        overview_df_values2 = [
            country2,
            max(df2.date).strftime("%Y-%m-%d"),
            "{:,.0f}".format(max(df2.confirmed)),
            "{:,.0f}".format(max(df2.recovered)),
            "{:,.0f}".format(df2.active_cases[len(df2)-1]),
            "{:,.0f}".format(max(df2.deaths)),
            "{:.2f}".format(df2.death_rate[len(df2) - 1] * 100) + "%",
            "{:,.0f}".format(df2.new_cases[len(df2) - 1]),
            "{:,.0f}".format(df2.new_deaths[len(df2) - 1]),
        ]
    else:
        overview_df_values2 = ["", "", "", "", "", "", "", "", ""]
    overview_df = pd.DataFrame(
        {
            "name": overview_df_names,
            "country1": overview_df_values1,
            "country2": overview_df_values2,
        }
    )
    table_dict = dict(overview_df)
    return table_dict


acceleration_dict = dict(acceleration_data)


# initializing data sources
source_table = ColumnDataSource(gen_table("World", "None"))
columns = [
    TableColumn(
        field="name", title="", formatter=HTMLTemplateFormatter(template=templatebold)
    ),
    TableColumn(
        field="country1",
        title="",
        formatter=HTMLTemplateFormatter(template=templatenormal),
    ),
    TableColumn(
        field="country2",
        title="",
        formatter=HTMLTemplateFormatter(template=templatenormal),
    ),
]
data_table = DataTable(
    source=source_table, columns=columns, width=600, height=250, row_height=25
)

# acceleration overview table source
source_acceleration_table = ColumnDataSource(acceleration_dict)
columns = [
    TableColumn(
        field="Country/Region",
        title="Country/Region",
        formatter=HTMLTemplateFormatter(template=templatebold),
        width=175,
    ),
    TableColumn(
        field="Confirmed Cases",
        title="Confirmed Cases",
        formatter=HTMLTemplateFormatter(template=templatenormal),
        width=125,
    ),
    TableColumn(
        field="Cases 5 Days Ago",
        title="Cases 5 Days Ago",
        formatter=HTMLTemplateFormatter(template=templatenormal),
        width=130,
    ),
    TableColumn(
        field="% Increase in 5 Days",
        title="% Increase in 5 Days",
        formatter=HTMLTemplateFormatter(template=templatenormal),
        width=145,
    ),
    TableColumn(
        field="Acceleration of Last 5 Days",
        title="Acceleration of Last 5 Days",
        formatter=HTMLTemplateFormatter(template=templatenormal),
        width=180,
    ),
    TableColumn(
        field="Recovered Cases",
        title="Recovered Cases",
        formatter=HTMLTemplateFormatter(template=templatenormal),
        width=180,
    ),
    TableColumn(
        field="Active Cases",
        title="Active Cases",
        formatter=HTMLTemplateFormatter(template=templatenormal),
        width=180,
    ),
    TableColumn(
        field="Deaths",
        title="Deaths",
        formatter=HTMLTemplateFormatter(template=templatenormal),
        width=85,
    ),
    TableColumn(
        field="Death Rate",
        title="Death Rate (%)",
        formatter=HTMLTemplateFormatter(template=templatenormal),
        width=110,
    ),
]
acceleration_table = DataTable(
    source=source_acceleration_table,
    columns=columns,
    width=600,
    height=600,
    fit_columns=False,
    index_width=0,
    row_height=25,
)

# other data sources
source = ColumnDataSource(data.loc[data.country == "World", :])
source2 = ColumnDataSource(data.loc[data.country == "None", :])
fc_source = ColumnDataSource(
    forecasts.loc[(forecasts.country == "World") & (forecasts.metric == "cases"), :]
)
fc_source2 = ColumnDataSource(
    forecasts.loc[(forecasts.country == "None") & (forecasts.metric == "cases"), :]
)


# defining plots
def line_plot(source, p, color, country, metric, dodge_value=None, name=None):
    """data = ColumnDataSource, country = country name, p = bokeh figure"""
    p.line("x_col", metric, source=source, color=color, name=name, width=2)
    return p


def change_width(source_data, source_2_data, date):
    if date:
        n_points = max([len(source_data), len(source_2_data)])
        width = 24 * 60 * 60 * 10000 / n_points
    else:
        n_points = max([len(source_data), len(source_2_data)])
        width = 10.0 / n_points
    return width


def bar_plot(source, p, color, country, metric, dodge_value, name=None):
    p.vbar(
        x=dodge("x_col", value=dodge_value),
        width=change_width(source.data, source2.data, True),
        top=metric,
        source=source,
        color=color,
        name="bar",
    )
    return p


def forecast_plot(
    fc_source, data_source, p, actual_color, fc_color, metric, color_80, color_95
):
    p.line("date", metric, source=data_source, color=actual_color, name="actual", width=2)
    p.line("date", "point_forecast", source=fc_source, color=fc_color, name="forecast", width=2)
    p.line(
        "date", "lo_80", source=fc_source, color=fc_color, name="lo_80", line_alpha=0
    )
    p.line(
        "date", "hi_80", source=fc_source, color=fc_color, name="hi_80", line_alpha=0
    )
    p.line(
        "date", "lo_95", source=fc_source, color=fc_color, name="lo_95", line_alpha=0
    )
    p.line(
        "date", "hi_95", source=fc_source, color=fc_color, name="hi_95", line_alpha=0
    )
    p.varea(
        x="date",
        y1="lo_80",
        y2="hi_80",
        fill_alpha=0.5,
        fill_color=color_80,
        source=fc_source,
    )
    p.varea(
        x="date",
        y1="lo_95",
        y2="hi_95",
        fill_alpha=0.5,
        fill_color=color_95,
        source=fc_source,
    )
    return p

title_text_font_size='14pt'
axis_text_font_size='11pt'

def add_plot(plot_function, metric, title, y_axis_type, name=None):
    p = figure(tools=["save"], title=title, y_axis_type=y_axis_type)
    p.xaxis.major_label_text_font_size = axis_text_font_size
    p.yaxis.major_label_text_font_size = axis_text_font_size
    p.title.text_font_size = title_text_font_size
    plot_function(source, p, aesthetics.country_1_color, select1.value, metric, 0.25, name)
    plot_function(source2, p, aesthetics.country_2_color, select1.value, metric, -0.25, name)
    p.xaxis.major_label_orientation = 3.14 / 4
    p.renderers.extend(
        [Span(location=0, dimension="width", line_color="black", line_width=1)]
    )  # adding a horizontal black line at 0
    p.yaxis.formatter = NumeralTickFormatter(format=",")

    return p


def add_forecast_plot(
    fc_source, data_source, p, metric, actual_color, fc_color, color_80, color_95
):
    p = forecast_plot(
        fc_source=fc_source,
        data_source=data_source,
        p=p,
        actual_color=actual_color,
        fc_color=fc_color,
        metric=metric,
        color_80=color_80,
        color_95=color_95,
    )
    p.add_tools(
        HoverTool(
            tooltips=[
                ("Country/Region", "@country"),
                ("Date", "@date_string"),
                (f"Actual", "@" + metric + "{,.00}"),
            ],
            names=["actual"],
            mode=hover_mode
        ),
        HoverTool(
            tooltips=[
                ("Country/Region", "@country"),
                ("Date", "@date_string"),
                (f"Forecast", "@point_forecast{,.00}"),
            ],
            names=["forecast"],
            mode=hover_mode
        ),
        HoverTool(
            tooltips=[
                ("Country/Region", "@country"),
                ("Date", "@date_string"),
                ("Lower 80% Confidence Interval", "@lo_80{,.00}"),
            ],
            names=["lo_80"],
            mode="mouse"
        ),
        HoverTool(
            tooltips=[
                ("Country/Region", "@country"),
                ("Date", "@date_string"),
                ("Upper 80% Confidence Interval", "@hi_80{,.00}"),
            ],
            names=["hi_80"],
            mode="mouse"
        ),
        HoverTool(
            tooltips=[
                ("Country/Region", "@country"),
                ("Date", "@date_string"),
                ("Lower 95% Confidence Interval", "@lo_95{,.00}"),
            ],
            names=["lo_95"],
            mode="mouse"
        ),
        HoverTool(
            tooltips=[
                ("Country/Region", "@country"),
                ("Date", "@date_string"),
                ("Upper 95% Confidence Interval", "@hi_95{,.00}"),
            ],
            names=["hi_95"],
            mode="mouse"
        ),
    )
    p.xaxis.major_label_text_font_size = axis_text_font_size
    p.yaxis.major_label_text_font_size = axis_text_font_size
    p.title.text_font_size = title_text_font_size
    p.xaxis.major_label_orientation = 3.14 / 4
    p.renderers.extend(
        [Span(location=0, dimension="width", line_color="black", line_width=1)]
    )  # adding a horizontal black line at 0
    p.yaxis.formatter = NumeralTickFormatter(format=",")
    return p


# selector/dropdown functions
def country_1_update_plot(attr, old, new):
    source.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000))
        & (data.date <= datetime.datetime.fromtimestamp(date_range.value[1] / 1000))
        & (data.country == new),
        :,
    ].reset_index(drop=True)
    fc_source.data = forecasts.loc[
        (forecasts.country == new)
        & (forecasts.metric == metric_forecast_name[metric_dropdown.value])
        & (
            forecasts.date
            >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000)
        ),
        :,
    ].reset_index(drop=True)
    source_table.data = gen_table(new, select2.value)


def country_2_update_plot(attr, old, new):
    source2.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000))
        & (data.date <= datetime.datetime.fromtimestamp(date_range.value[1] / 1000))
        & (data.country == new),
        :,
    ].reset_index(drop=True)
    if x_col.value == "Date":
        source2.data["x_col"] = source2.data["x_col"] + pd.Timedelta(hours=12)
    fc_source2.data = forecasts.loc[
        (forecasts.country == new)
        & (forecasts.metric == metric_forecast_name[metric_dropdown.value])
        & (
            forecasts.date
            >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000)
        ),
        :,
    ].reset_index(drop=True)
    source_table.data = gen_table(select1.value, new)


def date_range_update_plot(attr, old, new):
    source.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(new[0] / 1000))
        & (data.date <= datetime.datetime.fromtimestamp(new[1] / 1000))
        & (data.country == select1.value),
        :,
    ].reset_index(drop=True)
    source2.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(new[0] / 1000))
        & (data.date <= datetime.datetime.fromtimestamp(new[1] / 1000))
        & (data.country == select2.value),
        :,
    ].reset_index(drop=True)
    for p in [
        "metricbar",
        "smooth_1st_derbar",
        "smooth_2nd_derbar",
    ]:
        for glyph in plots[p].select({"name": "bar"}):
            if x_col.value == "Date":
                glyph.glyph.width = change_width(source.data, source2.data, True)
            else:
                glyph.glyph.width = change_width(source.data, source2.data, False)
    if x_col.value == "Date":
        source2.data["x_col"] = source2.data["x_col"] + pd.Timedelta(hours=12)


def x_axis_update_plot(attr, old, new):
    ["Date", "Days since 100th case", "Days since 10th death"]
    x_col = "date"
    if new == "Date":
        x_col = "date"
        for p in all_plots[:-4]:
            p.xaxis.formatter = DatetimeTickFormatter(
                days=["%d %b"], months=["%d %b"], years=["%d %b"]
            )
    elif new == "Days since 100th case":
        x_col = "days_since_100"
        for p in all_plots[:-4]:
            p.xaxis.formatter = NumeralTickFormatter(format="0,0")
    elif new == "Days since 10th death":
        x_col = "days_since_10"
        for p in all_plots[:-4]:
            p.xaxis.formatter = NumeralTickFormatter(format="0,0")
    data.x_col = data[x_col]
    source.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000))
        & (data.date <= datetime.datetime.fromtimestamp(date_range.value[1] / 1000))
        & (data.country == select1.value),
        :,
    ].reset_index(drop=True)
    source2.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000))
        & (data.date <= datetime.datetime.fromtimestamp(date_range.value[1] / 1000))
        & (data.country == select2.value),
        :,
    ].reset_index(drop=True)
    for p in [
        "metricbar",
        "smooth_1st_derbar",
        "smooth_2nd_derbar"
    ]:
        for glyph in plots[p].select({"name": "bar"}):
            if new == "Date":
                glyph.glyph.width = change_width(source.data, source2.data, True)
            else:
                glyph.glyph.width = change_width(source.data, source2.data, False)
    if new == "Date":
        source2.data["x_col"] = source2.data["x_col"] + pd.Timedelta(hours=12)


def smoothing_helper(smoothing_days):
    if (smoothing_days != "0") & (smoothing_days != 0):
        data.smooth_1st_der = (
            data.groupby("country")["metric_1st_der"]
            .rolling(int(smoothing_days))
            .mean()
            .reset_index()
            .sort_values(["country", "level_1"])["metric_1st_der"]
            .reset_index(drop=True)
        )
        data.smooth_2nd_der = (
            data.groupby("country")["metric_2nd_der"]
            .rolling(int(smoothing_days))
            .mean()
            .reset_index()
            .sort_values(["country", "level_1"])["metric_2nd_der"]
            .reset_index(drop=True)
        )
    else:
        data["smooth_1st_der"] = data.metric_1st_der
        data["smooth_2nd_der"] = data.metric_2nd_der
    source.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000))
        & (data.date <= datetime.datetime.fromtimestamp(date_range.value[1] / 1000))
        & (data.country == select1.value),
        :,
    ].reset_index(drop=True)
    source2.data = data.loc[
        (data.date >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000))
        & (data.date <= datetime.datetime.fromtimestamp(date_range.value[1] / 1000))
        & (data.country == select2.value),
        :,
    ].reset_index(drop=True)

def smoothing_update(attr, old, new):
    smoothing_helper(new)
    if x_col.value == "Date":
        source2.data["x_col"] = source2.data["x_col"] + pd.Timedelta(hours=12)

def rename_plots(metric, pop_type):
    if pop_type == "Per 100k Population":
        suffix = " (per 100k population)"
    else:
        suffix = ""
    plots["smooth_2nd_derlinear"].title.text = metric + " Acceleration" + suffix
    plots["metriclog"].title.text = "Cumulative " + metric + suffix
    for p in [
            "metriclinear",
            "smooth_1st_derlinear",
            "smooth_2nd_derlinear"
            "metriclog",
            "smooth_1st_derlog",
            "smooth_2nd_derlog",
            "metricbar",
            "smooth_1st_derbar",
            "smooth_2nd_derbar",
            "forecast_metriclinear",
            "forecast_metriclog"
        ]:
            if p in ["metriclinear", "metriclog", "metricbar"]:
                plots[p].title.text = "Cumulative " + metric + suffix
            elif p in ["smooth_1st_derlinear", "smooth_1st_derlog", "smooth_1st_derbar"]:
                plots[p].title.text = "New Daily " + metric + suffix
            elif p in ["smooth_2nd_derlinear", "smooth_2nd_derlog", "smooth_2nd_derbar"]:
                plots[p].title.text = metric + " Acceleration" + suffix
            elif p == "forecast_metriclinear":
                plots[p].title.text = "Forecast " + metric + " (linear scale)" + suffix
            elif p == "forecast_metriclog":
                plots[p].title.text = "Forecast " + metric + " (log scale)" + suffix

def metric_update(attr, old, new):
    col_count = metric_options_count[new]
    col_1st_der = metric_options_1st_der[new]
    col_2nd_der = metric_options_2nd_der[new]
    data["metric"] = data[col_count]
    data["metric_1st_der"] = data[col_1st_der]
    data["metric_2nd_der"] = data[col_2nd_der]
    if new == "Cases":
        data["double_3"] = data.double_3_cases
        data["double_5"] = data.double_5_cases
        data["double_10"] = data.double_10_cases
    elif new == "Deaths":
        data["double_3"] = data.double_3_deaths
        data["double_5"] = data.double_5_deaths
        data["double_10"] = data.double_10_deaths
    else:
        data["double_3"] = 0
        data["double_5"] = 0
        data["double_10"] = 0
    fc_source.data = forecasts.loc[
        (forecasts.country == select1.value)
        & (forecasts.metric == metric_forecast_name[metric_dropdown.value])
        & (
            forecasts.date
            >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000)
        ),
        :,
    ].reset_index(drop=True)
    fc_source2.data = forecasts.loc[
        (forecasts.country == select2.value)
        & (forecasts.metric == metric_forecast_name[metric_dropdown.value])
        & (
            forecasts.date
            >= datetime.datetime.fromtimestamp(date_range.value[0] / 1000)
        ),
        :,
    ].reset_index(drop=True)
    rename_plots(metric_dropdown.value, pop_dropdown.value)
    smoothing_helper(smoothing.value)
    if x_col.value == "Date":
        source2.data["x_col"] = source2.data["x_col"] + pd.Timedelta(hours=12)

def make_per_100(df, column, round=False):
    if round:
        df[column] = ((df[column] / df["population"]) * 100000).round(2)
    else:
        df[column] = ((df[column] / df["population"]) * 100000)
def make_total(df, column, round=False):
    if round:
        df[column] = (df[column] * (df["population"]/100000)).round(2)
    else:
        df[column] = (df[column] * (df["population"]/100000))
def pop_update_helper(new):
    # graphs
    for src in [source, source2]:
        for col in ["confirmed", "deaths", "metric", "metric_1st_der", "metric_2nd_der", "smooth_1st_der", "smooth_2nd_der", "double_3", "double_5", "double_10"]:
            if new == "Total Numbers":
                make_total(src.data, col)
            else:
                make_per_100(src.data, col)
    # forecasts
    for src in [fc_source, fc_source2]:
        for col in ["point_forecast", "lo_80", "hi_80", "lo_95", "hi_95"]:
            if new == "Total Numbers":
                make_total(src.data, col)
            else:
                make_per_100(src.data, col)
    for col in ["point_forecast", "lo_80", "hi_80", "lo_95", "hi_95"]:
        if new == "Total Numbers":
            make_total(forecasts, col)
        else:
            make_per_100(forecasts, col)
    # overview table
    for col in data.columns:
        if not(col in ["date", "country", "death_rate", "days_since_100", "days_since_10", "population", "date_string", "x_col"]):
            if new == "Total Numbers":
                make_total(data, col)
            else:
                make_per_100(data, col)
    source_table.data = gen_table(select1.value, select2.value)
    # acceleration table
    acceleration_data = pd.read_csv("plots/data/acceleration_data.csv") 
    for col in ["Confirmed Cases", "Cases 5 Days Ago", "Recovered Cases", "Active Cases", "Deaths"]:
        if new != "Total Numbers":
            make_per_100(acceleration_data, col, True)
    source_acceleration_table.data = dict(acceleration_data)
def pop_update(attr, old, new):
    pop_update_helper(new)
    rename_plots(metric_dropdown.value, pop_dropdown.value)

# dropdowns
select1 = Select(
    title="Country/Region 1",
    options=countries,
    value="World",
    css_classes=["country_1"],
)
select1.on_change("value", country_1_update_plot)

select2 = Select(
    title="Country/Region 2", options=countries, value="None", css_classes=["country_2"]
)
select2.on_change("value", country_2_update_plot)

x_col = Select(
    title="X Axis [1]",
    options=["Date", "Days since 100th case", "Days since 10th death"],
    value="Date",
)
x_col.on_change("value", x_axis_update_plot)

date_range = DateRangeSlider(
    title="Date Range",
    end=dates[len(dates) - 1],
    start=dates[0],
    value=(
        dates[0].astype("datetime64[s]").astype("int") * 1000,
        dates[len(dates) - 1].astype("datetime64[s]").astype("int") * 1000,
    ),
)
date_range.on_change("value", date_range_update_plot)

smoothing = Select(
    title="# Days for moving average smoothing [4]",
    options=["0", "3", "5", "7", "9"],
    value="0",
)
smoothing.on_change("value", smoothing_update)

metric_dropdown = Select(
    title="Metric [2]",
    options=metric_options,
    value="Cases"
)
metric_dropdown.on_change("value", metric_update)

pop_dropdown = Select(
    title="Total/Per 100k Population [3]",
    options=["Total Numbers", "Per 100k Population"],
    value="Total Numbers"
)
pop_dropdown.on_change("value", pop_update)


# plots
hover_mode = "mouse"
plots = {}
metrics = {
    "metric": "Cumulative",
    "smooth_1st_der": "New per Day",
    "smooth_2nd_der": "Acceleration"
}
axis_types = ["linear", "log", "bar"]
for metric, title in metrics.items():
    for axis_type in axis_types:
        if axis_type != "bar":
            # log dotted lines
            if (metric_dropdown.value in ["Cases", "Deaths"]) & (axis_type == "log"):
                p = add_plot(line_plot, metric, title, axis_type, "first")
                p.add_tools(
                    HoverTool(
                        tooltips=[
                            ("Country/Region", "@country"),
                            ("Date", "@date_string"),
                            (title, "@" + metric + "{,.00}"),
                        ],
                        names=["first"],
                        mode=hover_mode
                    ),
                )
                # only add doubling lines if it's cases or deaths
                if metric == "metric":
                    p.line(
                        "x_col",
                        "double_3",
                        source=source,
                        color="grey",
                        line_dash="dashed",
                        name="double_3",
                    )
                    p.line(
                        "x_col",
                        "double_5",
                        source=source,
                        color="grey",
                        line_dash="dashed",
                        name="double_5",
                    )
                    p.line(
                        "x_col",
                        "double_10",
                        source=source,
                        color="grey",
                        line_dash="dashed",
                        name="double_10",
                    )
                    p.add_tools(
                        HoverTool(
                            tooltips=[
                                ("Country/Region", "@country"),
                                ("Double every 3 days", "@double_3{,.00}"),
                            ],
                            names=["double_3"],
                            mode="mouse"
                        ),
                        HoverTool(
                            tooltips=[
                                ("Country/Region", "@country"),
                                ("Double every 5 days", "@double_5{,.00}"),
                            ],
                            names=["double_5"],
                            mode="mouse"
                        ),
                        HoverTool(
                            tooltips=[
                                ("Country/Region", "@country"),
                                ("Double every 10 days", "@double_10{,.00}"),
                            ],
                            names=["double_10"],
                            mode="mouse"
                        ),
                    )
                plots[metric + axis_type] = p
            else:
                p = add_plot(line_plot, metric, title, axis_type, "first")
                p.add_tools(
                    HoverTool(
                        tooltips=[
                            ("Country/Region", "@country"),
                            ("Date", "@date_string"),
                            (title, "@" + metric + "{,.00}"),
                        ],
                        names=["first"],
                        mode=hover_mode
                    )
                )
                plots[metric + axis_type] = p
        else:
            p = add_plot(bar_plot, metric, title, "linear", "bar")
            p.add_tools(
                HoverTool(
                    tooltips=[
                        ("Country/Region", "@country"),
                        ("Date", "@date_string"),
                        (title, "@" + metric + "{,.00}"),
                    ],
                    names=["bar"],
                    mode=hover_mode
                )
            )
            plots[metric + axis_type] = p

# forecast plots
metrics = {"metric": "Metric Title"}
for metric, title in metrics.items():
    for axis_type in axis_types[:-1]:
        sc = fc_source
        sc2 = fc_source2
        if axis_type == "linear":
            fc_title = title + " (linear scale)"
        else:
            fc_title = title + " (log scale)"
        p = figure(tools=["save"], title=fc_title, y_axis_type=axis_type)
        p = add_forecast_plot(
            sc,
            source,
            p,
            metric,
            actual_color=aesthetics.country_1_color,
            fc_color=aesthetics.country_1_fc_color,
            color_80=aesthetics.country_1_80_color,
            color_95=aesthetics.country_1_95_color,
        )
        p = add_forecast_plot(
            sc2,
            source2,
            p,
            metric,
            actual_color=aesthetics.country_2_color,
            fc_color=aesthetics.country_2_fc_color,
            color_80=aesthetics.country_2_80_color,
            color_95=aesthetics.country_2_95_color,
        )
        plots["forecast_" + metric + axis_type] = p

# log-linear tabs
line_div_text = """
<h4>Explanation: README [5]</h4>
"""

# initialize plot names
rename_plots("Cases", pop_dropdown.value)

linear_tab_layout = column(
    row(Div(text=line_div_text, width=600)),
    row(plots["metriclinear"]),
    row(plots["smooth_1st_derlinear"]),
    row(plots["smooth_2nd_derlinear"]),
)
log_div_text = """
<h4>Explanation: README [6]</h4>
"""
log_tab_layout = column(
    row(Div(text=log_div_text, width=600)),
    row(plots["metriclog"]),
    row(plots["smooth_1st_derlog"]),
    row(plots["smooth_2nd_derlog"]),
)
bar_tab_layout = column(
    row(Div(text=line_div_text, width=600)),
    row(plots["metricbar"]),
    row(plots["smooth_1st_derbar"]),
    row(plots["smooth_2nd_derbar"]),
)
forecast_text = """
<h4>Explanation: README [7]</h4>
"""
forecast_div = Div(text=forecast_text, width=600)
forecast_tab_layout = column(
    row(forecast_div),
    row(plots["forecast_metriclinear"]),
    row(plots["forecast_metriclog"]),
)
linear_tab = Panel(child=linear_tab_layout, title="Linear Scale")
log_tab = Panel(child=log_tab_layout, title="Log Scale")
bar_tab = Panel(child=bar_tab_layout, title="Bar Graphs")
forecast_tab = Panel(child=forecast_tab_layout, title="Forecasts")
accel_div_text = """
<h4>Explanation: README [8]</h4>
"""
accel_div = Div(text=accel_div_text, width=600)
acceleration_tab = Panel(
    child=column(accel_div, acceleration_table), title="Overview"
)
notes_text = """
<h4>About</h4>
<p>
This page uses data from <a href="https://github.com/CSSEGISandData/COVID-19">Johns Hopkins CSSE</a> and the Robert Koch Institute via <a href="https://npgeo-corona-npgeo-de.hub.arcgis.com/datasets/dd4580c810204019a7b8eb3e0b329dd6_0">this</a> api (for German Bundesländer data) to create charts on the status of COVID-19 cases and deaths around the world. It is updated once a day around 10:00am CET. The code used to make this site is hosted <a href="https://github.com/dhopp1/COVID-19-status-reports">here</a>. Country groupings such as North America come from Wikipedia, but to see specifically which countries are included in each group check the <i>country_groups.csv</i> file <a href="https://github.com/dhopp1/COVID-19-status-reports/tree/master/plots/data">here</a>. Please note Robert Koch Institute data is continually revised backwards, so numbers will retroactively rise as time goes on and numbers shown here won't correspond exactly to those found <a href="https://experience.arcgis.com/experience/478220a4c454480e823b17327b2bf1d4">here</a>.
<br>
</p>
<p style="font-size:14px">
<strong>*Note:</strong> if you choose two countries with a large discrepency in case load, e.g. US and Cuba, the smaller country's curves will probably be invisible due to the scale. Set the second country to one with a more similar caseload to the smaller country, or set the second country to "None" to see the curve more clearly.
</p>
<h4>A note on testing</h4>
<p>
All this site does is give access to the data produced at the sources listed in the previous section. Different countries have different testing regimens and their governments have different policies. That means that these numbers alone cannot be taken as encapsulating the true extent of the situation in any given country. You can read more about the importance of testing in <a href="https://fivethirtyeight.com/features/coronavirus-case-counts-are-meaningless/">this</a> article.
</p>
<p>
<h4>Explanations</h4>
<p>
<strong>[1] X Axis:</strong> The units of the x (horizontal) axis. Days since 100th case are the number of days since the 100th case of the country were recorded. It is useful for comparing countries at different stages in their epidemics by giving them a common x axis. Days since 10th death is the same idea, but useful when looking at death rates.
</p>
<p>
<strong>[2] Metric:</strong> This filter will change the metric (y-axis) the graphs display. Active cases = cases - deaths - recovered cases. US and German states lack recovered data, so their active cases are just cases - deaths.
</p>
<p>
<strong>[3] Total/Per 100k Population:</strong> This filter will change all metrics to be per 100 thousand people, making metrics more comparable by country. Population data comes from <a href="https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)">here</a> for countries, <a href="https://en.wikipedia.org/wiki/States_of_Germany">here</a> for German states, <a href="https://en.wikipedia.org/wiki/Provinces_of_China">here</a> for Chinese provinces, <a href="https://en.wikipedia.org/wiki/List_of_states_and_territories_of_the_United_States_by_population">here</a> for US states, and their respective Wikipedia pages for other territories.
</p>
<p>
<strong>[4] Moving Average Smoothing:</strong> This filter refers to how much smoothing occurs in the new cases/deaths and acceleration cases/deaths plots. Countries can report very different numbers from day to day due to many factors like weekends, accounting errors, etc., so this dropdown attempts to smooth that volatility a little to see a better idea of the trend. 3 means that each day's value will be replaced with the average of 3 days' values, and so on. So a higher number means more smoothing.
</p>
<p>
<strong>[5] Bar Graphs/Linear Scale:</strong> Cumulative numbers mean all of the metric (e.g. cases, deaths, etc.) reported up to a certain day. New daily metric are the number of the metric reported/calculated for that day alone. Acceleration is the rate of change of the metric. A higher acceleration means not only are cases e.g. growing, but they're growing at an <em>increasing</em> rate. A negative acceleration is good (except for recovered cases) and means that cases e.g. are still growing, but not as quickly.
</p>
<p>
<strong>[6]: Log Scale </strong> See an explanation of a logarithmic scale <a href="https://en.wikipedia.org/wiki/Logarithmic_scale">here</a>. The dotted lines show the number of cases/deaths there would be if they doubled every 3, 5, or 10 days for country 1 (they are only visible for the "Cases" and "Deaths" metrics). They start from the day of the 100th confirmed case and 10th death for cases and deaths respectively. As a result they are interpreted most easily when the X axis is set to those respective metrics. Slopes rather than absolute levels should be used for comparison.
</p>
<p>
<strong>[7]: Forecasts</strong> Forecast numbers and plots are created using <a href="https://otexts.com/fpp2/holt.html">Holt's linear trend method with dampening</a>. This is a linear model, which means it probably significantly underestimates countries that are experiencing the acceleration phase of their epidemics. It will probably be better at forecasting countries at a more mature phase, such as Italy or Spain. Important to note is that this is just one of many methods that can forecast the data, and I have not spent a significant amount of time validating it. I may spend more time in the future investigating and adding better forecasting methods. Plots display the point forecast and 80% prediction interval (darker shading), and 95% prediction interval (lighter shading).
</p>
<p>
<strong>[8]: Overview Table</strong> The "Acceleration of Last 5 Days" column is calculated by the average second derivative over the last 5 days / number of cases 5 days ago. It doesn't have much intrinsic meaning but is rather a more comparable/relative measure between countries of how fast new cases are accelerating. The table is scrollable and sortable. Highlight a row by clicking or tapping for reference when scrolling horizontally.
</p>
"""
notes = Div(text=notes_text, width=600)
notes_tab = Panel(
    child=column(notes), title="README"
)
tabs = Tabs(tabs=[bar_tab, linear_tab, log_tab, forecast_tab, acceleration_tab, notes_tab])
# initialize plots with date format
all_plots = list(plots.values())
for p in all_plots:
    p.xaxis.formatter = DatetimeTickFormatter(
        days=["%d %b"], months=["%d %b"], years=["%d %b"]
    )

# final layout
layout = column(
    row(select1, select2),
    Spacer(height=15),
    row(x_col, metric_dropdown),
    Spacer(height=15),
    row(pop_dropdown, smoothing),
    Spacer(height=15),
    row(date_range),
    Spacer(height=20),
    row(data_table),
    Spacer(height=30),
    row(tabs),
)
curdoc().add_root(layout)
curdoc().title = "COVID-19 Status Report"
