---
description: "Use when adding Google-style docstrings to Python modules."
argument-hint: "Python file, module, or selection to document"
agent: "agent"
---
Inspect the current Python file, module, or selected code and add or complete Google-style docstrings.

Requirements:
- Add concise, accurate docstrings to public classes, functions, and methods that are missing them.
- Preserve existing behavior and avoid unrelated refactors.
- For classes, include constructor arguments in the class docstring under `Args:` when the constructor defines the initialization contract.
- Do not add a docstring to `__init__` when the constructor contract is already documented on the class.
- Include `Attributes:` in class docstrings only for meaningful public instance attributes.
- Include `Args:`, `Returns:`, `Yields:`, and `Raises:` sections where they apply.
- Keep private helpers undocumented unless the file already documents them consistently or the task specifically requires it.
- Do not document private attributes in `Attributes:` sections.
- Match the repository's existing style and linter expectations.
- Clean up any docstring-related whitespace or formatting issues introduced during the edit.
- Validate the edited file and fix any diagnostics caused by the change.

When responding:
- Make the code changes directly.
- Keep the patch minimal.
- Summarize what was documented and note any remaining issues if validation fails.
