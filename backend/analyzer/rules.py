"""Detection rules for JavaScript and Python.

Every rule has:
  * a category and a default severity (the prior),
  * a short `description` that the ML severity model reads,
  * a plain-language explanation (`why`) and a suggested fix,
  * a test that looks at one line, with the cleaned file as context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .parsing import FN_START, block_end, max_depth


@dataclass(frozen=True)
class Rule:
    id: str
    lang: str  # "js", "py" or "any"
    category: str
    severity: str
    title: str
    description: str
    why: str
    fix: str
    fix_code: str
    test: Callable  # (clean_line, raw_line, index, ctx) -> bool


class Context:
    def __init__(self, raw: list[str], clean: list[str], lang: str):
        self.raw, self.clean, self.lang = raw, clean, lang


def on_clean(pattern: str, flags: int = 0):
    rx = re.compile(pattern, flags)
    return lambda c, raw, i, ctx: bool(rx.search(c))


def on_raw(pattern: str, flags: int = 0):
    rx = re.compile(pattern, flags)
    return lambda c, raw, i, ctx: bool(rx.search(raw))


_SQL_WORD = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.I)
_SQL_CALL = re.compile(r"(execute|query)\s*\(", re.I)
_SQL_BUILT = [
    re.compile(r"""["'`]\s*\+\s*\w"""),
    re.compile(r"\$\{"),
    re.compile(r"""\bf["']"""),
    re.compile(r"""["']\s*%\s*\w"""),
]


def _sql_from_strings(c, raw, i, ctx):
    return bool(_SQL_WORD.search(raw) and _SQL_CALL.search(raw) and any(p.search(raw) for p in _SQL_BUILT))


_EXCEPT_LINE = re.compile(r"^\s*except\s+[\w.(), ]+(?:\s+as\s+\w+)?\s*:\s*$")


def _except_pass(c, raw, i, ctx):
    return bool(_EXCEPT_LINE.search(c)) and i + 1 < len(ctx.clean) and ctx.clean[i + 1].strip() == "pass"


_THEN = re.compile(r"\.then\s*\(")
_CATCH = re.compile(r"\.catch\s*\(")


def _promise_without_catch(c, raw, i, ctx):
    return bool(_THEN.search(c)) and not any(_CATCH.search(line) for line in ctx.clean[i : i + 5])


_LOOP_OPEN = re.compile(r"^\s*(?:for|while)\b.*\{\s*$")
_AWAIT = re.compile(r"\bawait\b")


def _await_in_loop(c, raw, i, ctx):
    if not _LOOP_OPEN.search(c):
        return False
    end = block_end(ctx.clean, i, "js")
    return any(_AWAIT.search(line) for line in ctx.clean[i + 1 : end + 1])


def _deeply_nested(c, raw, i, ctx):
    if not FN_START[ctx.lang].search(c):
        return False
    return max_depth(ctx.clean, i, block_end(ctx.clean, i, ctx.lang), ctx.lang) >= 5


def _long_function(c, raw, i, ctx):
    if not FN_START[ctx.lang].search(c):
        return False
    return block_end(ctx.clean, i, ctx.lang) - i + 1 > 40


