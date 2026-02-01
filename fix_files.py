import pathlib

# Fix test_analysis.py
path = pathlib.Path('examples/test_analysis.py')
content = path.read_text()

# Replace print_cfg() with print(cfg)
lines = []
for line in content.split('\n'):
    if 'cfg.print_cfg()' in line:
        indent = line[:len(line) - len(line.lstrip())]
        lines.append(indent + 'print(cfg)')
    elif '.entry =' in line and 'cfg' in line:
        lines.append(line.replace('.entry =', '.entry_label ='))
    else:
        lines.append(line)

path.write_text('\n'.join(lines))
print('Fixed test_analysis.py')

# Fix demo_analysis.py
path2 = pathlib.Path('examples/demo_analysis.py')
content2 = path2.read_text()

lines2 = []
for line in content2.split('\n'):
    if 'cfg.print_cfg()' in line:
        indent = line[:len(line) - len(line.lstrip())]
        lines2.append(indent + 'print(cfg)')
    elif '.entry =' in line and 'cfg' in line:
        lines2.append(line.replace('.entry =', '.entry_label ='))
    else:
        lines2.append(line)

path2.write_text('\n'.join(lines2))
print('Fixed demo_analysis.py')
