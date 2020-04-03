git -C COVID-19 pull &&
git -C covid-19-data &&
julia etl.jl &&
git add . &&
git commit -m "Daily update" &&
git push origin master
