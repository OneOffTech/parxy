# How to Add a New Parser to Parxy

Parxy is designed to be **extensible** — you can integrate new parsing backends (drivers) or create custom variants of existing ones directly from your Python code, without modifying the core library.


## Live Extension

Live extensions let you register and use new drivers *on the fly*, directly within your app.
This is ideal for experimentation, testing, or deploying custom parsers in a dynamic environment.

### 1. Create a Custom Driver

Each parser must subclass the base `Driver` class from `parxy_core.drivers`.
At minimum, you need to implement the `_handle` method, which receives a file and should return a `Document` model.

```python
from parxy_core.drivers import Driver
from parxy_core.models import Document

class CustomDriverExample(Driver):
    """Example custom driver for testing."""

    def _handle(self, file, level="page") -> Document:
        # Implement your custom parsing logic here
        return Document(pages=[])
```

Your driver can:

* Read files from disk, bytes, or URLs
* Support specific extraction levels (page, block, line, span, character)
* Leverage logging (`self._logger`) for diagnostics


### 2. Register the Driver Dynamically

Once defined, you can make Parxy aware of your new driver using the `extend` method.

```python
from parxy_core.facade import Parxy

Parxy.extend(name='my_parser', callback=lambda: CustomDriverExample())
```

This registers a new driver named `my_parser`, available globally within your current process.


### 3. Use Your Custom Parser

After registration, your driver can be used just like any built-in one.

```python
doc = Parxy.driver('my_parser').parse('path/to/document.pdf')
```


## The Driver Base Class

All drivers must subclass [`Driver`](../../src/parxy_core/drivers/abstract_driver.py).

Here's a simplified overview of the main methods:

| Method                           | Description                                                                           |
|----------------------------------|---------------------------------------------------------------------------------------|
| `_handle(file, level, **kwargs)` | Main entry point to implement your parsing logic. Must return a `Document`.           |
| `_initialize_driver()`           | Called once during initialization, can be overridden for setup.                       |
| `_validate_level(level)`         | Ensures the selected extraction level is supported.                                   |
| `get_stream_from_url(url)`       | Helper to safely fetch and validate remote files.                                     |
| `parse(file, level, **kwargs)`   | Public entry point that wraps `_handle` with validation, error handling, and tracing. |

Each driver should declare its supported extraction levels:

```python
supported_levels = ["page", "block", "line"]
```


## Error Handling

Your `_handle` method should raise exceptions appropriate to the failure:

| Exception                 | Meaning                                      |
|---------------------------|----------------------------------------------|
| `FileNotFoundException`   | File or URL is missing or inaccessible.      |
| `AuthenticationException` | Failed authentication for external services. |
| `ParsingException`        | Any generic or unexpected parsing error.     |

Parxy automatically wraps low-level exceptions into these structured types when possible.


## Best Practices

* Use `self._logger` for debug or error messages — Parxy sets it up automatically.
* Keep `_handle` atomic and stateless — initialization should happen in `_initialize_driver()` if needed.
* Always validate the `level` before parsing files.


## Example: Register a Remote API Parser

Here's a slightly more realistic example that sends the file to a remote service:

```python
import requests
from parxy_core.drivers import Driver
from parxy_core.models import Document

class ApiDriver(Driver):
    """Driver that sends documents to a remote parsing API."""

    supported_levels = ["block"]

    def _handle(self, file, level="block") -> Document:
        if isinstance(file, str):
            with open(file, "rb") as f:
                file_data = f.read()
        else:
            file_data = file.read()

        response = requests.post("https://api.example.com/parse", files={"file": file_data})
        response.raise_for_status()

        json_data = response.json()
        return Document.model_validate(json_data)
```

Register and use it:

```python
Parxy.extend("api_parser", lambda: ApiDriver())
Parxy.driver("api_parser").parse("document.pdf")
```


## Contributing as a Built-in Driver

If your driver could benefit the broader community, you can contribute it to Parxy's official `parxy_core.drivers` module.
In that case:

* Include docstrings and type annotations
* Add tests under `tests/drivers/`
* Update the driver list in `Parxy.drivers()`
