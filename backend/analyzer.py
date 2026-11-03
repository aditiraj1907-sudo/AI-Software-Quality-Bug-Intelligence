import ast


def analyze_code(code):
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        issues.append({
            "type": "Syntax Error",
            "severity": "Critical",
            "message": f"Invalid Python syntax at line {error.lineno}"
        })

        return issues

    for node in ast.walk(tree):

        # Detect empty except blocks
        if isinstance(node, ast.ExceptHandler):
            if node.body and isinstance(node.body[0], ast.Pass):
                issues.append({
                    "type": "Code Quality",
                    "severity": "Medium",
                    "message": f"Empty exception handler at line {node.lineno}"
                })

        # Detect print statements
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                issues.append({
                    "type": "Code Quality",
                    "severity": "Low",
                    "message": f"Print statement found at line {node.lineno}"
                })

    return issues