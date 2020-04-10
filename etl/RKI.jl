module RKI

using
CSV,
CSVFiles,
DataFrames,
Dates,
HTTP,
JSON

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
historic = load("../plots/data/rki_data.csv") |> DataFrame!
json_array = []
missing_days = [Dates.today() - Dates.Day(n) for n in (Dates.today() - maximum(historic.date)).value-1:-1:1]
println("RKI: calling API")
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
    CSV.write("../plots/data/rki_data.csv", historic)
end

# converting to all_country_data format
println("RKI: converting format")
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

function gen_RKI(df)
    global historic
    select!(historic, names(df))
    historic[!, :country] = "Germany: " .* historic.country
    df = [df; historic]
end

println("RKI: complete")

# end module
end
