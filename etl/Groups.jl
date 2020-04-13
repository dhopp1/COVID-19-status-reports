module Groups

using
CSV,
CSVFiles,
DataFrames,
Statistics

function add_group(countries, df::DataFrame, name::String)
    subgroup = df[in.(df.country, (countries,)), :]
    cols(cols, operator) = eval(Meta.parse(replace(":" .* (cols .|> string) .* " => $operator" .|> string |> string, r"\"|\[|\]"=>"")))
    output = by(subgroup, :date,  cols([names(subgroup)[3:end-3]; :population], "sum"))
    rename!(output, [:date, :confirmed, :deaths, :death_rate, :recovered, :active_cases, :new_cases, :new_deaths, :new_recoveries, :acceleration_cases, :acceleration_deaths, :population])
    output[!, :death_rate] = output.deaths ./ output.confirmed
    output[!, :country] .= name
    output[!, :days_since_100] .= 0
    output[output.confirmed .>= 100, :days_since_100] = 1:nrow(output[output.confirmed .>= 100, :])
    output[!, :days_since_10] .= 0
    output[output.deaths .>= 10, :days_since_10] = 1:nrow(output[output.deaths .>= 10, :])
    select!(output, names(df))
    return output
end

groups = load("../plots/data/country_groups.csv") |> DataFrame!

function gen_groups(df)
    global groups
    for group in unique(groups.group)
        countries = groups[groups.group .== group, :country] |> Array
        df = [df; add_group(countries, df, group)]
    end
    return df
end

function persist_pop(df)
    CSV.write("../plots/data/population.csv", by(df, :country, population = :population => mean))
end

# module end
end
