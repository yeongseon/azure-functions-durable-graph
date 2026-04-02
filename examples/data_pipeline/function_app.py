"""Data Pipeline Example - Azure Functions entry point.

Run from this directory:
    func start
"""

# pyright: reportImplicitRelativeImport=false, reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from graph import registration

from azure_functions_durable_graph import DurableGraphApp

runtime = DurableGraphApp()
runtime.register_registration(registration)

app = runtime.function_app
