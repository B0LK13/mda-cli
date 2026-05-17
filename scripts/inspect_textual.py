import inspect
from textual.app import App

print("run_test:", App.run_test)
print(inspect.signature(App.run_test))
