# Technical notes & rationale

- **Nitter** is used as the public Twitter front-end to avoid paid APIs. Instances may be unreliable; rotate instances in `config.yaml`.
- **Selenium + undetected_chromedriver**: used to render JS and avoid simple bot detection. Headless may be less reliable depending on target instance — try toggling `headless` in config.
- **Parquet** used for efficient columnar storage.
- **TF-IDF** used for lightweight text-to-signal conversion (no heavy embedding model).
- **Scaling**: For 10x scale:
  - run multiple worker instances (containerized) with different proxies/IPs and aggregate parquet files.
  - replace TF-IDF with incremental vectorizers or online models if memory becomes a bottleneck.
- **Data quality**:
  - dedupe by `tweet_id`
  - normalize unicode using built-in Python string normalization (already handled lightly in `utils.clean_text`).
