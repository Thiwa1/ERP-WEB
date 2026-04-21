plan = """1. **Fix hardcoded currency symbol in Receipt Reversal Modal**: Replace the hardcoded `$` in `templates/customer_receipt.html` with `{{ company_currency }} ` so it inherits the correct currency configured in the system.
2. **Review frontend changes**: Verify `customer_receipt.html` is properly updated.
3. **Complete pre commit steps**: Run `pre_commit_instructions` to ensure code quality checks and tests pass.
4. **Submit changes**: Push to the branch."""
print(plan)
