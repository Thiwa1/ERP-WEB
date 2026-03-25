with open('app.py', 'r') as f:
    for i, line in enumerate(f.readlines()):
        if i >= 5285 and i <= 5295:
            print(repr(line))
