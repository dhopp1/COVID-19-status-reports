module Acceleration

using
CSV,
DataFrames,
Statistics

population = CSV.read("../plots/data/population.csv") |> DataFrame!

function gen_acceleration(df)
    countries = df.country |> unique
    acceleration = []
    cases_5_ago = []
    cases_now = []
    deaths = []
    recovered = []
    active = []
    for country in countries
        metric = mean(df[df.country .== country, :acceleration_cases][end-4:end])
        metric /= df[df.country .== country, :confirmed][end-4]
        if isnan(metric)
            metric = 0
        end
        push!(acceleration, metric)
        push!(cases_5_ago, df[df.country .== country, :confirmed][end-4])
        push!(cases_now, df[df.country .== country, :confirmed][end])
        push!(deaths, df[df.country .== country, :deaths][end])
        push!(recovered, df[df.country .== country, :recovered][end])
        push!(active, df[df.country .== country, :active_cases][end])
    end
    last_5 = rename!(DataFrame([countries, cases_now, cases_5_ago, recovered, active, deaths, acceleration]), [:country, :cases_now, :cases_5_ago, :recovered, :active_cases, :deaths, :last_5_accel])
    last_5[!, :perc_increase] = last_5.cases_now ./ last_5.cases_5_ago .- 1
    last_5[!, :death_rate] = last_5.deaths ./ last_5.cases_now
    tmp = sort(last_5, order(:cases_now, rev=true))
    tmp[!, :perc_increase] = round.(tmp.perc_increase .* 100, digits=2)
    tmp[!, :death_rate] = round.(tmp.death_rate .* 100, digits=2)
    rename!(tmp, [Symbol("Country/Region"), Symbol("Confirmed Cases"), Symbol("Cases 5 Days Ago"), Symbol("Recovered Cases"), Symbol("Active Cases"), :Deaths, Symbol("Acceleration of Last 5 Days"), Symbol("% Increase in 5 Days"), Symbol("Death Rate")])
    tmp[!, Symbol("Acceleration of Last 5 Days")] = round.(tmp[!, Symbol("Acceleration of Last 5 Days")] * 100, digits=2)
    select!(tmp, [Symbol("Country/Region"), Symbol("Confirmed Cases"), Symbol("Cases 5 Days Ago"), Symbol("% Increase in 5 Days"), Symbol("Acceleration of Last 5 Days"), Symbol("Recovered Cases"), Symbol("Active Cases"),:Deaths, Symbol("Death Rate")])

    return join(tmp, population, on=(Symbol("Country/Region"), :country), kind=:left)
end

# module end
end
