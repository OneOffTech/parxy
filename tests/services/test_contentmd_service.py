"""Test suite for ContentMdService."""

import pytest

from parxy_core.models.models import (
    Document,
    ImageBlock,
    Metadata,
    Page,
    TableBlock,
    TextBlock,
)
from parxy_core.services.contentmd_service import ContentMdService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_page(
    number: int = 1,
    text: str = '',
    blocks: list | None = None,
) -> Page:
    return Page(number=number, text=text, blocks=blocks)


def make_text_block(
    text: str,
    role: str = 'generic',
    level: int | None = None,
) -> TextBlock:
    return TextBlock(type='text', text=text, role=role, level=level)


def make_image_block(
    alt_text: str | None = None, name: str | None = None
) -> ImageBlock:
    return ImageBlock(type='image', alt_text=alt_text, name=name)


def make_table_block(text: str) -> TableBlock:
    return TableBlock(type='table', text=text)


def make_doc(
    pages: list[Page],
    metadata: Metadata | None = None,
    filename: str | None = None,
    language: str | None = None,
) -> Document:
    return Document(
        pages=pages,
        metadata=metadata,
        filename=filename,
        language=language,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_doc():
    """Document with a single page, no blocks, no metadata."""
    return make_doc(pages=[make_page(text='Hello world')])


@pytest.fixture
def metadata_doc():
    """Document with full metadata and one plain paragraph block."""
    meta = Metadata(
        title='Metadata Title',
        author='Jane Doe',
        created_at='2025-01-15',
    )
    page = make_page(
        text='Paragraph text.',
        blocks=[make_text_block('Paragraph text.')],
    )
    return make_doc(pages=[page], metadata=meta, filename='report.pdf')


@pytest.fixture
def all_blocks_doc():
    """Document whose first page contains every supported block type."""
    blocks = [
        make_text_block('My Document', role='doc-title'),
        make_text_block('Introduction', role='heading', level=1),
        make_text_block('Background', role='heading', level=2),
        make_text_block('First item\nSecond item', role='list'),
        make_text_block('A plain paragraph.', role='paragraph'),
        make_text_block('A brief overview.', role='doc-abstract'),
        make_image_block(alt_text='A sunset over mountains', name='sunset.jpg'),
        make_table_block('| Col A | Col B |\n| ----- | ----- |\n| 1     | 2     |'),
    ]
    page = make_page(text='My Document', blocks=blocks)
    return make_doc(pages=[page], language='en')


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


class TestFrontmatter:
    def test_frontmatter_delimiters_present(self, minimal_doc):
        result = ContentMdService.render(minimal_doc, title='T', description='D')
        lines = result.splitlines()
        assert lines[0] == '---'
        closing = lines.index('---', 1)
        assert closing > 0

    def test_explicit_title_in_frontmatter(self, minimal_doc):
        result = ContentMdService.render(minimal_doc, title='Explicit Title')
        assert 'title: "Explicit Title"' in result

    def test_title_from_metadata(self, metadata_doc):
        result = ContentMdService.render(metadata_doc)
        assert 'title: "Metadata Title"' in result

    def test_title_from_doc_title_role_preferred_over_heading(self):
        blocks = [
            make_text_block('Real Title', role='doc-title'),
            make_text_block('Section One', role='heading', level=1),
        ]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc)
        assert 'title: "Real Title"' in result

    def test_title_from_heading_when_no_doc_title(self):
        blocks = [
            make_text_block('Section One', role='heading', level=2),
            make_text_block('Section Two', role='heading', level=1),
        ]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc)
        # Level 1 heading wins (lowest level = highest rank)
        assert 'title: "Section Two"' in result

    def test_title_from_filename_when_no_headings(self):
        doc = make_doc(
            pages=[make_page(text='body text')],
            filename='my-report.pdf',
        )
        result = ContentMdService.render(doc)
        assert 'title: "my-report.pdf"' in result

    def test_title_fallback_to_untitled(self):
        doc = make_doc(pages=[make_page(text='body text')])
        result = ContentMdService.render(doc)
        assert 'title: "Untitled"' in result

    def test_description_from_explicit_param(self, minimal_doc):
        result = ContentMdService.render(
            minimal_doc, title='T', description='My summary.'
        )
        assert 'description: "My summary."' in result

    def test_description_from_doc_abstract_block(self):
        blocks = [
            make_text_block('Abstract content here.', role='doc-abstract'),
            make_text_block(
                'A much longer paragraph that should not be picked.', role='paragraph'
            ),
        ]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc)
        assert 'description: "Abstract content here."' in result

    def test_description_from_first_five_body_blocks(self):
        blocks = [make_text_block(f'Sentence {i}.', role='paragraph') for i in range(7)]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc)
        # Only the first five contribute; the sixth and seventh are ignored
        assert 'Sentence 5' not in result.split('---\n')[1].split('\n')[0]
        assert 'Sentence 0' in result

    def test_description_excludes_structural_roles(self):
        blocks = [
            make_text_block('Table of contents text.', role='doc-toc'),
            make_text_block('Page header text.', role='doc-pageheader'),
            make_text_block('A heading block.', role='heading'),
            make_text_block('Body content.', role='paragraph'),
        ]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc)
        assert 'description: "Body content."' in result

    def test_description_truncated_to_200_chars(self):
        long_text = 'word ' * 60  # well over 200 chars
        blocks = [make_text_block(long_text, role='paragraph')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc)
        fm_end = result.index('---\n', 4)
        frontmatter = result[:fm_end]
        desc_line = next(l for l in frontmatter.splitlines() if l.startswith('description:'))
        # Strip the YAML quoting to measure the actual value length
        value = desc_line[len('description: "'):-1]
        assert len(value) <= 200

    def test_description_contains_no_newlines(self):
        blocks = [make_text_block('Line one.\nLine two.\nLine three.', role='paragraph')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc)
        fm_end = result.index('---\n', 4)
        frontmatter = result[:fm_end]
        desc_line = next(l for l in frontmatter.splitlines() if l.startswith('description:'))
        assert '\n' not in desc_line

    def test_description_searches_first_two_pages(self):
        page1 = make_page(number=1, text='', blocks=[make_text_block('Page 1 text.')])
        page2 = make_page(
            number=2,
            text='',
            blocks=[make_text_block('Page 2 has a longer text block.')],
        )
        page3 = make_page(
            number=3,
            text='',
            blocks=[make_text_block('Page 3 has the longest block of all by far.')],
        )
        doc = make_doc(pages=[page1, page2, page3])
        result = ContentMdService.render(doc)
        # Page 3 is out of the two-page window
        assert 'Page 3' not in result.split('---')[1]  # not in frontmatter

    def test_date_from_metadata_created_at(self, metadata_doc):
        result = ContentMdService.render(metadata_doc)
        assert 'date: "2025-01-15"' in result

    def test_date_from_metadata_updated_at_when_no_created_at(self):
        meta = Metadata(updated_at='2025-06-01')
        doc = make_doc(pages=[make_page(text='')], metadata=meta)
        result = ContentMdService.render(doc)
        assert 'date: "2025-06-01"' in result

    def test_explicit_date_overrides_metadata(self, metadata_doc):
        result = ContentMdService.render(metadata_doc, date='2026-01-01')
        assert 'date: "2026-01-01"' in result
        assert '2025-01-15' not in result

    def test_author_from_metadata(self, metadata_doc):
        result = ContentMdService.render(metadata_doc)
        assert 'author: "Jane Doe"' in result

    def test_optional_fields_omitted_when_absent(self, minimal_doc):
        result = ContentMdService.render(minimal_doc, title='T')
        assert 'description:' not in result
        assert 'date:' not in result
        assert 'license:' not in result
        assert 'author:' not in result

    def test_license_included_when_provided(self, minimal_doc):
        result = ContentMdService.render(minimal_doc, title='T', license='CC-BY-4.0')
        assert 'license: "CC-BY-4.0"' in result

    def test_yaml_values_escaped(self, minimal_doc):
        result = ContentMdService.render(
            minimal_doc,
            title='Title with "quotes"',
            description='Back\\slash',
        )
        assert r'title: "Title with \"quotes\""' in result
        assert r'description: "Back\\slash"' in result


