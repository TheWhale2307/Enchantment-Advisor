#!/usr/bin/env python3

from PIL import Image, ImageEnhance, ImageFilter
from difflib import SequenceMatcher
import numpy as np
import pytesseract
import subprocess
import pyautogui
import time

# Safety setting: fail-safe by moving mouse to corner
pyautogui.FAILSAFE = True

def capture_screen_region(name, x1, y1, x2, y2):
	"""
	Capture a specific region of the screen using spectacle on KDE.
	
	Args:
		name: name for debug
		x1, y1: Top-left corner coordinates
		x2, y2: Bottom-right corner coordinates
	
	Returns:
		PIL Image object
	"""

	# Save to current directory for debugging
	output_path = name + ".png"
	
	print(f"Capturing screenshot to {output_path}...")
	# Passed arguments mean: Fullscreen, Background, Nonotify, Output
	result = subprocess.run(
		['spectacle', '-f', '-b', '-n', '-o', output_path],
		capture_output=True,
		text=True
	)
	
	if result.returncode != 0:
		raise RuntimeError(f"Spectacle failed: {result.stderr}")
	
	# Wait a moment to ensure file is written
	time.sleep(0.2)
	
	# Open image and crop to specified region
	print(f"Cropping to region ({x1},{y1}) - ({x2},{y2})...")
	image = Image.open(output_path)
	
	# PIL crop expects (left, top, right, bottom)
	cropped = image.crop((x1, y1, x2, y2))
	cropped.save(name + "_cropped.png")
	
	return cropped

def extract_text_from_image(name, image):
	"""
	Extract text from an image using OCR.
	
	Args:
		name: name for debug
		image: PIL Image object
	
	Returns:
		Extracted text as string
	"""

	# Convert to grayscale
	if image.mode != 'L':
		image = image.convert('L')
	
	# Increase contrast
	#enhancer = ImageEnhance.Contrast(image)
	#image = enhancer.enhance(2.0)
	
	# Sharpen the image
	#image = image.filter(ImageFilter.SHARPEN)

	image.save(name + "_cropped_grey.png")
	
	# Apply binary threshold (convert to pure black and white)
	image_array = np.array(image)
	threshold = 160
	image_array = ((image_array > threshold) * 255).astype(np.uint8)
	image = Image.fromarray(image_array)

	image.save(name + "_cropped_grey_thresh.png")

	# Configure tesseract
	custom_config = f'--oem 3 --psm 7'
	# OEM 3 = Default OCR Engine Mode (uses both legacy and LSTM)
	
	# Extract text
	text = pytesseract.image_to_string(image, lang='eng', config=custom_config)

	return text.strip()

def enchant_book():
	# Define the coordinates of enchantment level text
	x1, y1 = 1154, 484
	x2, y2 = 1195, 513

	# Define the coordinates of resulting enchantment text
	x3, y3 = 851, 487
	x4, y4 = 1230, 522
	
	# Insert book
	pyautogui.click(745, 580, button='middle', _pause=False)
	time.sleep(0.1)
	pyautogui.click(800, 470, button='left', _pause=False)
	time.sleep(0.1)
	pyautogui.click(600, 470, button='left', _pause=False)
	time.sleep(0.1)

	print(f"Capturing level region: ({x1}, {y1}) to ({x2}, {y2})")

	# Capture the screen region
	image = capture_screen_region("images/level", x1, y1, x2, y2)
	
	# Extract text
	level = extract_text_from_image("images/level", image)
	
	print("\nExtracted text:")
	print("-" * 40)
	print(level)
	print("-" * 40)

	# Choose lowest enchantment slot
	print("Clicking at (900, 500)")
	pyautogui.click(900, 500, button='left', _pause=False)
	time.sleep(0.1)

	# Hover over enchanted book
	pyautogui.moveTo(800, 470)

	print(f"Capturing enchantment region: ({x3}, {y3}) to ({x4}, {y4})")
	
	# Capture the screen region
	image = capture_screen_region("images/ench", x3, y3, x4, y4)
	
	# Extract text
	ench = extract_text_from_image("images/ench", image)
	
	print("\nExtracted text:")
	print("-" * 40)
	print(ench)
	print("-" * 40)
	
	# Pick up the book
	print("Clicking at (800, 470)")
	pyautogui.click()
	time.sleep(0.1)
	
	# Throw the book out
	print("Clicking at (600, 470)")
	pyautogui.click(600, 470)
	time.sleep(0.1)

	return level, ench

def find_best_match(unknown_string, possible_strings, cutoff=0.6):
    """
    Find the best matching string from a list of possible strings.
    
    Args:
        unknown_string (str): The string to match
        possible_strings (list): List of strings to match against
        cutoff (float): Minimum similarity ratio (0-1) to consider a match.
                       Default is 0.6. Returns None if no match exceeds cutoff.
    
    Returns:
        tuple: (best_match, similarity_score) or (None, 0) if no good match found
    """
    if not unknown_string or not possible_strings:
        return None, 0
    
    # Normalize the unknown string for comparison
    unknown_normalized = unknown_string.lower().strip()
    
    best_match = None
    best_ratio = 0
    
    for candidate in possible_strings:
        # Normalize candidate string
        candidate_normalized = candidate.lower().strip()
        
        # Calculate similarity ratio
        ratio = SequenceMatcher(None, unknown_normalized, candidate_normalized).ratio()
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate
    
    # Return None if best match doesn't meet cutoff threshold
    if best_ratio < cutoff:
        return None, best_ratio
    
    return best_match, best_ratio

def main():
	print("Starting in 3 seconds... Move mouse to corner to abort")
	time.sleep(3)

	level, ench = enchant_book()

	print("Done!")

if __name__ == "__main__":
	main()