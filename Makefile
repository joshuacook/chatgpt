PROJECT = chatgpt
PYTHON_VERSION = 3.10

PYTEST_ARGS = -x -p no:warnings
PYTEST_COVERAGE = --cov-report term-missing --cov=${PROJECT}
PYTEST_DEBUG = -s
PYTEST_FOCUS = -k focus

clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

initialize:
	conda create -n ${PROJECT} python=${PYTHON_VERSION} --yes
	conda activate ${PROJECT}
	pip install -r requirements.txt

lint:
	black chatgpt tests
	flake8 chatgpt tests

activate:
	conda activate ${PROJECT}

run:
	FLASK_APP=chatgpt/app.py FLASK_ENV=development flask run

test: lint
	pytest ${PYTEST_COVERAGE} ${PYTEST_ARGS}

debug:
	pytest ${PYTEST_DEBUG} ${PYTEST_ARGS}

focus:
	pytest ${PYTEST_DEBUG} ${PYTEST_ARGS} ${PYTEST_FOCUS}