using
CSVFiles,
DataFrames,
Dates

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

# adding US states
states_path = "covid-19-data/us-states.csv"
states = load(states_path) |> DataFrame!
states[!, :state] = "US: " .* states.state
for state in unique(states.state)
    tmp = states[states.state .== state, :]
    global all_country_data = vcat(all_country_data, gen_df(tmp.state[1], tmp.deaths, tmp.cases, tmp.date))
end

CSV.write("data/transformed_data.csv", all_country_data)
