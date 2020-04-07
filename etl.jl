using
CSV,
CSVFiles,
DataFrames,
Dates,
Format,
HTTP,
JSON,
RCall,
Statistics
R"library(forecast)"

death_path = "COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
confirmed_path = "COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"

death = load(death_path) |> DataFrame! |> x -> rename!(x, Dict(Symbol("Province/State") => :state, Symbol("Country/Region") => :country))
confirmed = load(confirmed_path) |> DataFrame! |> x -> rename!(x, Dict(Symbol("Province/State") => :state, Symbol("Country/Region") => :country))

# distinguishing states with territories via "Mainland"
for data_set in [death, confirmed]
    for country in ["United Kingdom", "Netherlands", "France", "Denmark"]
        data_set[(data_set.state .== "") .& (data_set.country .== country), :state] .= "Mainland"
    end
end

# add a row for total of countries with states
state_countries = confirmed[confirmed.state .!= "", :country] |> unique
for country in state_countries
    col_values = ["" country 0.0 0.0 ([sum(col) for col in eachcol(confirmed[confirmed.country .== country,:5:end])] |>
                    transpose)] |> DataFrame |> x -> rename!(x, names(confirmed))
    global confirmed = [confirmed; col_values]
    col_values = ["" country 0.0 0.0 ([sum(col) for col in eachcol(death[death.country .== country,:5:end])] |>
                    transpose)] |> DataFrame |> x -> rename!(x, names(death))
    global death = [death; col_values]
end

suffix(state, country) = state == "" ? country : country * ": " * state
for data_set in [death, confirmed]
    data_set[!, :country] = suffix.(data_set.state, data_set.country)
    select!(data_set, Not([:state, :Lat, :Long]))
end

function gen_df(country::String, d::Array{Int64}, c::Array{Int64}, dates::Array{Date})
    dates = reshape(dates, :, 1)
    df = convert(DataFrame, dates) |> x -> rename!(x, [:date])
    df[!, :country] .= country
    df[!, :confirmed] = c
    df[!, :deaths] = d
    df[!, :death_rate] = d ./ c
    df[!, :new_cases] .= 0
    df[2:end, :new_cases] = df[2:end, :confirmed] .- df[1:end-1, :confirmed]
    df[!, :new_deaths] .= 0
    df[2:end, :new_deaths] = df[2:end, :deaths] .- df[1:end-1, :deaths]
    df[!, :acceleration_cases] .= 0
    df[2:end, :acceleration_cases] = df[2:end, :new_cases] .- df[1:end-1, :new_cases]
    df[!, :acceleration_deaths] .= 0
    df[2:end, :acceleration_deaths] = df[2:end, :new_deaths] .- df[1:end-1, :new_deaths]
    df[!, :days_since_100] .= 0
    counter = 0
    for row in eachrow(df)
        if row.confirmed > 100
            counter += 1
        end
        row.days_since_100 = counter
    end
    df[!, :days_since_10] .= 0
    counter = 0
    for row in eachrow(df)
        if row.deaths > 10
            counter += 1
        end
        row.days_since_10 = counter
    end
    return df
end

function country_data(country)
    d = death[death.country .== country, 2:end] |> Array |> Iterators.flatten |> collect
    dates = [Dates.Date(2020, 1, 22) + Dates.Day(day) for day in 1:length(d)]
    c = confirmed[confirmed.country .== country, 2:end] |> Array |> Iterators.flatten |> collect
    df = gen_df(country, d, c, dates)
    return df
end

all_countries = death.country |> unique |> sort
all_country_data = vcat([country_data(country) for country in all_countries]...)

# adding world
no_states = all_country_data[.!occursin.(":", all_country_data.country), :]
no_states = by(no_states, :date,
    confirmed = :confirmed => sum,
    deaths = :deaths => sum,
    new_cases = :new_cases => sum,
    new_deaths = :new_deaths => sum,
    acceleration_cases = :acceleration_cases => sum,
    acceleration_deaths = :acceleration_deaths => sum
)
no_states[!, :death_rate] = no_states.deaths ./ no_states.confirmed
no_states[!, :days_since_100] = 1:nrow(no_states)
no_states[!, :days_since_10] = 1:nrow(no_states)
no_states[!, :country] .= "World"
no_states = no_states[!, names(all_country_data)]
all_country_data = [all_country_data; no_states]

