# Data Pipeline Example

Sequential ETL pipeline: extract -> transform -> load.

## Prerequisites

- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) v4+
- [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite) for local storage emulation

## Run locally

```bash
# Start Azurite in a separate terminal
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log

# Install dependencies
pip install -r requirements.txt

# Start the function app
cd examples/data_pipeline
func start
```

## Test

```bash
# Start a pipeline run
curl -X POST http://localhost:7071/api/graphs/data_pipeline/runs \
  -H "Content-Type: application/json" \
  -d '{"input": {"source_url": "https://example.com/data"}}'

# Check run status (replace <instance_id> from the response above)
curl http://localhost:7071/api/runs/<instance_id>

# Health check
curl http://localhost:7071/api/health
```
