import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
result = []

for line in lines:
    if line.strip().startswith('#') and not ("'" in line or '"' in line):
        continue
    
    cleaned_line = re.sub(r'\s+#[^\'\"]*$', '', line).rstrip()
    result.append(cleaned_line)

final_content = '\n'.join(result)

while '\n\n\n' in final_content:
    final_content = final_content.replace('\n\n\n', '\n\n')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(final_content)

print("コメントを削除しました")
