import re

# Extrair emails
text = "Contact: email@site.com, otehr@mail.org"
emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)

# Validar padrões
if re.match(r'^\d{3}-\d{2}-\d{4}$', ssn):
    process_ssn(ssn)
    