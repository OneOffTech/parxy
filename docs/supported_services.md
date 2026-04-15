---
title: Supported services
description: All document processing services and libraries supported by Parxy, their stability status, required extras, and how to register a custom driver.
weight: 2
---

# Supported Services

Parxy supports the following document processing services and libraries. The **Extra** column shows the optional dependency group to install for each driver.

| Service or Library | Support status | Extra | Local file | Remote file |
|--------------------|----------------|-------|------------|-------------|
| [**PyMuPDF**](https://pymupdf.readthedocs.io/en/latest/) | Live | *(included)* | ✅ | ✅ |
| [**PdfAct**](https://github.com/data-house/pdfact) | Live | *(included)* | ✅ | ✅ |
| [**Unstructured** library](https://docs.unstructured.io/open-source/introduction/overview) | Preview | `unstructured_local` | ✅ | ✅ |
| [**Landing AI Agentic Document Extraction**](https://landing.ai/agentic-document-extraction) | Preview | `landingai` | ✅ | ✅ |
| [**LlamaParse**](https://docs.cloud.llamaindex.ai/llamaparse/overview) | Preview | `llama` | ✅ | ✅ |
| [**LLMWhisperer**](https://docs.unstract.com/llmwhisperer/index.html) | Preview | `llmwhisperer` | ✅ | ✅ |


Status meanings: **Live** = stable; **Preview** = functional but the API may change.

## Adding a custom driver (Live Extension)

You can register a new driver directly in your application code — no fork required.

**1. Create a class that inherits from `Driver`**

```python
from parxy_core.drivers import Driver
from parxy_core.models import Document

class CustomDriverExample(Driver):
    """Example custom driver."""

    def _handle(self, file, level="page") -> Document:
        return Document(pages=[])
```

**2. Register it with `Parxy.extend()`**

```python
from parxy_core.facade import Parxy

Parxy.extend(name='my_parser', callback=lambda: CustomDriverExample())
```

**3. Use it**

```python
Parxy.driver('my_parser').parse('path/to/document.pdf')
```

For a full guide on building and publishing a driver, see [How to Add a New Parser to Parxy](./howto/add_new_parser.md).
