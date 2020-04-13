module Population

using
DataFrames,
CSV

population = CSV.read("../plots/data/population.csv") |> DataFrame!

function add_population(df)
    join(df, population, on=:country, kind=:left)
end

# end module
end
