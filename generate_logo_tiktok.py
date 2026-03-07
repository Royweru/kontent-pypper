import os
from PIL import Image

def format_logo(input_path: str, output_path: str) -> None:
    target_size = (1024, 1024)
    max_size_mb = 5.0

    try:
        with Image.open(input_path) as img:
            # Ensure image is in RGB mode if saving as JPEG later, though PNG supports RGBA
            if img.mode != 'RGB' and img.mode != 'RGBA':
                img = img.convert('RGBA')
                
            # Resize using Lanczos for high-quality resampling
            resized_img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # PNG is preferred for logos to maintain sharp edges
            resized_img.save(output_path, format="PNG")
            
        # Verify constraint: File size
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        
        if file_size_mb > max_size_mb:
            print(f"Error: Output file is {file_size_mb:.2f}MB, which exceeds the {max_size_mb}MB limit.")
            # Note: For this specific logo, a 1024x1024 PNG will rarely exceed 1MB.
        else:
            print(f"Success: Image saved at {output_path}. Dimensions: {target_size}, Size: {file_size_mb:.2f}MB.")

    except Exception as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    format_logo("logo.png", "tiktok_developer_logo.png")