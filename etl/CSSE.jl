module CSSE

using
CSV,
CSVFiles,
DataFrames,
Dates

println("CSSE: initial CSV read")

cols(cols, operator) = eval(Meta.parse(replace(":" .* (cols .|> string) .* " => $operator" .|> string |> string, r"\"|\[|\]"=>"")))

death_path = "../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
confirmed_path = "../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
recovered_path = "../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv"
us_confirmed_path = "../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"
us_death_path = "../COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv"

# drop US, get it from state accumulation except for recovered
# missing 22.01 data, duplicated 23.01 data
println("CSSE: initial CSV read")

# combining us counties to state level
us_confirmed = load(us_confirmed_path) |> DataFrame! |> x -> rename!(x, Dict(Symbol("Province_State") => :state, Symbol("Country_Region") => :country, :Long_ => :Long)) |> x -> hcat(x[!, 7:10], x[!, 13], x[!, 13:end], makeunique=true) |> x -> rename!(x, Dict(:x1 => Symbol("1/22/20")))
rename!(us_confirmed, [[:state, :country]; Symbol.(["x" * string(i) for i in 1:ncol(us_confirmed)-2])])
# any by() handle newer julia version
try
    global us_confirmed = by(us_confirmed, [:state, :country], cols(names(us_confirmed)[3:end], "sum"))
catch
    global us_confirmed = groupby(us_confirmed, [:state, :country]) |> x-> combine(x, cols(names(us_confirmed)[3:end], "sum")...)
end

us_death = load(us_death_path) |> DataFrame! |> x -> rename!(x, Dict(Symbol("Province_State") => :state, Symbol("Country_Region") => :country, :Long_ => :Long)) |> x -> x[!, [7:10;13:end]]
rename!(us_death, [[:state, :country]; Symbol.(["x" * string(i) for i in 1:ncol(us_death)-2])])
try
    global us_death = by(us_death, [:state, :country], cols(names(us_death)[3:end], "sum"))
catch
    global us_death = groupby(us_death, [:state, :country]) |> x->  combine(x, cols(names(us_death)[3:end], "sum")...)
end

confirmed = load(confirmed_path) |> DataFrame! |> x -> rename!(x, Dict(Symbol("Province/State") => :state, Symbol("Country/Region") => :country))
rename!(us_confirmed, names(confirmed))
confirmed = [confirmed; us_confirmed]

death = load(death_path) |> DataFrame! |> x -> rename!(x, Dict(Symbol("Province/State") => :state, Symbol("Country/Region") => :country))
rename!(us_death, names(death))
death = [death; us_death]

recovered = load(recovered_path) |> DataFrame! |> x -> rename!(x, Dict(Symbol("Province/State") => :state, Symbol("Country/Region") => :country))
# create 0s for US states recovered
n_col = ncol(recovered)
empty_row =  ["US" 0.0 0.0 reshape([0 for i in 5:n_col], 1, :)]
for state in unique(us_confirmed.state)
    global recovered
    push!(recovered, [state empty_row])
end

# distinguishing states with territories via "Mainland"
for data_set in [death, confirmed, recovered]
    for country in ["United Kingdom", "Netherlands", "France", "Denmark"]
        data_set[(data_set.state .== "") .& (data_set.country .== country), :state] .= "Mainland"
    end
end

# add a row for total of countries with states
println("CSSE: adding rows for total of countries with states")
state_countries = confirmed[confirmed.state .!= "", :country] |> unique |> x -> x[x .!= "US"]
function country_total(data)
    for country in state_countries
        col_values = ["" country 0.0 0.0 ([sum(col) for col in eachcol(data[data.country .== country,5:end])] |>
                        transpose)] |> DataFrame |> x -> rename!(x, names(data))
        data = [data; col_values]
    end
    return data
end
confirmed = country_total(confirmed)
death = country_total(death)
recovered = country_total(recovered)

# rename states to be in one column
suffix(state, country) = state == "" ? country : country * ": " * state
for data_set in [death, confirmed, recovered]
    data_set[!, :country] = suffix.(data_set.state, data_set.country)
    select!(data_set, Not([:state, :Lat, :Long]))
end

function gen_df(country::String, d::Array{Int64}, c::Array{Int64}, r::Array{Int64}, dates::Array{Date})
    dates = reshape(dates, :, 1)
    df = convert(DataFrame, dates) |> x -> rename!(x, [:date])
    df[!, :country] .= country
    df[!, :confirmed] = c
    df[!, :deaths] = d
    df[!, :death_rate] = d ./ c
    df[!, :recovered] = r
    df[!, :active_cases] = c .- d .- r
    df[!, :new_cases] .= 0
    df[2:end, :new_cases] = df[2:end, :confirmed] .- df[1:end-1, :confirmed]
    df[!, :new_deaths] .= 0
    df[2:end, :new_deaths] = df[2:end, :deaths] .- df[1:end-1, :deaths]
    df[!, :new_recoveries] .= 0
    df[2:end, :new_recoveries] = df[2:end, :recovered] .- df[1:end-1, :recovered]
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
    d = death[death.country .== country, 2:end] |> Array
    d = [ismissing(x) ? 0 : x for x in d]
    d = d |> Iterators.flatten |> collect .|> Int
    dates = [Dates.Date(2020, 1, 22) + Dates.Day(day) for day in 1:length(d)]
    c = confirmed[confirmed.country .== country, 2:end] |> Array |> Iterators.flatten |> collect .|> Int
    r = recovered[recovered.country .== country, 2:end]
    if nrow(r) == 0
        r = repeat([0], length(c))
    else
        r = r[1, :] |> DataFrame
    end
    r = r |> Array |> Iterators.flatten |> collect .|> Int
    df = gen_df(country, d, c, r, dates)
    return df
end

all_countries = death.country |> unique |> sort
all_countries = all_countries[all_countries .!= ""]
println("CSSE: processing data")
all_country_data = vcat([country_data(country) for country in all_countries]...)

# adding world
println("CSSE: adding world")
no_states = all_country_data[.!occursin.(":", all_country_data.country), :]
no_states = by(no_states, :date,
    confirmed = :confirmed => sum,
    deaths = :deaths => sum,
    recovered = :recovered => sum,
    active_cases = :active_cases => sum,
    new_cases = :new_cases => sum,
    new_deaths = :new_deaths => sum,
    new_recoveries = :new_recoveries => sum,
    acceleration_cases = :acceleration_cases => sum,
    acceleration_deaths = :acceleration_deaths => sum
)
no_states[!, :death_rate] = no_states.deaths ./ no_states.confirmed
no_states[!, :days_since_100] = 1:nrow(no_states)
no_states[!, :days_since_10] = 1:nrow(no_states)
no_states[!, :country] .= "World"
no_states = no_states[!, names(all_country_data)]
all_country_data = [all_country_data; no_states]
println("CSSE: complete")
# end module
end
