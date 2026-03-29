from azure_functions_langgraph import DurableGraphApp
from examples.support_agent.graph import registration

runtime = DurableGraphApp()
runtime.register_registration(registration)

app = runtime.function_app
