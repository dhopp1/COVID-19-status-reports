git pull &&
git -C COVID-19 pull &&
cd etl/ && julia ETL.jl && cd .. &&
git add . &&
git commit -m "Daily update" &&
git push origin master
