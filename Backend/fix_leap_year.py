import re

with open('apps/emissions/management/commands/seed_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('date(2026,2,29)', 'date(2026,2,28)')

with open('apps/emissions/management/commands/seed_data.py', 'w', encoding='utf-8') as f:
    f.write(content)
