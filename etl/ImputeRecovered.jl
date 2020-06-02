module ImputeRecovered

using DataFrames

function impute(all_country_data)
    data = copy(all_country_data)
    missing_recovered = by(data, :country, :recovered => sum) |> x->
        x[x[!, 2] .== 0.0,:country] |>
        unique
    for country in missing_recovered
        subset = data[data.country .== country, :]
        new_cases = subset.new_cases
        new_deaths = subset.new_deaths
        recovered = fill(0.0, length(new_deaths))
        new_recoveries = fill(0.0, length(new_deaths))
        new_recoveries[15:end] = new_cases[1:end-14] - new_deaths[15:end]
        for i in 2:length(recovered)
            recovered[i] = recovered[i-1] + new_recoveries[i]
        end
        data[data.country .== country, :recovered] = recovered .|> x-> round(x, digits=0) .|> Int64
        data[data.country .== country, :new_recoveries] = new_recoveries .|> x->  round(x, digits=0) .|> Int64
        data[data.country .== country, :active_cases] = data[data.country .== country, :confirmed] .- data[data.country .== country, :recovered] .- data[data.country .== country, :deaths]
    end
    return data
end

end