# adding US states
states_path = "covid-19-data/us-states.csv"
states = load(states_path) |> DataFrame!
states[!, :state] = "US: " .* states.state
for state in unique(states.state)
    tmp = states[states.state .== state, :]
    global all_country_data = vcat(all_country_data, gen_df(tmp.state[1], tmp.deaths, tmp.cases, tmp.date))
end

# adding German states
function api_call(;start_date::Date, end_date::Date, bundesland::String)
    url = "https://services7.arcgis.com/mOBPykOjAyBO2ZKk/arcgis/rest/services/RKI_COVID19/FeatureServer/0/query?where=Bundesland%20%3D%20%27$(bundesland)%27%20AND%20Meldedatum%20%3E%3D%20TIMESTAMP%20%27$(start_date)%2000%3A00%3A00%27%20AND%20Meldedatum%20%3C%3D%20TIMESTAMP%20%27$(end_date)%2000%3A00%3A00%27&outFields=Bundesland,AnzahlFall,AnzahlTodesfall,Meldedatum&outSR=4326&f=json"
    response_json = HTTP.get(url).body |> String |> JSON.Parser.parse
    return response_json["features"]
end
bundesländer = [
    "Baden-Württemberg",
    "Bayern",
    "Berlin",
    "Brandenburg",
    "Bremen",
    "Hannover",
    "Hamburg",
    "Hessen",
    "Mecklenburg-Vorpommern",
    "Niedersachsen",
    "Nordrhein-Westfalen",
    "Rheinland-Pfalz",
    "Saarland",
    "Sachsen",
    "Sachsen-Anhalt",
    "Schleswig-Holstein",
    "Thüringen"
]
# getting data of missing days
historic = load("plots/data/rki_data.csv") |> DataFrame!
json_array = []
missing_days = [Dates.today() - Dates.Day(n) for n in (Dates.today() - maximum(historic.date)).value-1:-1:1]
for day in missing_days
    start_date = day
    end_date = day + Dates.Day(1)
    println(start_date)
    for bundesland in bundesländer
        response = api_call(start_date=start_date, end_date=end_date, bundesland=bundesland)#["attributes"]
        if !isempty(response)
            for line in response
                global json_array = [json_array; line["attributes"]]
            end
        end
    end
end
json_df = DataFrame()
for entry in json_array
    global json_df = [json_df; DataFrame(entry)]
end
if !isempty(json_array)
    json_df = by(json_df, [:Bundesland, :Meldedatum], new_cases = :AnzahlFall => x -> sum(x)/2, deaths = :AnzahlTodesfall => x -> sum(x)/2)
    rename!(json_df, [:country, :date, :new_cases, :deaths])
    select!(json_df, [:date, :country, :new_cases, :deaths])
    json_df[!, :date] = Dates.unix2datetime.(json_df.date ./ 1000) .|> Dates.Date
    historic = [historic; json_df]
    CSV.write("plots/data/rki_data.csv", historic)
end

# converting to all_country_data format
rename!(historic, Dict(:deaths => :new_deaths))
sort!(historic, (:country, :date))
historic[!, :confirmed] .= 0.0
historic[!, :deaths] .= 0.0
historic[!, :acceleration_cases] .= 0.0
historic[!, :acceleration_deaths] .= 0.0
for (new_col, metric) in Dict(:confirmed => :new_cases, :deaths => :new_deaths, :acceleration_cases => :new_cases, :acceleration_deaths => :new_deaths)
    for bundesland in bundesländer
        if new_col == :confirmed || new_col == :deaths
            historic[historic.country .== bundesland, new_col] .= cumsum(historic[historic.country .== bundesland, metric])
        else
            historic[historic.country .== bundesland, new_col] .= [0; historic[historic.country .== bundesland, metric][2:end] .- historic[historic.country .== bundesland, metric][1:end-1]]
        end
    end
