with open('app.py', 'r') as f:
    content = f.read()

# Let's replace the strict checking logic so it falls back nicely, or tells the user properly.
content = content.replace("flash(f\"Backup tool '{dump_cmd}' not found on the server", "flash(f\"Backup tool '{dump_cmd}' not found on the server")

with open('app.py', 'w') as f:
    f.write(content)
