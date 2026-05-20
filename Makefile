.PHONY: all validate generate diagrams markdown dataframe app

all: validate generate

validate:
	python scripts/validate.py

generate: diagrams markdown dataframe

diagrams:
	python scripts/gen_diagrams.py

markdown:
	python scripts/gen_markdown.py

dataframe:
	python scripts/gen_dataframe.py

app:
	streamlit run app.py
