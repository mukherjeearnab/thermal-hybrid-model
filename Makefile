.PHONY: install export-fmu generate-data train run-hybrid evaluate test clean

install:
	pip install -r requirements.txt

export-fmu:
	python scripts/export_fmu.py --mode=automatic

export-fmu-manual:
	python scripts/export_fmu.py --mode=manual

generate-data:
	python scripts/generate_data.py

train:
	python scripts/train.py

run-hybrid:
	python scripts/run_hybrid.py

evaluate:
	python scripts/evaluate.py

test:
	pytest -v

all: export-fmu generate-data train run-hybrid evaluate

clean:
	rm -rf data/raw/*.csv data/processed/*.csv \
		artifacts/checkpoints/* artifacts/metrics/* \
		results/*.csv results/plots/*.png
