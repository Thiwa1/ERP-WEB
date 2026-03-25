with open('app.py', 'r') as f:
    for i, line in enumerate(f.readlines()):
        if i >= 5130 and i <= 5160:
            print(repr(line))
