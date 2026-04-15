#!/usr/bin/env python3
"""
Generate CLI and configuration reference documentation for Parxy.

Run this script whenever CLI commands or configuration options change:

    python scripts/generate_docs.py

Writes:
    docs/reference/cli.md
    docs/reference/configuration.md
"""

import ast
import inspect
import logging
import sys
import textwrap
import types
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

GENERATED_NOTICE = """\
<!-- This file is auto-generated from the source code. Do not edit it manually. -->
<!-- Regenerate with: python scripts/generate_docs.py -->
"""

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _literal_values(annotation) -> list | None:
    """
    Return the allowed literal values if *annotation* is (or wraps) a Literal type.

    Handles all three common forms:
      - ``Literal['a', 'b']``
      - ``Optional[Literal['a', 'b']]``  (typing.Union with None)
      - ``Literal['a', 'b'] | None``     (Python 3.10+ union syntax)
    """
    if annotation is None:
        return None

    origin = getattr(annotation, "__origin__", None)

    # Direct: Literal['a', 'b']
    if origin is typing.Literal:
        return list(annotation.__args__)

    # Union: Optional[Literal[...]] or Literal[...] | None
    is_union = origin is typing.Union or isinstance(annotation, types.UnionType)
    if is_union:
        for arg in getattr(annotation, "__args__", ()):
            if arg is type(None):
                continue
            if getattr(arg, "__origin__", None) is typing.Literal:
                return list(arg.__args__)

    return None


def _type_label(click_type) -> str:
    """Human-readable label for a Click parameter type."""
    import click

    if isinstance(click_type, click.Choice):
        return " | ".join(f"`{c}`" for c in click_type.choices)
    name = getattr(click_type, "name", None) or type(click_type).__name__
    return f"`{name.lower()}`"


def _default_label(value, is_flag: bool = False) -> str:
    """Human-readable default value for a CLI option."""
    import enum

    if value is None:
        return "-"
    if is_flag:
        return "`false`" if value is False else "`true`"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, list) and not value:
        return "-"
    # Enum instances from typer — use .value
    if isinstance(value, enum.Enum):
        return f"`{value.value}`"
    return f"`{value}`"


# ---------------------------------------------------------------------------
# CLI reference
# ---------------------------------------------------------------------------

def _iter_leaf_commands(group):
    """
    Yield (display_name, click_command) for every non-hidden leaf command.

    Handles both flat commands and single-level groups (e.g. the `tui`
    sub-app which has a callback but no sub-commands).
    """
    import click

    for name, cmd in sorted(group.commands.items()):
        if getattr(cmd, "hidden", False):
            continue
        if isinstance(cmd, click.Group) and cmd.commands:
            # Proper sub-command group — recurse one level
            for sub_name, sub_cmd in sorted(cmd.commands.items()):
                if not getattr(sub_cmd, "hidden", False):
                    yield f"{name} {sub_name}", sub_cmd
        else:
            yield name, cmd


def _format_command(full_name: str, cmd) -> str:
    """Format one command as a markdown section."""
    import click

    lines = []
    lines.append(f"## `parxy {full_name}`\n")

    # Help text — strip the Examples block, which is too verbose for a reference page
    help_text = (cmd.help or "").strip()
    if "\n\nExamples:" in help_text:
        help_text = help_text[: help_text.index("\n\nExamples:")].strip()
    if help_text:
        lines.append(help_text + "\n")

    # Usage line
    has_opts = any(isinstance(p, click.Option) for p in cmd.params)
    args_str = ""
    for p in cmd.params:
        if isinstance(p, click.Argument):
            mv = p.human_readable_name.upper()
            if p.nargs == -1:
                mv += "..."
            args_str += f" {mv}"

    lines.append(f"```\nparxy {full_name}{' [OPTIONS]' if has_opts else ''}{args_str}\n```\n")

    # Arguments table
    args = [p for p in cmd.params if isinstance(p, click.Argument)]
    if args:
        lines.append("**Arguments:**\n")
        lines.append("| Argument | Required | Description |")
        lines.append("|----------|----------|-------------|")
        for arg in args:
            req = "Yes" if arg.required else "No"
            desc = (arg.help or "").replace("\n", " ").strip()
            lines.append(f"| `{arg.human_readable_name.upper()}` | {req} | {desc} |")
        lines.append("")

    # Options table (skip the --help flag)
    opts = [
        p
        for p in cmd.params
        if isinstance(p, click.Option) and not p.hidden and p.name != "help"
    ]
    if opts:
        lines.append("**Options:**\n")
        lines.append("| Option | Short | Type | Default | Description |")
        lines.append("|--------|-------|------|---------|-------------|")
        for opt in opts:
            long_opts = [o for o in opt.opts if o.startswith("--")]
            short_opts = [o for o in opt.opts if not o.startswith("--")]
            long = ", ".join(f"`{o}`" for o in long_opts)
            short = ", ".join(f"`{o}`" for o in short_opts) if short_opts else "-"
            type_str = "`flag`" if opt.is_flag else _type_label(opt.type)
            default_str = _default_label(opt.default, is_flag=opt.is_flag)
            desc = (opt.help or "").replace("\n", " ").strip()
            lines.append(f"| {long} | {short} | {type_str} | {default_str} | {desc} |")
        lines.append("")

    return "\n".join(lines)