# ---------------------------------------------------------------------------
# Body – block rendering
# ---------------------------------------------------------------------------


class TestBodyBlocks:
    def test_body_starts_with_h1_title(self, metadata_doc):
        result = ContentMdService.render(metadata_doc)
        body = result.split('---\n', 2)[-1]
        assert body.lstrip().startswith('# Metadata Title')

    def test_doc_title_block_skipped_in_body(self, all_blocks_doc):
        result = ContentMdService.render(all_blocks_doc)
        body = result.split('---\n', 2)[-1]
        # Should appear exactly once (as the h1), not twice
        assert body.count('My Document') == 1

    def test_heading_level_shifted_by_one(self):
        blocks = [make_text_block('Section', role='heading', level=1)]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '## Section' in result

    def test_heading_level_2_becomes_3(self):
        blocks = [make_text_block('Subsection', role='heading', level=2)]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '### Subsection' in result

    def test_heading_without_level_defaults_to_h2(self):
        blocks = [make_text_block('Heading', role='heading')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '## Heading' in result

    def test_heading_level_capped_at_6(self):
        blocks = [make_text_block('Deep', role='heading', level=6)]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '###### Deep' in result
        assert '####### Deep' not in result

    def test_list_role_rendered_as_bullets(self):
        blocks = [make_text_block('Alpha\nBeta\nGamma', role='list')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '- Alpha' in result
        assert '- Beta' in result
        assert '- Gamma' in result

    def test_listitem_role_rendered_as_bullet(self):
        blocks = [make_text_block('Single item', role='listitem')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '- Single item' in result

    def test_doc_abstract_rendered_as_abstract_tag(self, all_blocks_doc):
        result = ContentMdService.render(all_blocks_doc)
        assert '<abstract lang="en">' in result
        assert 'A brief overview.' in result
        assert '</abstract>' in result

    def test_doc_abstract_without_language_omits_lang_attr(self):
        blocks = [make_text_block('Summary.', role='doc-abstract')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '<abstract>\nSummary.\n</abstract>' in result

    def test_generic_textblock_rendered_as_paragraph(self):
        blocks = [make_text_block('Plain paragraph text.', role='generic')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert 'Plain paragraph text.' in result

    def test_empty_textblock_not_rendered(self):
        blocks = [make_text_block('   ', role='paragraph')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        # Body should only contain the h1 line
        body = result.split('---\n', 2)[-1].strip()
        assert body == '# T'

    def test_image_block_rendered_as_figure(self):
        blocks = [make_image_block(alt_text='A sunset over mountains')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '<figure>\nA sunset over mountains\n</figure>' in result

    def test_image_block_without_alt_text(self):
        blocks = [make_image_block()]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '<figure>\n\n</figure>' in result

    def test_table_block_rendered_as_is(self):
        table_text = '| Col A | Col B |\n| ----- | ----- |\n| 1     | 2     |'
        blocks = [make_table_block(table_text)]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert table_text in result

    def test_page_without_blocks_uses_page_text(self):
        page = make_page(text='Fallback page text', blocks=None)
        doc = make_doc(pages=[page])
        result = ContentMdService.render(doc, title='T')
        assert 'Fallback page text' in result

    def test_empty_page_text_not_rendered(self):
        page = make_page(text='   ', blocks=None)
        doc = make_doc(pages=[page])
        result = ContentMdService.render(doc, title='T')
        body = result.split('---\n', 2)[-1].strip()
        assert body == '# T'


# ---------------------------------------------------------------------------
# Whitespace normalisation
# ---------------------------------------------------------------------------


class TestWhitespaceNormalisation:
    def test_multiple_spaces_in_paragraph_collapsed(self):
        blocks = [make_text_block('Word1   Word2     Word3')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert 'Word1 Word2 Word3' in result

    def test_tabs_in_paragraph_collapsed(self):
        blocks = [make_text_block('Word1\t\tWord2')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert 'Word1 Word2' in result

    def test_whitespace_in_heading_collapsed(self):
        blocks = [make_text_block('My   Section', role='heading', level=1)]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '## My Section' in result

    def test_whitespace_in_title_collapsed(self):
        blocks = [make_text_block('  My   Title  ', role='doc-title')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc)
        assert 'title: "My Title"' in result

    def test_whitespace_in_description_collapsed(self):
        blocks = [make_text_block('Summary   with   gaps.', role='doc-abstract')]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert 'description: "Summary with gaps."' in result

    def test_table_whitespace_preserved(self):
        table_text = '| Col A | Col B |\n| ----- | ----- |'
        blocks = [make_table_block(table_text)]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert '| Col A | Col B |' in result


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------


class TestOutputStructure:
    def test_result_ends_with_newline(self, minimal_doc):
        result = ContentMdService.render(minimal_doc, title='T')
        assert result.endswith('\n')

    def test_empty_pages_list_returns_frontmatter_and_title(self):
        doc = Document(pages=[])
        result = ContentMdService.render(doc, title='Empty')
        assert 'title: "Empty"' in result
        assert '# Empty' in result

    def test_blocks_separated_by_blank_line(self):
        blocks = [
            make_text_block('First paragraph.'),
            make_text_block('Second paragraph.'),
        ]
        doc = make_doc(pages=[make_page(text='', blocks=blocks)])
        result = ContentMdService.render(doc, title='T')
        assert 'First paragraph.\n\nSecond paragraph.' in result

    def test_multipage_document_renders_all_pages(self):
        page1 = make_page(
            number=1,
            text='',
            blocks=[make_text_block('Page one content.')],
        )
        page2 = make_page(
            number=2,
            text='',
            blocks=[make_text_block('Page two content.')],
        )
        doc = make_doc(pages=[page1, page2])
        result = ContentMdService.render(doc, title='T')
        assert 'Page one content.' in result
        assert 'Page two content.' in result

    def test_render_delegates_from_document_method(self, metadata_doc):
        via_service = ContentMdService.render(metadata_doc)
        via_method = metadata_doc.contentmd()
        assert via_service == via_method
