"""Support Agent Example - Azure Functions entry point.

Run from this directory:
    func start
"""

from graph import registration

from azure_functions_durable_graph import DurableGraphApp

runtime = DurableGraphApp()
runtime.register_registration(registration)

app = runtime.function_app