def generate_cli_reference() -> str:
    import typer
    from parxy_cli.cli import app

    cli = typer.main.get_command(app)

    frontmatter = (
        "---\n"
        "title: CLI reference\n"
        "description: Command line reference with all parxy commands, including arguments, options, types, and defaults. Prefer to run parxy --help and parxy <command> --help if you have access to the terminal.\n"
        "---\n"
    )

    parts = [
        frontmatter,
        GENERATED_NOTICE,
        "# CLI reference\n",
    ]

    for name, cmd in _iter_leaf_commands(cli):
        parts.append(_format_command(name, cmd))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Configuration reference
# ---------------------------------------------------------------------------

def _field_docstrings(cls) -> dict[str, str]:
    """
    Extract per-field docstrings from a Pydantic settings class.

    Pydantic does not capture attribute docstrings automatically, so we
    parse the class source with the AST and look for string literals that
    immediately follow an annotated assignment.
    """
    try:
        source = textwrap.dedent(inspect.getsource(cls))
        tree = ast.parse(source)
    except Exception:
        return {}

    descriptions: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        body = node.body
        for i, child in enumerate(body):
            if not (isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name)):
                continue
            field_name = child.target.id
            if i + 1 >= len(body):
                continue
            nxt = body[i + 1]
            if (
                isinstance(nxt, ast.Expr)
                and isinstance(nxt.value, ast.Constant)
                and isinstance(nxt.value.value, str)
            ):
                descriptions[field_name] = nxt.value.value.strip()

    return descriptions


def _env_prefix(cls) -> str:
    try:
        return cls.model_config.get("env_prefix", "").upper()
    except Exception:
        return ""


def _config_default_label(field_name: str, field_info) -> str:
    """Human-readable default for a Pydantic field."""
    from pydantic_core import PydanticUndefinedType

    default = field_info.default

    # default_factory means the value is computed at runtime
    if field_info.default_factory is not None:
        return "*(computed)*"

    if isinstance(default, PydanticUndefinedType):
        return "*(required)*"
    if default is None:
        return "-"
    if isinstance(default, bool):
        return f"`{str(default).lower()}`"
    # Only map int → logging level name for fields explicitly named *logging_level*
    if isinstance(default, int) and "logging_level" in field_name:
        return f"`{logging.getLevelName(default)}`"
    return f"`{default}`"


def _format_config_section(cls, heading: str) -> str:
    """Format one config class as a markdown section."""
    from pydantic import BaseModel

    prefix = _env_prefix(cls)
    docstrings = _field_docstrings(cls)

    lines = [f"## {heading}\n"]

    class_doc = inspect.getdoc(cls)
    if class_doc:
        # Strip the "All env variables must start with..." boilerplate
        first_line = class_doc.splitlines()[0]
        if "All env variables" not in first_line:
            lines.append(first_line + "\n")

    lines.append(f"Prefix: `{prefix}`\n")
    lines.append("| Variable | Default | Description |")
    lines.append("|----------|---------|-------------|")

    for field_name, field_info in cls.model_fields.items():
        # Skip nested model fields — they have their own section
        annotation = field_info.annotation
        try:
            origin = getattr(annotation, "__origin__", None)
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                continue
        except TypeError:
            pass

        env_var = f"`{prefix}{field_name.upper()}`"
        default_str = _config_default_label(field_name, field_info)

        desc = docstrings.get(field_name, "").replace("\n", " ").strip()
        # Trim to first sentence for table readability
        if ". " in desc:
            desc = desc[: desc.index(". ") + 1]

        # Append allowed values for Literal-typed fields
        lit_vals = _literal_values(field_info.annotation)
        if lit_vals:
            vals_str = ", ".join(f"`{v}`" for v in lit_vals)
            desc = (desc.rstrip(".") + ". " if desc else "") + f"One of: {vals_str}."

        # Flag secret fields
        annotation_str = str(field_info.annotation)
        if "SecretStr" in annotation_str:
            default_str = "*(secret)*"

        lines.append(f"| {env_var} | {default_str} | {desc} |")

    lines.append("")
    return "\n".join(lines)


def generate_config_reference() -> str:
    from parxy_core.models.config import (
        LandingAIConfig,
        LlamaParseConfig,
        LlmWhispererConfig,
        ParxyConfig,
        ParxyTracingConfig,
        PdfActConfig,
        UnstructuredLocalConfig,
    )

    frontmatter = (
        "---\n"
        "title: Configuration reference\n"
        "description: Configuration options for Parxy and the drivers. Settings are read from the environment or a .env file. Run parxy env to generate a starter .env with some default.\n"
        "---\n"
    )

    parts = [
        frontmatter,
        GENERATED_NOTICE,
        "# Configuration reference\n",
        "All settings are read from environment variables or a `.env` file in your project root.\n",
        "Run `parxy env` to generate a template `.env` with usual configuration options.\n",
    ]

    sections = [
        (ParxyConfig, "Core settings"),
        (ParxyTracingConfig, "Observability / tracing"),
        (PdfActConfig, "PdfAct"),
        (LlamaParseConfig, "LlamaParse"),
        (LlmWhispererConfig, "LLMWhisperer"),
        (LandingAIConfig, "Landing AI"),
        (UnstructuredLocalConfig, "Unstructured library"),
    ]

    for cls, title in sections:
        parts.append(_format_config_section(cls, title))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    out_dir = ROOT / "docs" / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)

    cli_path = out_dir / "cli.md"
    cli_path.write_text(generate_cli_reference(), encoding="utf-8")
    print(f"  docs/reference/cli.md")

    config_path = out_dir / "configuration.md"
    config_path.write_text(generate_config_reference(), encoding="utf-8")
    print(f"  docs/reference/configuration.md")


if __name__ == "__main__":
    main()
