FROM python:3.11-slim

WORKDIR /app

# No third-party dependencies (stdlib only), so no pip install step.
COPY . /app

RUN python3 -m unittest discover -s tests -v

CMD ["python3", "run_demo.py"]
