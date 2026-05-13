"""
Generates demo.cast (asciinema v2) — a scripted terminal demo
showing mcp-code-sanitizer analyzing a vulnerable Python function.
Run: python make_demo.py  ->  demo.cast
Convert: svg-term --in demo.cast --out demo.svg --window
"""
import json

W, H = 110, 34

header = {
    "version": 2, "width": W, "height": H,
    "timestamp": 1747123200,
    "title": "mcp-code-sanitizer — AI code review",
    "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
}

events = []
t = 0.0

R  = "\r\n"
RS = "[0m"
BOLD   = "[1m"
DIM    = "[2m"
RED    = "[38;5;203m"
ORANGE = "[38;5;215m"
YELLOW = "[38;5;220m"
GREEN  = "[38;5;84m"
CYAN   = "[38;5;117m"
PURPLE = "[38;5;141m"
GRAY   = "[38;5;245m"
WHITE  = "[97m"

def o(text, dt=0.0):
    global t
    events.append([round(t, 3), "o", text])
    t += dt

def pause(dt):
    global t
    t += dt

def type_cmd(cmd, char_dt=0.07):
    global t
    o(f"{CYAN}${RS} ")
    for ch in cmd:
        o(ch, char_dt)
    o(R, 0.3)

def hr(char="─", color=GRAY):
    o(f"{color}{char * (W - 2)}{RS}{R}")

# ── start ──────────────────────────────────────────────────────────────────────
pause(0.5)

o(f"{PURPLE}{BOLD}  mcp-code-sanitizer{RS}{GRAY}  AI-powered code review via Groq{RS}{R}", 0.05)
hr()
o(R)
pause(0.6)

# show code being reviewed
o(f"{GRAY}  Analyzing this function:{RS}{R}", 0.04)
o(R)
code_lines = [
    f"{GRAY}  1{RS}  {CYAN}def{RS} {GREEN}login{RS}(username, password):",
    f"{GRAY}  2{RS}      query = {YELLOW}f\"SELECT * FROM users WHERE name='{{username}}' AND pass='{{password}}'\"{RS}",
    f"{GRAY}  3{RS}      user = db.execute(query).fetchone()",
    f"{GRAY}  4{RS}      {CYAN}if{RS} user:",
    f"{GRAY}  5{RS}          token = jwt.encode(user.__dict__, {YELLOW}'secret'{RS})",
    f"{GRAY}  6{RS}          app.logger.info({YELLOW}f\"Login OK: {{username}} pwd={{password}}\"{RS})",
    f"{GRAY}  7{RS}          {CYAN}return{RS} token",
]
for line in code_lines:
    o(f"{line}{R}", 0.05)
o(R)
pause(0.8)

o(f"{GRAY}  Sending to Groq (llama-3.3-70b)...{RS}{R}", 0.04)
pause(2.2)

# results header
o(R)
hr("═", PURPLE)
o(f"{BOLD}{WHITE}  Analysis complete{RS}  {RED}{BOLD}Score: 12 / 100{RS}{R}", 0.03)
hr("═", PURPLE)
o(R)
pause(0.4)

# stat pills
o(f"  {RED}{BOLD} 2 CRITICAL {RS}  {ORANGE}{BOLD} 1 HIGH {RS}  {YELLOW} 0 MEDIUM {RS}  {GREEN} 1 LOW {RS}{R}", 0.03)
o(R)
pause(0.5)

# issue 1
o(f"  {RED}{BOLD}● CRITICAL{RS}  {WHITE}{BOLD}SQL Injection{RS}  {GRAY}line 2{RS}{R}", 0.02)
o(f"  {GRAY}  f-string interpolates user input directly into SQL query.{RS}{R}", 0.02)
o(f"  {GRAY}  Attacker can log in as any user with: {RS}{YELLOW}' OR '1'='1{RS}{R}", 0.02)
o(f"  {DIM}  Fix:{RS}{R}", 0.02)
o(f"  {GRAY}  {GREEN}db.execute({RS}{YELLOW}\"SELECT * FROM users WHERE name=? AND pass=?\"{RS}{GREEN}, (username, password)){RS}{R}", 0.02)
o(R)
pause(0.4)

# issue 2
o(f"  {RED}{BOLD}● CRITICAL{RS}  {WHITE}{BOLD}Hardcoded JWT secret{RS}  {GRAY}line 5{RS}{R}", 0.02)
o(f"  {GRAY}  JWT signed with literal string 'secret'. Anyone can forge tokens.{RS}{R}", 0.02)
o(f"  {DIM}  Fix:{RS}{R}", 0.02)
o(f"  {GRAY}  {GREEN}SECRET = os.getenv({RS}{YELLOW}\"JWT_SECRET\"{RS}{GREEN}){RS}{R}", 0.02)
o(R)
pause(0.4)

# issue 3
o(f"  {ORANGE}{BOLD}● HIGH{RS}  {WHITE}{BOLD}Password exposed in logs{RS}  {GRAY}line 6{RS}{R}", 0.02)
o(f"  {GRAY}  Plaintext password written to application log on every login.{RS}{R}", 0.02)
o(f"  {DIM}  Fix:{RS}{R}", 0.02)
o(f"  {GRAY}  {GREEN}app.logger.info({RS}{YELLOW}f\"Login OK: {{username}}\"{RS}{GREEN}){RS}{R}", 0.02)
o(R)
pause(0.4)

# suggestion
o(f"  {GREEN}✓ LOW{RS}  {WHITE}Use parameterized queries across the codebase{RS}{R}", 0.02)
o(R)
pause(0.4)

hr("─", GRAY)
o(f"  {GREEN}Report saved → {CYAN}report.html{RS}{R}", 0.03)
o(R)
pause(1.5)

# second command — generate_tests
type_cmd("python demo.py generate_tests", 0.07)
pause(0.3)
o(f"{GRAY}  Generating pytest suite...{RS}{R}", 0.03)
pause(2.0)
o(R)
o(f"  {GREEN}{BOLD}Generated 6 test cases:{RS}{R}", 0.02)
o(R)

tests = [
    ("happy_path",  GREEN,  "test_login_valid_credentials"),
    ("security",    RED,    "test_login_sql_injection_blocked"),
    ("security",    RED,    "test_login_or_always_true_blocked"),
    ("edge_case",   YELLOW, "test_login_empty_password"),
    ("edge_case",   YELLOW, "test_login_special_chars"),
    ("error_case",  ORANGE, "test_login_db_unavailable"),
]
for kind, color, name in tests:
    o(f"  {color}[{kind}]{RS}  {WHITE}{name}{RS}{R}", 0.05)
o(R)
pause(1.8)

# footer
hr("─", GRAY)
o(f"  {GRAY}github.com/notasandy/mcp-code-sanitizer  ·  powered by Groq (free){RS}{R}", 0.02)
o(R)
pause(1.0)

# write file
lines = [json.dumps(header, ensure_ascii=True)]
for ev in events:
    lines.append(json.dumps(ev, ensure_ascii=True, separators=(",", ":")))

with open("demo.cast", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Written demo.cast  ({len(events)} events, {round(t, 1)}s)")
