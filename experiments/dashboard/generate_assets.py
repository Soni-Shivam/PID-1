import os
import sys

# Add parent directory to path to use handler
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    from handler import generate_images
except ImportError as e:
    print(f"Failed to import generate_images from handler.py: {e}")
    sys.exit(1)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

PROMPTS = {
    "hero_1_education": "A cinematic shot of a modern Indian living room. A teenager is sitting on a comfortable sofa or at a coffee table with a wireless keyboard, looking intently at a large smart TV. The TV screen shows a complex 3D biology model or a coding interface. Warm, cozy ambient lighting in the room.",
    "hero_2_gaming": "A close-up of a person's hands holding a sleek wireless game controller. The background is a large screen showing a high-fidelity, graphic-intensive racing or action game. The lighting in the room is dark, illuminated primarily by the vibrant neon blues and magentas reflecting off the TV screen.",
    "hero_3_productivity": "A sleek, minimalist desk setup or a tidy living room table. A steaming cup of coffee sits next to a sleek wireless keyboard and mouse. The screen displays a split-view: a spreadsheet or stock market dashboard (like Zerodha/Groww) on one side, and a modern presentation editor on the other.",
    "hero_4_ai": "An abstract, 3D 'glassmorphic' render. A glowing, soft-edged orb (representing the AI assistant) floating against a dark, mesh-gradient background. It feels smart, capable, and embedded into the OS. Futuristic, elegant, cutting-edge UI design.",
    "hero_5_media": "A view from behind a couple or family sitting on a couch, looking at the TV. The screen displays a rich, Netflix-style grid of high-quality movie posters and live sports streams (like an IPL cricket match). Relaxed, cinematic, family-oriented vibe.",
    "weather_bg": "A beautiful, serene, dynamic weather background artwork suitable for a desktop UI widget. Gentle clouds, soft sunlight, a beautiful minimalist landscape with depth. High quality, digital art, UI aesthetic."
}

def main():
    print(f"Generating images into {ASSETS_DIR}...")
    for key, prompt in PROMPTS.items():
        expected_path = os.path.join(ASSETS_DIR, f"{key}.png")
        if os.path.exists(expected_path):
            print(f"Skipping {key}, already exists.")
            continue
            
        print(f"\nGenerating {key}...")
        # handler.py generate_images returns a filename saved in the target folder
        filename = generate_images(prompt, save_folder=ASSETS_DIR)
        
        if filename:
            generated_path = os.path.join(ASSETS_DIR, filename)
            # rename it to our fixed key name
            try:
                os.rename(generated_path, expected_path)
                print(f"-> Successfully saved to {expected_path}")
            except Exception as e:
                print(f"-> Error renaming {filename} to {key}.png: {e}")
        else:
            print(f"-> Failed to generate {key}")

if __name__ == "__main__":
    main()
