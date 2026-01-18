# How to Process Multiple Documents in Parallel

Parxy provides a `batch` method for processing multiple documents in parallel, with support for per-file configuration. This is useful when you need to parse many documents efficiently or when different documents require different parsing strategies.


## Basic Usage

The simplest way to batch process documents is to pass a list of file paths:

```python
from parxy_core.facade import Parxy

results = Parxy.batch(
    tasks=['document1.pdf', 'document2.pdf', 'document3.pdf'],
    drivers=['pymupdf'],
    level='block',
)

for result in results:
    if result.success:
        print(f'{result.file}: {len(result.document.pages)} pages')
    else:
        print(f'{result.file}: Error - {result.error}')
```


## Using Multiple Drivers

You can process each file with multiple drivers to compare results or use different backends:

```python
results = Parxy.batch(
    tasks=['document.pdf'],
    drivers=['pymupdf', 'llamaparse'],
)

# Each file is processed once per driver
for result in results:
    print(f'{result.driver}: {len(result.document.pages)} pages')
```


## Controlling Parallelism

By default, Parxy uses as many workers as CPU cores. You can customize this:

```python
results = Parxy.batch(
    tasks=['doc1.pdf', 'doc2.pdf', 'doc3.pdf'],
    workers=4,  # Use exactly 4 parallel workers
)
```


## Stopping on First Error

By default, batch processing continues even if some files fail. To stop immediately when the first error occurs, use `stop_on_error`:

```python
results = Parxy.batch(
    tasks=['doc1.pdf', 'doc2.pdf', 'doc3.pdf'],
    stop_on_error=True,
)

# Check if processing was interrupted
failed = [r for r in results if not r.success]
if failed:
    print(f'Processing stopped due to error: {failed[0].error}')
```

When `stop_on_error=True`:
- Processing stops as soon as any task fails
- Pending tasks are cancelled
- Only completed results (including the failed one) are returned


## Advanced: Per-File Configuration with BatchTask

For more control, use `BatchTask` objects to specify per-file configuration:

```python
from parxy_core.facade import Parxy, BatchTask

results = Parxy.batch(
    tasks=[
        # Simple file - uses batch-level defaults
        BatchTask(file='simple.pdf'),

        # Complex document - use LlamaParse with line-level extraction
        BatchTask(
            file='complex.pdf',
            drivers=['llamaparse'],
            level='line',
        ),

        # Compare multiple drivers for this file
        BatchTask(
            file='comparison.pdf',
            drivers=['pymupdf', 'pdfact', 'llamaparse'],
        ),
    ],
    drivers=['pymupdf'],  # Default driver for tasks without explicit drivers
    level='block',        # Default level for tasks without explicit level
)
```


## Mixed Mode

You can mix simple file paths with `BatchTask` objects:

```python
results = Parxy.batch(
    tasks=[
        'regular1.pdf',           # Uses defaults
        'regular2.pdf',           # Uses defaults
        BatchTask(                # Custom configuration
            file='special.pdf',
            drivers=['llamaparse'],
            level='span',
        ),
    ],
    drivers=['pymupdf'],
)
```


## Processing In-Memory Files

`BatchTask` accepts file paths, URLs, or binary data:

```python
import io

# Load files into memory
with open('doc1.pdf', 'rb') as f:
    pdf_bytes = f.read()

with open('doc2.pdf', 'rb') as f:
    pdf_stream = io.BytesIO(f.read())

results = Parxy.batch(
    tasks=[
        BatchTask(file='path/to/file.pdf'),      # File path
        BatchTask(file='https://example.com/doc.pdf'),  # URL
        BatchTask(file=pdf_bytes),               # Raw bytes
        BatchTask(file=pdf_stream),              # BytesIO stream
    ],
)
```


## Working with Results

The `batch` method returns a list of `BatchResult` objects:

| Attribute  | Type              | Description                                    |
|------------|-------------------|------------------------------------------------|
| `file`     | str/BytesIO/bytes | The input file that was processed              |
| `driver`   | str               | The driver name used for parsing               |
| `document` | Document or None  | The parsed document, or None if parsing failed |
| `error`    | str or None       | Error message if parsing failed                |
| `success`  | bool (property)   | True if parsing succeeded                      |
| `failed`   | bool (property)   | True if parsing failed                         |

Example of processing results:

```python
results = Parxy.batch(tasks=['doc1.pdf', 'doc2.pdf'])

successful = [r for r in results if r.success]
failed = [r for r in results if not r.success]

print(f'Processed {len(successful)} successfully, {len(failed)} failed')

# Access parsed documents
for result in successful:
    doc = result.document
    print(f'{result.file} ({result.driver}):')
    print(f'  Pages: {len(doc.pages)}')
    print(f'  Title: {doc.metadata.title if doc.metadata else "N/A"}')

# Handle errors
for result in failed:
    print(f'{result.file} ({result.driver}): {result.error}')
```


## Best Practices

1. **Choose appropriate worker count**: More workers isn't always better. For CPU-bound parsing (e.g., PyMuPDF), match your CPU cores. For I/O-bound parsing (e.g., API-based drivers), you can use more workers.

2. **Group similar files**: If files have similar characteristics, they likely benefit from the same driver and level settings.

3. **Handle errors gracefully**: Always check `result.success` before accessing `result.document`.

4. **Consider memory usage**: When processing many large files, the results list holds all parsed documents in memory. Process results incrementally if memory is a concern.


## API Reference

### BatchTask

```python
@dataclass
class BatchTask:
    file: str | BytesIO | bytes  # File to parse
    drivers: List[str] | None    # Drivers for this file (optional)
    level: str | None            # Extraction level (optional)
```

### BatchResult

```python
@dataclass
class BatchResult:
    file: str | BytesIO | bytes  # Input file
    driver: str                  # Driver used
    document: Document | None    # Parsed result
    error: str | None            # Error message

    @property
    def success(self) -> bool:   # True if document is not None

    @property
    def failed(self) -> bool:    # True if error is not None
```

### Parxy.batch()

```python
@classmethod
def batch(
    cls,
    tasks: List[BatchTask | str | BytesIO | bytes],
    drivers: List[str] | None = None,  # Default: [default_driver()]
    level: str = 'block',
    workers: int | None = None,        # Default: CPU count
    stop_on_error: bool = False,       # Stop on first error
) -> List[BatchResult]
```