end
historic[!, :death_rate] = historic.deaths ./ historic.confirmed
historic[!, :days_since_100] .= 0
historic[!, :days_since_10] .= 0
for bundesland in bundesländer
    mask = (historic.country .== bundesland) .& (historic.confirmed .>= 100)
    historic[mask, :days_since_100] .= 1:sum(mask)
    mask = (historic.country .== bundesland) .& (historic.confirmed .>= 10)
    historic[mask, :days_since_10] .= 1:sum(mask)
end
select!(historic, names(all_country_data))
historic[!, :country] = "Germany: " .* historic.country
all_country_data = [all_country_data; historic]

# adding country groups
function add_group(countries, df::DataFrame, name::String)
    subgroup = df[in.(df.country, (countries,)), :]
    cols(cols, operator) = eval(Meta.parse(replace(":" .* (cols .|> string) .* " => $operator" .|> string |> string, r"\"|\[|\]"=>"")))
    output = by(subgroup, :date,  cols(names(subgroup)[3:end-2], "sum"))
    rename!(output, [:date, :confirmed, :deaths, :death_rate, :new_cases, :new_deaths, :acceleration_cases, :acceleration_deaths])
    output[!, :death_rate] = output.deaths ./ output.confirmed
    output[!, :country] .= name
    output[!, :days_since_100] .= 0
    output[output.confirmed .>= 100, :days_since_100] = 1:nrow(output[output.confirmed .>= 100, :])
    output[!, :days_since_10] .= 0
    output[output.deaths .>= 10, :days_since_10] = 1:nrow(output[output.deaths .>= 10, :])
    select!(output, names(df))
    return output
end

groups = load("plots/data/country_groups.csv") |> DataFrame!

for group in unique(groups.group)
    countries = groups[groups.group .== group, :country] |> Array
    global all_country_data = [all_country_data; add_group(countries, all_country_data, group)]
end

# adding log doubling times
function double_time(start_number, days, n)
    output = []
    for i in 1:n
        push!(output, start_number)
        start_number = exp(log(2) / days) * start_number
    end
    return output
end

new_cols = Dict(:double_1_cases=>1, :double_3_cases=>3, :double_5_cases=>5, :double_10_cases=>10, :double_20_cases=>20, :double_1_deaths=>1, :double_3_deaths=>3, :double_5_deaths=>5, :double_10_deaths=>10, :double_20_deaths=>20)

for new_col in keys(new_cols)
    global all_country_data[!, new_col] .= 0.0
end

for country in unique(all_country_data.country)
    for (new_col, days) in new_cols
        if occursin("cases", string(new_col))
            if sum((all_country_data.country .== country) .& (all_country_data.days_since_100 .> 0)) > 0
                mask = (all_country_data.country .== country) .& (all_country_data.days_since_100 .> 0)
                base_col = :confirmed
                all_country_data[mask, new_col] = double_time(all_country_data[mask, base_col][1], days, length(all_country_data[mask, new_col]))
            end
        else
            if sum((all_country_data.country .== country) .& (all_country_data.days_since_10 .> 0)) > 0
                mask = (all_country_data.country .== country) .& (all_country_data.days_since_10 .> 0)
                base_col = :deaths
                all_country_data[mask, new_col] = double_time(all_country_data[mask, base_col][1], days, length(all_country_data[mask, new_col]))
            end
        end
    end
end

# write out all country file
CSV.write("plots/data/transformed_data.csv", all_country_data)

# adding acceleration table
countries = unique(all_country_data.country)
acceleration = []
cases_5_ago = []
cases_now = []
deaths = []
for country in countries
    metric = mean(all_country_data[all_country_data.country .== country, :acceleration_cases][end-4:end])
    metric /= all_country_data[all_country_data.country .== country, :confirmed][end-4]
    if isnan(metric)
        metric = 0
    end
    push!(acceleration, metric)
    push!(cases_5_ago, all_country_data[all_country_data.country .== country, :confirmed][end-4])
    push!(cases_now, all_country_data[all_country_data.country .== country, :confirmed][end])
    push!(deaths, all_country_data[all_country_data.country .== country, :deaths][end])
