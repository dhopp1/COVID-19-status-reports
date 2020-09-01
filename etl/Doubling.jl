module Doubling

function double_time(start_number, days, n)
    output = []
    for i in 1:n
        push!(output, start_number)
        start_number = minimum([exp(log(2) / days) * start_number, 1e9]) # limit to 1 billion to avoid y axis exploding
    end
    return output
end

new_cols = Dict(:double_1_cases=>1, :double_3_cases=>3, :double_5_cases=>5, :double_10_cases=>10, :double_20_cases=>20, :double_1_deaths=>1, :double_3_deaths=>3, :double_5_deaths=>5, :double_10_deaths=>10, :double_20_deaths=>20)

function initialize_df(df)
    for new_col in keys(new_cols)
        df[!, new_col] .= 0.0
    end
    return df
end

function gen_df(df)
    for country in unique(df.country)
        for (new_col, days) in new_cols
            if occursin("cases", string(new_col))
                if sum((df.country .== country) .& (df.days_since_100 .> 0)) > 0
                    mask = (df.country .== country) .& (df.days_since_100 .> 0)
                    base_col = :confirmed
                    df[mask, new_col] = double_time(df[mask, base_col][1], days, length(df[mask, new_col]))
                end
            else
                if sum((df.country .== country) .& (df.days_since_10 .> 0)) > 0
                    mask = (df.country .== country) .& (df.days_since_10 .> 0)
                    base_col = :deaths
                    df[mask, new_col] = double_time(df[mask, base_col][1], days, length(df[mask, new_col]))
                end
            end
        end
    end
    return df
end

# module end
end
