# Katana Monitoring Neural Layer v2 - TODO

## Epic: Katana Monitoring Neural Layer v2

### Group: Ingestion Layer

- [ ] `feat: Design Kafka topic structure for Katana multi-stream monitoring`
- [ ] `task: Implement multipart ingestion support via Protobuf & Avro`

### Group: Stream Processing

- [ ] `feat: Setup Faust-based stream processor for log and metric enrichment`
- [ ] `task: Implement severity filter and tag enricher`

### Group: Anomaly Detection Engine

- [ ] `feat: Integrate online anomaly detection using river`
- [ ] `task: Tune thresholds for error_rate and latency`

### Group: Reactive Feedback Loop

- [ ] `feat: Implement feedback command trigger on anomaly detection`
- [ ] `task: Create snapshot/log dump generator`

### Group: Visualization & Monitoring

- [ ] `feat: Setup Grafana with TimescaleDB datasource`
- [ ] `feat: Create Streamlit/FastAPI UI for live monitoring`

### Group: Tracing & Observability

- [ ] `feat: Integrate OpenTelemetry SDK into all producers/consumers`
- [t ] `ask: Enable Jaeger/Tempo backend + Grafana traces`

### Group: Infra & CI/CD

- [ ] `task: Add Helm chart for monitoring stack (Kafka, TSDB, Faust)`
- [ ] `task: Add GitHub Actions for testing stream processors`
- [ ] `task: Use Testcontainers to run integration tests on PR`

### Group: Docs & Diagrams

- [ ] `task: Finalize architecture diagrams (PlantUML/Draw.io)`
- [ ] `doc: Document monitoring v2 pipeline in README`
- [ ] `doc: Write quickstart on running stack locally (docker-compose + makefile)`
