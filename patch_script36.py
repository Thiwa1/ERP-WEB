with open("profit_loss_report.py", "r") as f:
    lines = f.readlines()

new_code = """
        total_income = [0.0] * len(periods)
        total_expense = [0.0] * len(periods)

        for cat in income_categories:
            cat['total'] = [0.0] * len(periods)
            for acc in cat['accounts']:
                for i, v in enumerate(acc['amounts']):
                    cat['total'][i] += v
                    total_income[i] += v

        for cat in expense_categories:
            cat['total'] = [0.0] * len(periods)
            for acc in cat['accounts']:
                for i, v in enumerate(acc['amounts']):
                    cat['total'][i] += v
                    total_expense[i] += v
"""

for i, line in enumerate(lines):
    if "for cat in income_categories:" in line:
        start_idx = i
        break

for i in range(start_idx, len(lines)):
    if "net_profit = " in lines[i]:
        end_idx = i
        break

with open("profit_loss_report.py", "w") as f:
    f.writelines(lines[:start_idx] + [new_code] + lines[end_idx:])
