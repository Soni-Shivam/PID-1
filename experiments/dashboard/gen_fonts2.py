import sys
import os
import subprocess

FILES = [
    "utils.py",
    "library.py",
    "app_launcher.py",
    "main.py",
    "widgets/explore_grid.py"
]

def swap_font(old_font, new_font):
    for path in FILES:
        with open(path, "r") as f:
            content = f.read()
        
        # In utils.py we have MODERN_FONT_STACK = "'Century Gothic', 'Tw Cen MT'..."
        if path == "utils.py":
            if old_font == "Century Gothic":
                content = content.replace(f"'{old_font}'", f"'{new_font}'")
            else:
                content = content.replace(f"'{old_font}'", f"'{new_font}'")
                
        content = content.replace(f'"{old_font}"', f'"{new_font}"')
        
        with open(path, "w") as f:
            f.write(content)

def main():
    font_name = sys.argv[1]
    out_file = sys.argv[2]
    
    # Swap out Century Gothic for the new font
    swap_font("Century Gothic", font_name)
    
    # Run the snapshot script
    try:
        subprocess.run(["python3", "snapshot2.py", out_file], check=True)
    finally:
        # Revert back
        swap_font(font_name, "Century Gothic")

if __name__ == "__main__":
    main()
