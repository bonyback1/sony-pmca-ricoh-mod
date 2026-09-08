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

RICOH_ORDER = ['pop-color', 'retro-photo', 'richtone-mono', 'rough-mono', 'watercolor']

def update_menu_data(menu_file):
    if not os.path.exists(menu_file):
        raise FileNotFoundError(f"Menu file not found: {menu_file}")

    with open(menu_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update each Ricoh filter tag attributes (Title, DisplayName, NextMenuID="", ExecType="SET_VALUE")
    for item_id, (title, disp_name) in FILTERS.items():
        pattern = rf'(<Layer2\b(?=[^>]*ItemId="{item_id}")[^>]*>)'
        m = re.search(pattern, content)
        if not m:
            pattern = rf'(<Layer2\b[^>]*ItemId="{item_id}"[^>]*>)'
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

            # Ensure ExecType="SET_VALUE"
            if 'ExecType="' in tag:
                tag = re.sub(r'ExecType="[^"]*"', 'ExecType="SET_VALUE"', tag)

            content = content[:m.start(1)] + tag + content[m.end(1):]
            print(f'Updated {item_id} -> Title: {title}')
        else:
            print(f'Warning: Could not find Layer2 for {item_id}')

    # 2. Reorder Layer2 blocks inside ApplicationTop so Ricoh presets are at the very top (0..4)
    app_top_match = re.search(r'(<Layer1\b[^>]*ItemId="ApplicationTop"[^>]*>)([\s\S]*?)(</Layer1>)', content)
    if app_top_match:
        body = app_top_match.group(2)
        layer2_blocks = list(re.finditer(r'(<Layer2\b[\s\S]*?</Layer2>)', body))
        block_map = {}
        other_blocks = []

        for b in layer2_blocks:
            b_text = b.group(1)
            id_m = re.search(r'ItemId="([^"]+)"', b_text)
            item_id = id_m.group(1) if id_m else None
            if item_id in RICOH_ORDER:
                block_map[item_id] = b_text
            else:
                other_blocks.append(b_text)

        if len(block_map) == len(RICOH_ORDER):
            new_body = "\n" + "\n".join([block_map[k] for k in RICOH_ORDER]) + "\n" + "\n".join(other_blocks) + "\n"
            content = content[:app_top_match.start(2)] + new_body + content[app_top_match.end(2):]
            print(f'Successfully reordered ApplicationTop: Ricoh presets placed at positions 1-5!')
        else:
            print(f'Warning: Only found {len(block_map)} Ricoh presets in ApplicationTop, skipping reordering.')

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

