init:
	pip install -U pipenv
	pipenv install --dev

ci:
	./style.sh