import os
import shutil
import subprocess
from PIL import Image

def generate_icons():
    source_path = "../frontend/img/kitsu_publisher.png"
    
    if not os.path.exists(source_path):
        print(f"Error: Source image not found at {source_path}")
        return

    img = Image.open(source_path)

    # 1. Create Frontend Logo (frontend/src/lib/assets/logo.png)
    logo_dir = "../frontend/src/lib/assets"
    if not os.path.exists(logo_dir):
        os.makedirs(logo_dir)
    
    logo_path = os.path.join(logo_dir, "logo.png")
    # Resize for UI usage (e.g. height 256px, keep aspect ratio)
    img.copy().resize((256, 256), Image.Resampling.LANCZOS).save(logo_path)
    print(f"Generated logo: {logo_path}")

    # 2. Create Favicon (frontend/static/favicon.png)
    favicon_dir = "../frontend/static"
    if not os.path.exists(favicon_dir):
        os.makedirs(favicon_dir)
    
    favicon_path = os.path.join(favicon_dir, "favicon.png")
    img.copy().resize((64, 64), Image.Resampling.LANCZOS).save(favicon_path)
    print(f"Generated favicon: {favicon_path}")

    # 3. Create macOS App Icon (backend/icon.icns) using iconutil
    # Create a temporary .iconset directory
    iconset_dir = "KitsuPublisher.iconset"
    if os.path.exists(iconset_dir):
        shutil.rmtree(iconset_dir)
    os.makedirs(iconset_dir)

    # Standard sizes for macOS icons
    sizes = [16, 32, 128, 256, 512]
    
    try:
        for size in sizes:
            # Normal resolution
            filename = f"icon_{size}x{size}.png"
            img.copy().resize((size, size), Image.Resampling.LANCZOS).save(os.path.join(iconset_dir, filename))
            
            # High resolution (@2x)
            filename_2x = f"icon_{size}x{size}@2x.png"
            img.copy().resize((size * 2, size * 2), Image.Resampling.LANCZOS).save(os.path.join(iconset_dir, filename_2x))

        # Convert .iconset to .icns using macOS 'iconutil'
        subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", "icon.icns"], check=True)
        print("Generated app icon: icon.icns")

    except Exception as e:
        print(f"Failed to generate .icns: {e}")
    finally:
        # Cleanup
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir)

if __name__ == "__main__":
    generate_icons()
