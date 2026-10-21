# API / Plugin Development

## Creating a plugin
1. Copy `plugins/_template.py` to `plugins/my_plugin.py`.
2. Define `PLUGIN` dict with name, description, parameters.
3. Implement `run(parameters, player, session_memory)`.
4. Restart JARVIS (or wait for hot-reload).

## Creating an action
1. Copy an existing action from `actions/`.
2. Define `TOOL` dict with name, description, parameters, handler.
3. The handler receives `parameters` plus context kwargs.

## Tool declaration shape
See `core/action_loader.py` and `core/plugin_loader.py`.

## Testing
Run `python -m providers._tests` for provider tests.
Run `python -m compileall -q .` for syntax check.
PY