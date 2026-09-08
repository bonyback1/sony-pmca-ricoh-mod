import xml.etree.ElementTree as ET
import re
import argparse
import os
import sys

FILTERS = {
    'pop-color': ('理光 GR 正片', '理光 GR 正片'),
    'retro-photo': ('理光负片', '理光负片'),
    'richtone-mono': ('高对比黑白', '高对比黑白'),
    'rough-mono': ('森山大道风', '森山大道风'),
    'watercolor': ('正负逆冲', '正负逆冲')
}

def update_menu_data(menu_file):
    if not os.path.exists(menu_file):
        raise FileNotFoundError(f"Menu file not found: {menu_file}")


    with open(menu_file, 'r', encoding='utf-8') as f:
        content = f.read()

    for item_id, (title, disp_name) in FILTERS.items():
        # Match Layer2 block for item_id
        pattern = rf'(<Layer2\b[^>]*ItemId="{item_id}"[^>]*>)'
        m = re.search(pattern, content)
        if not m:
            # Check if ItemId comes later in attributes
            pattern = rf'(<Layer2\b(?=[^>]*ItemId="{item_id}")[^>]*>)'
            m = re.search(pattern, content)
        
        if m:
            tag = m.group(1)
            # Update Title
            if 'Title="' in tag:
                tag = re.sub(r'Title="[^"]*"', f'Title="{title}"', tag)
            else:
                tag = tag[:-1] + f' Title="{title}">'
                
            # Update DisplayName
            if 'DisplayName="' in tag:
                tag = re.sub(r'DisplayName="[^"]*"', f'DisplayName="{disp_name}"', tag)
            else:
                tag = tag[:-1] + f' DisplayName="{disp_name}">'
                
            # Set NextMenuID="" so it applies directly without submenu
            if 'NextMenuID="' in tag:
                tag = re.sub(r'NextMenuID="[^"]*"', 'NextMenuID=""', tag)
                
            content = content[:m.start(1)] + tag + content[m.end(1):]
            print(f'Updated {item_id} -> Title: {title}')
        else:
            print(f'Warning: Could not find Layer2 for {item_id}')

    with open(menu_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'MenuData updated successfully: {menu_file}')

def main():
    parser = argparse.ArgumentParser(description="Update MenuData.xml filter titles to Ricoh presets")
    parser.add_argument('menu_file', help="Path to assets/MenuData.xml")
    args = parser.parse_args()
    update_menu_data(args.menu_file)

if __name__ == '__main__':
    main()

