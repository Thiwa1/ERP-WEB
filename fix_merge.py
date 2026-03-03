with open('app.py', 'r') as f:
    lines = f.readlines()

with open('app.py', 'w') as f:
    for line in lines:
        if line == 'from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, Response, stream_with_context\n':
            continue
        f.write(line)
