git -C COVID-19 pull &&
jupyter nbconvert --to notebook --execute COVID-19\ Status\ Report.ipynb --output COVID-19\ Status\ Report.ipynb &&
jupyter nbconvert COVID-19\ Status\ Report.ipynb &&
mv COVID-19\ Status\ Report.html index.html
