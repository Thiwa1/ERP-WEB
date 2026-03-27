import re

text1 = "VAT REGISTRATION NO: 123456789"
text2 = "VAT NO: GB123456789"
text3 = "VAT NUMBER: 987654321"
text4 = "VAT: 12345"

vat_pattern = r'(?i)VAT\s*(?:REGISTRATION\s*)?(?:NO|NUMBER|#)?\s*[:\-\s]?\s*([A-Z0-9]{8,15})'

print(re.findall(vat_pattern, text1))
print(re.findall(vat_pattern, text2))

# Wait, if we use [A-Z0-9]{8,15} it can still match "CERTIFICATE".
# So we need to ensure the captured group has at least one digit or looks like a VAT number.
# A VAT number typically starts with an optional 2-letter country code, then digits, and maybe some more letters/digits.
# Better pattern:
# (?i)VAT\s*(?:REGISTRATION\s*)?(?:NO|NUMBER|#)?\s*[:\-\s]*([A-Z]{0,2}\d[A-Z0-9]{4,14})

vat_pattern_better = r'(?i)VAT\s*(?:REGISTRATION\s*)?(?:NO\.|NO|NUMBER|#)?\s*[:\-\s]*([A-Z]{0,2}\d[A-Z0-9]{4,14})'
print("Better:", re.findall(vat_pattern_better, text1))
print("Better:", re.findall(vat_pattern_better, text2))
print("Better:", re.findall(vat_pattern_better, text3))
print("Better:", re.findall(vat_pattern_better, text4))

# Let's write a function that extracts and then filters out purely alphabetical strings.
