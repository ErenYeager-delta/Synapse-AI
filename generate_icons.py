import os
from PIL import Image

# Path to master logo
master_path = r"C:\Users\VIGNESH\.gemini\antigravity\brain\aa63d051-ad1b-44dd-8d25-38b18b80563f\synapse_master_logo_1772552211959.png"
static_dir = r"c:\Users\VIGNESH\Downloads\Synapse\chat\static\chat\images"

if not os.path.exists(static_dir):
    os.makedirs(static_dir)

img = Image.open(master_path)

# 1. favicon.ico (Multiple sizes)
img.save(os.path.join(static_dir, 'favicon.ico'), sizes=[(16, 16), (32, 32), (48, 48)])

# 2. favicon-32x32.png
img.resize((32, 32)).save(os.path.join(static_dir, 'favicon-32x32.png'))

# 3. apple-touch-icon.png (180x180)
img.resize((180, 180)).save(os.path.join(static_dir, 'apple-touch-icon.png'))

# 4. android-chrome-192x192.png
img.resize((192, 192)).save(os.path.join(static_dir, 'android-chrome-192x192.png'))

# 5. android-chrome-512x512.png
img.resize((512, 512)).save(os.path.join(static_dir, 'android-chrome-512x512.png'))

print("All icons generated successfully.")
