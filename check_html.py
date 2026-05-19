with open('templates/index.html', encoding='utf-8') as f:
    content = f.read()

checks = [
    ('Neural default active',  'id="neural-container" class="active"'),
    ('Chat hidden by default', 'class="main-container" id="main-container"'),
    ('Single toggle checked',  'id="mode-switch" checked'),
    ('toggleMode function',    'function toggleMode()'),
    ('closing html tag',       '</html>'),
]
for name, marker in checks:
    status = 'OK' if marker in content else 'MISSING'
    print(f'  {name}: {status}')

hud = 'class="hud-header"' in content
print(f'  Old hud-header removed: {"NO - still present" if hud else "YES - clean"}')
print(f'  Total lines: {content.count(chr(10))}')