end
last_5 = rename!(DataFrame([countries, cases_now, cases_5_ago, deaths, acceleration]), [:country, :cases_now, :cases_5_ago, :deaths, :last_5_accel])
last_5[!, :perc_increase] = last_5.cases_now ./ last_5.cases_5_ago .- 1
last_5[!, :death_rate] = last_5.deaths ./ last_5.cases_now
tmp = sort(last_5, order(:cases_now, rev=true))
tmp[!, :perc_increase] = string.(round.(tmp.perc_increase .* 100, digits=2)) .* "%"
tmp[!, :death_rate] = string.(round.(tmp.death_rate .* 100, digits=2)) .* "%"
rename!(tmp, [Symbol("Country/Region"), Symbol("Confirmed Cases"), Symbol("Cases 5 Days Ago"), :Deaths, Symbol("Acceleration of Last 5 Days"), Symbol("% Increase in 5 Days"), Symbol("Death Rate")])
tmp[!, Symbol("Acceleration of Last 5 Days")] = string.(round.(tmp[!, Symbol("Acceleration of Last 5 Days")] * 100, digits=2)) .* "%"
select!(tmp, [Symbol("Country/Region"), Symbol("Confirmed Cases"), Symbol("Cases 5 Days Ago"), Symbol("% Increase in 5 Days"), Symbol("Acceleration of Last 5 Days"), :Deaths, Symbol("Death Rate")])
for col in [Symbol("Confirmed Cases"), Symbol("Cases 5 Days Ago"), :Deaths]
    tmp[!, col] = format.(tmp[!, col], commas=true)
end
CSV.write("plots/data/acceleration_data.csv", tmp)

# adding forecast
function r_forecast(x, y; country, metric, r_forecast_function, time_function, h)
    fc_x = [x[end] + time_function(i) for i in 1:h]
    fc = r_forecast_function(y)
    point_forecast = [val for val in fc[2]]
    lo_80 = [val for val in fc[6][1:h]]
    hi_80 = [val for val in fc[5][1:h]]
    lo_95 = [val for val in fc[6][h+1:h*2]]
    hi_95 = [val for val in fc[5][h+1:h*2]]
    output = hcat([point_forecast, lo_80, hi_80, lo_95, hi_95]...) |> DataFrame |> x -> rename!(x, [:point_forecast, :lo_80, :hi_80, :lo_95, :hi_95])
    output[!, :date] = fc_x
    output[!, :country] .= country
    output[!, :metric] .= metric
    output = output[!, [:date, :country, :metric, :point_forecast, :lo_80, :hi_80, :lo_95, :hi_95]]

    return output
end

counter = 1
for country in unique(all_country_data.country)
    global counter
    tmp = all_country_data[all_country_data.country .== country, :]
    if maximum(tmp.confirmed) >= 100
        if counter == 1
            global fc = r_forecast(tmp.date, tmp.confirmed; country=country, metric="cases", r_forecast_function = z -> R"holt"(z, h=20, damped=true), time_function = Dates.Day, h = 20)
            fc = [fc;
                r_forecast(tmp.date, tmp.deaths; country=country, metric="deaths", r_forecast_function = z -> R"holt"(z, h=20, damped=true), time_function = Dates.Day, h = 20)
            ]
            counter += 1
        else
            fc = [fc;
                r_forecast(tmp.date, tmp.confirmed; country=country, metric="cases", r_forecast_function = z -> R"holt"(z, h=20, damped=true), time_function = Dates.Day, h = 20)
            ]
            fc = [fc;
                r_forecast(tmp.date, tmp.deaths; country=country, metric="deaths", r_forecast_function = z -> R"holt"(z, h=20, damped=true), time_function = Dates.Day, h = 20)
            ]
        end
    end
end

CSV.write("plots/data/forecasts.csv", fc)
