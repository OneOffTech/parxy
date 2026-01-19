# Document Structure

Documents and pages are composed of logical parts, e.g. headings, footnotes, tables, images, headers, and footers, that describe *what content is*, rather than *how it is visually presented*. These logical parts are independent of layout, styling, or rendering medium.

We refer to this logical classification as **document structure**, or more generally as **document semantics**. In this context, *semantics* describe the role a piece of content plays within the document, as defined by the [W3C Web Accessibility Initiative definition of semantics](https://www.w3.org/TR/wai-aria/#dfn-semantics).

Following the terminology of the [W3C Web Accessibility Initiative (WAI)](https://www.w3.org/WAI/standards-guidelines/aria/), each logical part of a document is assigned a **role**.
Roles prefixed with `doc-` identify **document structure roles**, while other roles describe **in-page or interactive structures**.

Document structure roles describe elements that organize and contextualize content within a page or publication. These roles are typically **non-interactive** and convey structural meaning rather than behavior.

**Roles** are mutuated from [Accessible Rich Internet Applications (WAI-ARIA)](https://www.w3.org/TR/wai-aria/) and the [Digital Publishing WAI-ARIA Module](https://www.w3.org/TR/dpub-aria-1.1/), specifically suited for structural divisions of long-form documents.

Because many document parsers and extraction tools use inconsistent or undocumented classification schemes, we maintain explicit **mappings from parser-specific categories to WAI-ARIA roles**. For this reason, we use the `role` field (rather than `category`) to represent document structure semantics in a standardized way. It is important to note that parsers might not support all roles.


## Page level roles

Page level roles applies to parts of a page (although some of them can span across pages). Page roles are a subset of [WAI-ARIA Document Structure Roles](https://www.w3.org/TR/wai-aria/#document_structure_roles)[^1].

[^1]: The term document structure might confuse you as ARIA roles comes from accessibility in a HTML document, so document in that context refers to an element of the markup language containing content that assistive technology users may want to browse in a reading mode.

- **blockquote**: A section of content quoted from another source.
- **caption**: Visible content that names and may describe a figure or a table.
- **definition**: Content that provides the meaning or explanation of a term.
- **deletion**: Content that has been removed or marked as deleted from the document.
- **emphasis**: Text that is emphasized to convey stress or importance in spoken or written language.
- **figure**: A self-contained unit of content, such as an image, diagram, code example, or illustration, often referenced from the main text.
- **generic**: Content that does not convey a specific semantic role beyond grouping or containment.
- **heading**: A label or title that introduces and describes the topic of a section.
- **insertion**: Content that has been added or inserted into the document.
- **list**: A collection of related items presented in a sequential or grouped form.
- **listitem**: A single item within a list.
- **math**: Mathematical expressions or formulas represented in a structured form.
- **paragraph**: A distinct block of text that presents a single idea or unit of discourse.
- **row**: A horizontal grouping of cells within a table or grid.
- **strong**: Text of strong importance, seriousness, or urgency.
- **subscript**: Text displayed below the baseline, typically used in mathematical or chemical notation.
- **superscript**: Text displayed above the baseline, commonly used for exponents, references, or annotations.
- **table**: A structured arrangement of data organized into rows and columns.





## Document level roles

Document level roles applies to parts of a document. Document roles are the same as defined in the [Digital Publishing WAI-ARIA Module](https://www.w3.org/TR/dpub-aria-1.1/).


- **doc-abstract**: A short summary of the principal ideas, concepts, and conclusions of the work, or of a section or excerpt within it.
- **doc-acknowledgments**: A section or statement that acknowledges significant contributions by persons, organizations, governments, and other entities to the realization of the work.
- **doc-afterword**: A closing statement from the author or a person of importance, typically providing insight into how the content came to be written, its significance, or related events that have transpired since its timeline.
- **doc-appendix**: A section of supplemental information located after the primary content that informs the content but is not central to it.
- **doc-backlink**: A link that allows the user to return to a related location in the content (e.g., from a footnote to its reference or from a glossary definition to where a term is used).
- **doc-bibliography**: A list of external references cited in the work, which could be to print or digital sources.
- **doc-biblioref**: A reference to a bibliography entry.
- **doc-chapter**: A major thematic section of content in a work.
- **doc-colophon**: A short section of production notes particular to the edition (e.g., describing the typeface used), often located at the end of a work.
- **doc-conclusion**: A concluding section or statement that summarizes the work or wraps up the narrative.
- **doc-cover**: An image that sets the mood or tone for the work and typically includes the title and author.
- **doc-credit**: An acknowledgment of the source of integrated content from third-party sources, such as photos. Typically identifies the creator, copyright, and any restrictions on reuse.
- **doc-credits**: A collection of credits.
- **doc-dedication**: An inscription at the front of the work, typically addressed in tribute to one or more persons close to the author.
- **doc-endnotes**: A collection of notes at the end of a work or a section within it.
- **doc-epigraph**: A quotation set at the start of the work or a section that establishes the theme or sets the mood.
- **doc-epilogue**: A concluding section of narrative that wraps up or comments on the actions and events of the work, typically from a future perspective.
- **doc-errata**: A set of corrections discovered after initial publication of the work, sometimes referred to as corrigenda.
- **doc-example**: An illustration of a key concept of the work, such as a code listing, case study or problem.
- **doc-footnote**: Ancillary information, such as a citation or commentary, that provides additional context to a referenced passage of text.
- **doc-foreword**: An introductory section that precedes the work, typically not written by the author of the work.
- **doc-glossary**: A brief dictionary of new, uncommon, or specialized terms used in the content.
- **doc-glossref**: A reference to a glossary definition.
- **doc-index**: A navigational aid that provides a detailed list of links to key subjects, names and other important topics covered in the work.
- **doc-introduction**: A preliminary section that typically introduces the scope or nature of the work.
- **doc-noteref**: A reference to a footnote or endnote, typically appearing as a superscripted number or symbol in the main body of text.
- **doc-notice**: Notifies the user of consequences that might arise from an action or event. Examples include warnings, cautions and dangers.
- **doc-pagebreak**: A separator denoting the position before which a break occurs between two contiguous pages in a statically paginated version of the content.
- **doc-pagefooter**: A section of text appearing at the bottom of a page that provides context about the current work and location within it. The page footer is distinct from the body text and normally follows a repeating template that contains (possibly truncated) items such as the document title, current section, author name(s), and page number.
- **doc-pageheader**: A section of text appearing at the top of a page that provides context about the current work and location within it. The page header is distinct from the body text and normally follows a repeating template that contains (possibly truncated) items such as the document title, current section, author name(s), and page number.
- **doc-pagelist**: A navigational aid that provides a list of links to the page breaks in the content.
- **doc-part**: A major structural division in a work that contains a set of related sections dealing with a particular subject, narrative arc, or similar encapsulated theme.
- **doc-preface**: An introductory section that precedes the work, typically written by the author of the work.
- **doc-prologue**: An introductory section that sets the background to a work, typically part of the narrative.
- **doc-pullquote**: A distinctively placed or highlighted quotation from the current content designed to draw attention to a topic or highlight a key point.
- **doc-qna**: A section of content structured as a series of questions and answers, such as an interview or list of frequently asked questions.
- **doc-subtitle**: An explanatory or alternate title for the work, or a section or component within it.
- **doc-tip**: Helpful information that clarifies some aspect of the content or assists in its comprehension.
- **doc-toc**: A navigational aid that provides an ordered list of links to the major sectional headings in the content. A table of contents could cover an entire work or only a smaller section of it.


Considering that in ARIA title comes from the HTML document we decided to add a non-standard role `doc-title` to represent the document title.