RULES: list[Rule] = [
    Rule(
        "eval", "any", "Security", "critical", "Use of eval()",
        "remote code execution through eval of untrusted user input",
        "eval() runs a string as code. If any part of that string comes from a user, an attacker can run their own code in your application.",
        "Remove eval. Parse the data you expect (for example JSON.parse) or look the action up in a fixed table of allowed functions.",
        "const actions = { applyDiscount };\nconst fn = actions[name];\nif (fn) fn(code);",
        on_clean(r"(?<![.\w])eval\s*\("),
    ),
    Rule(
        "exec", "py", "Security", "critical", "Use of exec()",
        "remote code execution through eval of untrusted user input",
        "exec() runs a string as Python code, so any user-controlled text becomes remote code execution.",
        "Replace exec with explicit function calls or a dispatch dictionary of allowed operations.",
        'ACTIONS = {"backup": run_backup}\nACTIONS[name](arg)',
        on_clean(r"(?<![.\w])exec\s*\("),
    ),
    Rule(
        "secret", "any", "Security", "critical", "Hardcoded secret",
        "hardcoded production database password committed to the repository",
        "Secrets in source control are copied into every clone, build and backup, and cannot be rotated without a code change.",
        "Load the value from an environment variable or a secrets manager, and rotate the exposed credential now.",
        'DB_PASSWORD = os.environ["DB_PASSWORD"]',
        on_raw(r"""(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*["'][^"']{6,}["']""", re.I),
    ),
    Rule(
        "sqli", "any", "Security", "critical", "SQL built from strings",
        "sql injection lets an attacker dump the users table",
        "Joining user input into a SQL string lets an attacker change the query, for example to bypass a login or read other tables.",
        "Use parameterized queries so the database treats input as data, never as SQL.",
        'cur.execute("SELECT * FROM users WHERE name = ? AND pw = ?", (username, password))',
        _sql_from_strings,
    ),
    Rule(
        "shell", "py", "Security", "high", "Shell command from variables",
        "shell command injection through os system with user supplied filename",
        'os.system and shell=True pass the whole string to a shell. A crafted name such as "x; rm -rf /" runs extra commands.',
        "Call subprocess.run with a list of arguments and without shell=True.",
        'subprocess.run(["tar", "czf", name + ".tgz", "data/"], check=True)',
        on_clean(r"os\.system\s*\(|shell\s*=\s*True"),
    ),
    Rule(
        "pickle", "py", "Security", "high", "Unsafe deserialization (pickle)",
        "unsafe deserialization of untrusted data executes arbitrary commands",
        "Unpickling data can run arbitrary code. It is only safe for data you created and fully trust.",
        "Use a data-only format such as JSON, or sign and verify the data before loading it.",
        "import json\ndata = json.loads(f.read())",
        on_clean(r"pickle\.loads?\s*\("),
    ),
    Rule(
        "innerhtml", "js", "Security", "high", "Unescaped innerHTML",
        "cross site scripting through innerHTML with user supplied comment",
        "Assigning text to innerHTML parses it as HTML. A comment containing a script tag or an onerror attribute runs in other users' browsers.",
        "Use textContent for plain text, or sanitize the HTML with a vetted library before inserting it.",
        "el.textContent = userComment;",
        on_clean(r"\.innerHTML\s*=(?!=)"),
    ),
    Rule(
        "assign-cond", "js", "Logic", "high", "Assignment inside a condition",
        "assignment used instead of comparison in the access check",
        "A single = assigns a value, so the condition is always true for a non-empty value and the variable is silently overwritten.",
        "Use === to compare. If the assignment is intentional, do it on its own line first.",
        'if (user.role === "admin") {',
        on_clean(r"\b(?:if|while)\s*\(\s*[\w$.\[\]]+\s*=(?!=)"),
    ),
    Rule(
        "offbyone", "js", "Logic", "high", "Off-by-one loop bound",
        "off by one error skips the last record",
        "Indexes run from 0 to length - 1. Looping while i <= length reads one element past the end, which is undefined and often throws.",
        "Use i < array.length, or iterate with for...of so no index is needed.",
        "for (const item of items) {\n  total += item.price * item.qty;\n}",
        on_clean(r"\bfor\s*\([^;]*;\s*[\w$]+\s*<=\s*[\w$.]+\.length\s*;"),
    ),
    Rule(
        "mutable-default", "py", "Logic", "high", "Mutable default argument",
        "mutable default argument shares state between requests",
        "The default list or dict is created once and reused by every call, so data from one call leaks into the next.",
        "Default to None and create a fresh object inside the function.",
        "def export_rows(rows, seen=None):\n    seen = [] if seen is None else seen",
        on_clean(r"\bdef\s+\w+\s*\([^)]*=\s*(?:\[\]|\{\}|set\(\))"),
    ),
    Rule(
        "empty-catch", "js", "Error handling", "medium", "Empty catch block",
        "empty catch block hides errors and makes failures hard to diagnose",
        "The error is swallowed, so a failed save looks like a success and nobody learns why data is missing.",
        "Log the error with context and either recover or rethrow it.",
        'catch (err) {\n  logger.error("saveOrder failed", err);\n  throw err;\n}',
        on_clean(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}"),
    ),
    Rule(
        "bare-except", "py", "Error handling", "medium", "Bare except clause",
        "bare except swallows keyboard interrupt and real errors",
        "A bare except also catches KeyboardInterrupt and SystemExit, and hides programming mistakes such as typos.",
        "Catch the specific exceptions you can handle, and log them.",
        'except (KeyError, ConnectionError) as err:\n    logger.warning("profile lookup failed: %s", err)',
        on_clean(r"^\s*except\s*:"),
    ),
    Rule(
        "except-pass", "py", "Error handling", "medium", "Exception ignored silently",
        "exception caught and ignored hides real errors and makes failures hard to diagnose",
        "Catching an exception and doing nothing hides the failure and leaves the program in an unknown state.",
        "Handle the error or log it. Use contextlib.suppress only for errors you expect.",
        'except ValueError as err:\n    logger.warning("bad value: %s", err)',
        _except_pass,
    ),
    Rule(
        "promise-no-catch", "js", "Error handling", "medium", "Promise without error handling",
        "unhandled promise rejection stops the sync",
        "If the request fails, the rejection is unhandled. Modern Node exits on it and browsers log an error while the UI waits forever.",
        "Add .catch(), or use async/await inside try/catch.",
        'fetch("/api/prices")\n  .then(r => r.json())\n  .then(render)\n  .catch(showError);',
        _promise_without_catch,
    ),
    Rule(
        "int-input", "py", "Error handling", "medium", "Unvalidated numeric input",
        "missing input validation crashes the program on bad user input",
        "int() and float() raise ValueError when the user types anything that is not a number, so the program crashes instead of asking again.",
        "Wrap the conversion in try/except ValueError and ask again.",
        'while True:\n    try:\n        age = int(input("Enter your age: "))\n        break\n    except ValueError:\n        print("Please enter a whole number.")',
        on_clean(r"\b(?:int|float)\s*\(\s*input\s*\("),
    ),
    Rule(
        "await-in-loop", "js", "Performance", "medium", "await inside a loop",
        "slow requests run one after another in a loop causing noticeable latency",
        "Each iteration waits for the previous request, so total time is the sum of all requests instead of the slowest one.",
        "Start the requests together with Promise.all when they do not depend on each other.",
        "const carts = await Promise.all(userIds.map(fetchCart));",
        _await_in_loop,
    ),
    Rule(
        "open-no-with", "py", "Resource management", "medium", 'File opened without "with"',
        "file handle not closed leaks resources slowly",
        "If an exception happens before close(), the file stays open. Repeated leaks eventually exhaust file handles.",
        "Open files in a with block so they close automatically.",
        'with open("report.csv", "w") as out:\n    out.write(data)',
        on_clean(r"^\s*\w+\s*=\s*open\s*\("),
    ),
    Rule(
        "nesting", "any", "Maintainability", "medium", "Deeply nested function",
        "deeply nested conditions make the function hard to test",
        "Four or more nested levels are hard to read and need many test cases to cover every path.",
        "Return early, flatten conditions, or move the inner loop into a helper function.",
        "if (!rule.active) continue;\nfor (const item of matching(order, rule)) {\n  item.qty = Math.min(item.qty, rule.limit);\n}",
        _deeply_nested,
    ),
    Rule(
        "longfn", "any", "Maintainability", "medium", "Very long function",
        "function is very long and does several unrelated things",
        "Functions over 40 lines usually mix several jobs, which makes bugs harder to find and changes riskier.",
        "Split the function by responsibility and give each part a clear name.",
        "function checkout(order) {\n  validate(order);\n  const total = price(order);\n  return charge(order, total);\n}",
        _long_function,
    ),
    Rule(
        "loose-eq", "js", "Code quality", "low", "Loose equality (==)",
        "loose equality used where strict equality is clearer",
        '== converts types before comparing, so "0" == 0 is true. That produces surprising results.',
        "Use === and !==. To test for null or undefined together, write value === null || value === undefined.",
        "return user.id === 1;",
        on_clean(r"(?<![=!<>])==(?!=)|!=(?!=)"),
    ),
    Rule(
        "none-eq", "py", "Code quality", "low", "Comparison to None with ==",
        "loose equality operator used where is none is clearer",
        "Objects can override ==, so == None can be wrong. None is a singleton and should be tested by identity.",
        'Write "is None" or "is not None".',
        "if row is None:",
        on_clean(r"[=!]=\s*None\b"),
    ),
    Rule(
        "var", "js", "Code quality", "low", "var declaration",
        "variable declared with var instead of let",
        "var is function-scoped and hoisted, which causes bugs in loops and closures.",
        "Use const by default and let when the value changes.",
        "const TAX_RATE = 0.18;",
        on_clean(r"(^|[\s(;])var\s+\w"),
    ),
    Rule(
        "console", "js", "Code quality", "low", "console.log left in code",
        "console log left in production code",
        "Debug output slows hot paths and can leak data into browser consoles and logs.",
        "Remove it, or use a logger with levels that is turned off in production.",
        'logger.debug("total", total);',
        on_clean(r"\bconsole\.(?:log|debug)\s*\("),
    ),
    Rule(
        "print", "py", "Code quality", "low", "print() used for output",
        "print statement used for debugging",
        "print has no levels or timestamps and cannot be filtered in production.",
        "Use the logging module.",
        'logger.info("exported %d rows", len(rows))',
        on_clean(r"^\s*print\s*\("),
    ),
    Rule(
        "parseint", "js", "Code quality", "low", "parseInt without radix",
        "parseInt without radix can give surprising results",
        "Without a radix, strings with prefixes such as 0x are parsed differently. Always state the base.",
        "Pass 10 as the second argument, or use Number(value) when the whole string must be numeric.",
        "return parseInt(input.trim(), 10);",
        on_clean(r"\bparseInt\s*\((?:[^(),]|\([^()]*\))*\)"),
    ),
    Rule(
        "star-import", "py", "Code quality", "low", "Wildcard import",
        "unused names from star import clutter the module",
        "A star import pulls every name into the file, hides where names come from and can overwrite existing ones.",
        "Import only the names you use.",
        "from config import DB_PATH, TIMEOUT",
        on_clean(r"^\s*from\s+\S+\s+import\s+\*"),
    ),
    Rule(
        "todo", "any", "Maintainability", "low", "Unfinished work marker",
        "todo comment left in a helper function",
        "TODO and FIXME notes mark work that was meant to be finished and are easy to forget.",
        "Turn it into a tracked issue and link it in the comment, or finish it now.",
        "// TODO(#128): debounce quantity updates",
        on_raw(r"\b(?:TODO|FIXME|HACK)\b"),
    ),
]

RULES_BY_ID = {r.id: r for r in RULES}
