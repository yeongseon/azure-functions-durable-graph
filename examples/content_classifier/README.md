# Content Classifier Example

Conditional routing workflow for user-submitted text.

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
cd examples/content_classifier
func start
```

## Test

```bash
# Start a classification run
curl -X POST http://localhost:7071/api/graphs/content_classifier/runs \
  -H "Content-Type: application/json" \
  -d '{"input": {"text": "How do I reset my password?"}}'

# Check run status (replace <instance_id> from the response above)
curl http://localhost:7071/api/runs/<instance_id>

# Health check
curl http://localhost:7071/api/health
```
