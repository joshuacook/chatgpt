PROJECT = chatgpt
PYTHON_VERSION = 3.10

PYTEST_ARGS = -x -p no:warnings
PYTEST_COVERAGE = --cov-report term-missing --cov=${PROJECT}
PYTEST_DEBUG = -s
PYTEST_FOCUS = -k focus

initialize:
	conda create -n ${PROJECT} python=${PYTHON_VERSION} --yes
	conda activate ${PROJECT}
	pip install -r requirements.txt

lint:
	black chatgpt tests
	flake8 chatgpt tests

activate:
	conda activate ${PROJECT}

test: lint
	pytest ${PYTEST_COVERAGE} ${PYTEST_ARGS}

debug:
	pytest ${PYTEST_DEBUG} ${PYTEST_ARGS}

focus:
	pytest ${PYTEST_DEBUG} ${PYTEST_ARGS} ${PYTEST_FOCUS}