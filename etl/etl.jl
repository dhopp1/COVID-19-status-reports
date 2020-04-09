include("Acceleration.jl")
include("CSSE.jl")
include("Doubling.jl")
include("Forecast.jl")
include("Groups.jl")
include("RKI.jl")

using
.Acceleration,
.CSSE,
.Doubling,
.Forecast,
.Groups,
.RKI,
CSV

# CSSE
all_country_data = CSSE.all_country_data

# RKI
all_country_data = RKI.gen_RKI(all_country_data)

# Groups
println("Groups: adding country groups")
all_country_data = Groups.gen_groups(all_country_data)

# Doubling
println("Doubling: adding log doubling times")
all_country_data = all_country_data |> Doubling.initialize_df |> Doubling.gen_df

# write out all country file
println("Writing transformed_data.csv")
CSV.write("../plots/data/transformed_data.csv", all_country_data)


# Acceleration/overview
println("Acceleration: writing acceleration.csv")
Acceleration.gen_acceleration(all_country_data) |> x -> CSV.write("../plots/data/acceleration_data.csv", x)


# Forecast
println("Forecast: writing forecast.csv")
Forecast.gen_forecast(all_country_data) |> x -> CSV.write("../plots/data/forecasts.csv", x)

println("ETL complete")
