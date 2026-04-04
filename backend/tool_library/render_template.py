import re


def _resolve(path: str, context: dict):
    """Resolve a dot-notation path against a context dict.

    Returns the value if found, or None.
    """
    parts = path.strip().split(".")
    current = context
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def _is_truthy(value) -> bool:
    """Check if a value is truthy for template conditionals."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _substitute_variables(text: str, context: dict, variables_used: set) -> str:
    """Replace {{variable}} placeholders with values from context."""
    def replacer(match):
        path = match.group(1).strip()
        variables_used.add(path)
        value = _resolve(path, context)
        if value is None:
            return match.group(0)  # Leave unresolved placeholders as-is
        return str(value)

    return re.sub(r"\{\{([^#/{}]+?)\}\}", replacer, text)


def _process_each(template: str, context: dict, variables_used: set) -> str:
    """Process {{#each array}}...{{/each}} blocks."""
    pattern = r"\{\{#each\s+(\S+?)\}\}(.*?)\{\{/each\}\}"

    def replacer(match):
        array_path = match.group(1).strip()
        body = match.group(2)
        variables_used.add(array_path)

        items = _resolve(array_path, context)
        if not isinstance(items, list):
            return ""

        rendered_parts = []
        for index, item in enumerate(items):
            block = body

            # Replace {{#index}} with the current loop index
            block = block.replace("{{#index}}", str(index))

            # Replace {{.property}} references
            def dot_replacer(m):
                dot_path = m.group(1).strip()
                if isinstance(item, dict):
                    val = _resolve(dot_path, item)
                else:
                    val = item
                variables_used.add(f"{array_path}[].{dot_path}")
                return str(val) if val is not None else m.group(0)

            block = re.sub(r"\{\{\.(\S+?)\}\}", dot_replacer, block)

            # Replace {{.}} with the item itself (for simple arrays)
            block = block.replace("{{.}}", str(item))

            # Also substitute top-level variables inside the loop body
            block = _substitute_variables(block, context, variables_used)

            rendered_parts.append(block)

        return "".join(rendered_parts)

    return re.sub(pattern, replacer, template, flags=re.DOTALL)


def _process_conditionals(template: str, context: dict, variables_used: set) -> str:
    """Process {{#if variable}}...{{/if}} blocks."""
    pattern = r"\{\{#if\s+(\S+?)\}\}(.*?)\{\{/if\}\}"

    def replacer(match):
        var_path = match.group(1).strip()
        body = match.group(2)
        variables_used.add(var_path)

        value = _resolve(var_path, context)
        if _is_truthy(value):
            return body
        return ""

    return re.sub(pattern, replacer, template, flags=re.DOTALL)


def render_template(input_data: dict) -> dict:
    """Render a string template with variable substitution and simple conditionals.

    Parameters:
        template (str): Template string with {{variable}} placeholders.
            Supports: {{variable}}, {{#if variable}}...{{/if}},
            {{#each array}}...{{/each}}, {{#index}} (loop index).
        variables (dict): Variables to substitute.

    Returns:
        dict with keys: result, variables_used, error (optional).
    """
    try:
        if not isinstance(input_data, dict):
            return {"result": None, "variables_used": [], "error": "input_data must be a dict"}

        template = input_data.get("template")
        variables = input_data.get("variables")

        if template is None:
            return {"result": None, "variables_used": [], "error": "'template' is required"}

        if not isinstance(template, str):
            return {"result": None, "variables_used": [], "error": "'template' must be a string"}

        if variables is None:
            variables = {}

        if not isinstance(variables, dict):
            return {"result": None, "variables_used": [], "error": "'variables' must be a dict"}

        variables_used = set()
        result = template

        # Process in order: each blocks first (they may contain conditionals and vars),
        # then conditionals, then plain variable substitution.
        # Run multiple passes to handle nesting (up to a reasonable limit).
        for _ in range(10):
            prev = result
            result = _process_each(result, variables, variables_used)
            result = _process_conditionals(result, variables, variables_used)
            result = _substitute_variables(result, variables, variables_used)
            if result == prev:
                break

        return {
            "result": result,
            "variables_used": sorted(variables_used),
        }

    except Exception as exc:
        return {"result": None, "variables_used": [], "error": f"Unexpected error: {exc}"}
