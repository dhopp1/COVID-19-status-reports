git -C COVID-19 pull &&
julia etl/ETL.jl &&
git add . &&
git commit -m "Daily update" &&
git push origin master
