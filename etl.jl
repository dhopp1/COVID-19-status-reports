using
CSV,
CSVFiles,
DataFrames,
Dates,
RCall
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

CSV.write("plots/data/transformed_data.csv", all_country_data)

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
