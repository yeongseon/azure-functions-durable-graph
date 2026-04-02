from azure_functions_durable_graph import DurableGraphApp
from examples.support_agent.graph import registration

runtime = DurableGraphApp()
runtime.register_registration(registration)

app = runtime.function_app
