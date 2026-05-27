import re

with open('apps/emissions/management/commands/seed_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace 2024 -> 2026
content = content.replace('2024', '2026')
# Replace 2023 -> 2025
content = content.replace('2023', '2025')
# Replace 2022 -> 2024
content = content.replace('2022', '2024')

with open('apps/emissions/management/commands/seed_data.py', 'w', encoding='utf-8') as f:
    f.write(content)
