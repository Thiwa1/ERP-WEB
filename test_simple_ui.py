from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('index.html')
# Render dummy
try:
    rendered = template.render(request={'path': '/'}, current_theme={'primary': '#000', 'secondary': '#000', 'accent': '#000'}, app_config={}, session={'user_id': 'ADM001'})
    print("Base template and Index template compiled and rendered successfully!")

    if "PRO VERSION" in rendered:
        print("Pro Version Footer found in rendered HTML!")

    if "Proforma Inv" in rendered:
        print("Proforma Inv Quick Action link found in rendered HTML!")
except Exception as e:
    print(f"Error rendering: {e}")
