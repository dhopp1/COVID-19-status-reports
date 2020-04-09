module Forecast

using
DataFrames,
Dates,
RCall
R"library(forecast)"

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

function gen_forecast(df)
    counter = 1
    for country in unique(df.country)
        counter
        tmp = df[df.country .== country, :]
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
    return fc
end

# module end
end
