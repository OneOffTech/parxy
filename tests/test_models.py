from parxy_core.models import (
    BoundingBox,
    Style,
    Character,
    Span,
    Line,
    TextBlock,
    ImageBlock,
    TableBlock,
    Page,
    Metadata,
    Document,
)


class TestModels:
    def test_bounding_box(self):
        bbox = BoundingBox(x0=0.0, y0=10.0, x1=100.0, y1=50.0)
        assert bbox.x0 == 0.0
        assert bbox.y0 == 10.0
        assert bbox.x1 == 100.0
        assert bbox.y1 == 50.0

    def test_style(self):
        style = Style(
            font_name='Arial',
            font_size=12.0,
            font_style='normal',
            color='#000000',
            alpha=255,
            weight=400.0,
        )
        assert style.font_name == 'Arial'
        assert style.font_size == 12.0
        assert style.font_style == 'normal'
        assert style.color == '#000000'
        assert style.alpha == 255
        assert style.weight == 400.0

    def test_character(self):
        bbox = BoundingBox(x0=0.0, y0=0.0, x1=10.0, y1=10.0)
        style = Style(font_name='Times')
        char = Character(text='A', bbox=bbox, style=style, page=1)
        assert char.text == 'A'
        assert char.bbox == bbox
        assert char.style == style
        assert char.page == 1
        assert not char.isEmpty()

    def test_span(self):
        bbox = BoundingBox(x0=0.0, y0=0.0, x1=50.0, y1=20.0)
        style = Style(font_size=12.0)
        chars = [Character(text='H', page=1), Character(text='i', page=1)]
        span = Span(text='Hi', bbox=bbox, style=style, characters=chars, page=1)
        assert span.text == 'Hi'
        assert span.bbox == bbox
        assert span.style == style
        assert len(span.characters) == 2
        assert span.page == 1
        assert not span.isEmpty()

    def test_line(self):
        bbox = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=30.0)
        style = Style(font_name='Helvetica')
        spans = [Span(text='Hello', page=1), Span(text='World', page=1)]
        line = Line(text='Hello World', bbox=bbox, style=style, spans=spans, page=1)
        assert line.text == 'Hello World'
        assert line.bbox == bbox
        assert line.style == style
        assert len(line.spans) == 2
        assert line.page == 1
        assert not line.isEmpty()

    def test_text_block(self):
        bbox = BoundingBox(x0=0.0, y0=0.0, x1=200.0, y1=100.0)
        style = Style(font_size=14.0)
        lines = [Line(text='First line', page=1), Line(text='Second line', page=1)]
        block = TextBlock(
            type='text',
            bbox=bbox,
            page=1,
            category='paragraph',
            style=style,
            level=1,
            lines=lines,
            text='First line\nSecond line',
        )
        assert block.type == 'text'
        assert block.bbox == bbox
        assert block.category == 'paragraph'
        assert block.style == style
        assert block.level == 1
        assert len(block.lines) == 2
        assert block.text == 'First line\nSecond line'
        assert not block.isEmpty()

    def test_image_block(self):
        bbox = BoundingBox(x0=0.0, y0=0.0, x1=300.0, y1=200.0)
        image = ImageBlock(type='image', bbox=bbox, page=1)
        assert image.type == 'image'
        assert image.bbox == bbox
        assert image.page == 1

    def test_table_block(self):
        bbox = BoundingBox(x0=0.0, y0=0.0, x1=400.0, y1=300.0)
        table = TableBlock(type='table', bbox=bbox, page=1)
        assert table.type == 'table'
        assert table.bbox == bbox
        assert table.page == 1

    def test_page(self):
        text_block = TextBlock(type='text', text='Sample text', page=1)
        image_block = ImageBlock(type='image', page=1)
        page = Page(
            number=1,
            width=612.0,
            height=792.0,
            blocks=[text_block, image_block],
            text='Sample text',
        )
        assert page.number == 1
        assert page.width == 612.0
        assert page.height == 792.0
        assert len(page.blocks) == 2
        assert page.text == 'Sample text'
        assert not page.isEmpty()

    def test_metadata(self):
        metadata = Metadata(
            title='Test Document',
            author='John Doe',
            subject='Testing',
            keywords='test,document',
            creator='Test App',
            producer='PDF Library',
            created_at='2025-08-18',
            updated_at='2025-08-18',
        )
        assert metadata.title == 'Test Document'
        assert metadata.author == 'John Doe'
        assert metadata.subject == 'Testing'
        assert metadata.keywords == 'test,document'
        assert metadata.creator == 'Test App'
        assert metadata.producer == 'PDF Library'
        assert metadata.created_at == '2025-08-18'
        assert metadata.updated_at == '2025-08-18'

    def test_document(self):
        metadata = Metadata(title='Test Document')
        page = Page(number=1, text='Page content')
        doc = Document(
            filename='test.pdf',
            language='en',
            metadata=metadata,
            pages=[page],
            outline=['Chapter 1', 'Chapter 2'],
        )
        assert doc.filename == 'test.pdf'
        assert doc.language == 'en'
        assert doc.metadata == metadata
        assert len(doc.pages) == 1
        assert doc.outline == ['Chapter 1', 'Chapter 2']
        assert not doc.isEmpty()
