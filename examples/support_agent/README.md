# Support Agent Example

Human-in-the-loop support workflow with approval events.

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
cd examples/support_agent
func start
```

## Test

```bash
# Start a support run
curl -X POST http://localhost:7071/api/graphs/support_agent/runs \
  -H "Content-Type: application/json" \
  -d '{"input": {"user_message": "I need a refund for order #12345"}}'

# Send approval event (replace <instance_id>)
curl -X POST http://localhost:7071/api/runs/<instance_id>/events/approval \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "reviewer": "admin@example.com"}'

# Check run status (replace <instance_id> from the response above)
curl http://localhost:7071/api/runs/<instance_id>

# Health check
curl http://localhost:7071/api/health
```
