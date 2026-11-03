from analyzer import analyze_code


code = """
try:
    x = 10 / 0
except:
    pass

print("Hello")
"""


issues = analyze_code(code)

print("===== AI SOFTWARE QUALITY ANALYZER =====")

if not issues:
    print("No issues found!")
else:
    for issue in issues:
        print(f"\nType: {issue['type']}")
        print(f"Severity: {issue['severity']}")
        print(f"Message: {issue['message']}")