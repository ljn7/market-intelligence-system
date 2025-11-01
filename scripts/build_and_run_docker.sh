#!/usr/bin/env bash
docker build -t market-intel-scraper .
docker run --rm -it \
  -v "$(pwd)/data":/app/data \
  -v "$(pwd)/logs":/app/logs \
  market-intel-scraper \
  python -m src.cli --config config.yaml
