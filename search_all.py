import os
for root, dirs, files in os.walk('/app'):
    for f in files:
        if f.endswith('.md') or f.endswith('.txt') or f.endswith('.py'):
            with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                try:
                    c = file.read()
                    if 'api_key' in c.lower() and 'notify.lk' in c.lower():
                        print(f"Found in {f}")
                except:
                    pass
