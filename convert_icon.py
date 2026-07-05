import os
from PIL import Image

png_path = r"C:\Users\sheik\.gemini\antigravity\brain\cb98d040-2049-4104-a8f1-f94dfd51afef\glide_cast_logo_1783224415930.png"
ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glidecast.ico")

if os.path.exists(png_path):
    print(f"Opening logo image from: {png_path}")
    img = Image.open(png_path)
    
    # Save as multi-resolution ICO file
    print(f"Saving icon to: {ico_path}")
    img.save(
        ico_path, 
        format="ICO", 
        sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]
    )
    print("Icon conversion successful!")
else:
    print(f"Error: Generated image not found at {png_path}")
