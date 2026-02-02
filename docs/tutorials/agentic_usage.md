# Agentic Usage

You can use Parxy with AI coding assistants such as Claude Code, GitHub Copilot, Cursor, and other AI-powered development tools.

## Overview

Parxy provides a CLI command to generate documentation that helps AI agents understand how to use Parxy effectively within your codebase.

### AGENTS.md

[`AGENTS.md`](https://agents.md/) is a file used to guide coding agents. It provides code examples and precise instructions for agents. The `AGENTS.md` file is always loaded into the coding agent’s context.

To set up `AGENTS.md`, or to update an existing file with Parxy-specific instructions, run:

```bash
parxy agents
```

The `AGENTS.md` file contains:

* Quick-start examples for parsing documents
* Available drivers and their use cases
* Explanations of extraction levels
* Document model usage patterns
* CLI command references
* Configuration environment variables
* Common tasks and code snippets
* Error-handling patterns

The Parxy-specific content is wrapped in `<parxy>` tags, allowing you to maintain your own project documentation alongside Parxy instructions.

When Parxy releases new features, you can update your agent documentation by running:

```bash
parxy agents --overwrite
```

This updates only the `<parxy>` section while preserving any custom content you have added to `AGENTS.md`.

### Skills

[Skills](https://agentskills.io/what-are-skills) are specialized workflows and instructions. They are used to progressively disclose information to agents, rather than filling the available context space. A skill may not be read by a coding agent if it is considered irrelevant.

You can add Parxy skills using the [skillsmd CLI](https://github.com/avvertix/skillsmd):

```bash
uvx skillsmd add https://github.com/OneOffTech/parxy
```

## Troubleshooting

### AI Not Finding Parxy Documentation

Ensure that `AGENTS.md` is located in the project root or in a directory scanned by your AI tool. Most tools look for:

* `AGENTS.md` in the project root
* `.github/AGENTS.md`
* `docs/AGENTS.md`

### Skills Not Appearing

Verify that the skills directory exists:

```bash
ls -la .claude/skills/
```

Restart Claude Code after adding new skills.

### Outdated Instructions

If AI suggestions seem outdated, update the Parxy section by running:

```bash
parxy agents --overwrite
```

## See Also

* [Getting Started Tutorial](./getting_started.md)
* [CLI Usage Guide](./using_cli.md)
* [Driver Configuration Guides](../howto/configure_pymupdf.md)
