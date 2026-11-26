# Excluded initial measurement

The first Locust invocation reconciled Compose dependencies back to two agent replicas. Its CSVs are preserved for transparency and excluded from final scaling tables. Official scale_1 and scale_3 runs use --no-deps and have saved Prometheus target counts proving one and three replicas.
