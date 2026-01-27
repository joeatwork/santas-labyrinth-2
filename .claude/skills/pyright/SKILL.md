---
name: pyright
description: Use pyright to check Python code for type errors and navigate the codebase. Use this when the user asks to check types, find definitions, find references, or navigate Python code.
argument-hint: [check|def|refs|type] [file-or-symbol]
---

# Pyright Python Navigation and Type Checking

You are helping the user navigate and check Python code using pyright and related tools.

## Commands

Parse `$ARGUMENTS` to determine the action:

| Pattern | Action |
|---------|--------|
| (empty) or `check` | Check entire project for type errors |
| `check <file>` | Check specific file(s) for type errors |
| `def <symbol>` | Find definition of a symbol (class, function, variable) |
| `refs <symbol>` | Find all references to a symbol |
| `type <file>:<line>` | Show type information at a specific location |

## Type Checking

Run pyright with JSON output for structured results:

```bash
pyright --outputjson [files...]
```

Parse the JSON output and present errors clearly:
- Group by file
- Show line number, message, and severity
- Summarize total errors/warnings

For quick checks without JSON:
```bash
pyright [files...]
```

## Finding Definitions

To find where a symbol is defined:

1. **For classes**: Search for `class <SymbolName>` pattern
2. **For functions**: Search for `def <symbol_name>` pattern
3. **For variables/constants**: Search for `<SYMBOL_NAME> =` at module level
4. **For imports**: Trace the import chain

Use Grep with patterns like:
- `class SymbolName\b` - class definition
- `def symbol_name\b` - function definition
- `^[A-Z_]+ =` - module-level constants

After finding candidates, read the file to confirm and show context.

## Finding References

To find all usages of a symbol:

1. Use Grep to search for the symbol name
2. Filter out the definition itself
3. Show each reference with file:line and surrounding context

```bash
# Example pattern for finding references
rg -n "\bsymbol_name\b" --type py
```

## Type Information

For type info at a location, use pyright's analysis. If the user wants hover-like info:

1. Run pyright on the file to ensure it's analyzed
2. Look at the symbol at that line
3. Describe the inferred or declared type based on context

## Best Practices

- Always show file paths relative to project root
- Include line numbers for easy navigation
- When showing definitions, include a few lines of context
- For large result sets, summarize and offer to show more
- If pyright reports errors, explain what they mean

## Example Outputs

**Type check results:**
```
Found 3 type errors in 2 files:

dungeon/world.py:45 - Argument of type "str" cannot be assigned to parameter "x" of type "int"
dungeon/world.py:67 - "foo" is not a known member of "Hero"
dungeon/animation.py:23 - Missing return statement
```

**Definition found:**
```
Found definition of `Hero` at dungeon/world.py:89

class Hero:
    """The player character that navigates the dungeon."""
    def __init__(self, dungeon: Dungeon, strategy: Strategy):
        ...
```

**References found:**
```
Found 12 references to `Hero`:

dungeon/world.py:89      - class Hero:  (definition)
dungeon/world.py:156     - hero = Hero(dungeon, strategy)
content.py:234           - self.hero: Hero = Hero(...)
tests/test_hero.py:15    - from dungeon.world import Hero
...
```
