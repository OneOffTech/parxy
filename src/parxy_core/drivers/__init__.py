from parxy_core.drivers.abstract_driver import Driver as Driver
from parxy_core.drivers.factory import DriverFactory as DriverFactory

# Concrete driver classes are exposed lazily so that `import parxy_core.drivers`
# (which the facade and CLI do on startup) does not eagerly import every
# driver's dependencies. Some drivers pull in heavy ML stacks (e.g. docling ->
# transformers/torch, ~5s), which would otherwise be loaded on every CLI
# invocation even when those drivers are never used.
_LAZY_DRIVERS = {
    'LlamaParseDriver': 'parxy_core.drivers.llamaparse',
    'LandingAIADEDriver': 'parxy_core.drivers.landingai',
    'LlmWhispererDriver': 'parxy_core.drivers.llmwhisperer',
    'PdfActDriver': 'parxy_core.drivers.pdfact',
    'PyMuPdfDriver': 'parxy_core.drivers.pymupdf',
    'UnstructuredLocalDriver': 'parxy_core.drivers.unstructured_local',
    'PyPDFium2Driver': 'parxy_core.drivers.pypdfium2',
    'PDFPlumberDriver': 'parxy_core.drivers.pdfplumber',
    'PDFMinerDriver': 'parxy_core.drivers.pdfminer',
    'DoclingDriver': 'parxy_core.drivers.docling',
    'LiteParseDriver': 'parxy_core.drivers.liteparse',
    'ReductoDriver': 'parxy_core.drivers.reducto',
}

__all__ = ['Driver', 'DriverFactory', *_LAZY_DRIVERS.keys()]


def __getattr__(name: str):
    """Lazily import driver classes on first attribute access (PEP 562)."""
    module_path = _LAZY_DRIVERS.get(name)
    if module_path is None:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')

    import importlib

    driver_class = getattr(importlib.import_module(module_path), name)
    globals()[name] = driver_class  # cache for subsequent lookups
    return driver_class


def __dir__():
    return sorted(__all__)
