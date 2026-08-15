import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier si le fichier contient des requêtes SQL avec ?
    if '?' not in content or 'cursor.execute' not in content:
        return False
    
    # Ajouter l'import si nécessaire
    if 'from app import execute_query' not in content:
        # Trouver la position pour insérer l'import
        import_pattern = r'(from app import [^\n]+)'
        match = re.search(import_pattern, content)
        if match:
            # Ajouter execute_query à l'import existant
            old_import = match.group(1)
            if 'execute_query' not in old_import:
                new_import = old_import.rstrip(')') + ', execute_query)'
                content = content.replace(old_import, new_import)
        else:
            # Ajouter un nouvel import après les autres imports
            import_line = 'from app import execute_query\n'
            # Insérer après le dernier import
            lines = content.split('\n')
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    last_import_idx = i
            lines.insert(last_import_idx + 1, import_line.rstrip())
            content = '\n'.join(lines)
    
    # Remplacer cursor.execute par execute_query
    # Pattern: cursor.execute("...", (...))
    pattern = r'cursor\.execute\((".*?"),\s*\((.*?)\)\)'
    
    def replace_func(match):
        query = match.group(1)
        params = match.group(2)
        return f'cursor, conn = execute_query({query}, ({params},))'
    
    new_content = re.sub(pattern, replace_func, content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

# Parcourir tous les fichiers Python dans app/
for root, dirs, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            if fix_file(filepath):
                print(f"✅ Corrigé : {filepath}")