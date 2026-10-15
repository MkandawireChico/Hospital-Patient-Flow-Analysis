setup:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt

test:
	PYTHONPATH=src pytest -q

lint:
	PYTHONPATH=src ruff check .

run:
	PYTHONPATH=src python -m patient_flow.cli run

analyse:
	PYTHONPATH=src python -m patient_flow.cli analyse
