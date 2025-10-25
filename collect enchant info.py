#!/usr/bin/env python3

from PIL import Image, ImageEnhance, ImageFilter
from difflib import SequenceMatcher
import numpy as np
import pytesseract
import subprocess
import pyautogui
import random
import time

# Safety setting: fail-safe by moving mouse to corner
pyautogui.FAILSAFE = True

# Define the coordinates of certain slots
book_x, book_y = 743, 579
ench_slot_x, ench_slot_y = 794, 468
throw_away_x, throw_away_y = 684, 468

# Define the coordinates of enchantment level text
slotheight = 57
level_x1, level_y1 = 1154, 369
level_x2, level_y2 = 1194, 397

# Define the coordinates of resulting enchantment text
ench_x1, ench_y1 = 848, 489
ench_x2, ench_y2 = 1220, 521


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
	
	#print(f"Capturing screenshot to {output_path}...")
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
	#print(f"Cropping to region ({x1},{y1}) - ({x2},{y2})...")
	image = Image.open(output_path)
	
	# PIL crop expects (left, top, right, bottom)
	cropped = image.crop((x1, y1, x2, y2))
	cropped.save(name + "_cropped.png")
	
	return cropped

def extract_text_from_image(name, image, numbers_only):
	"""
	Extract text from an image using OCR.
	
	Args:
		name: name for debug
		image: PIL Image object
	
	Returns:
		Extracted text as string
	"""

	# Convert to grayscale
	image = image.convert('L')
	
	# Increase contrast
	#enhancer = ImageEnhance.Contrast(image)
	#image = enhancer.enhance(2.0)
	
	# Sharpen the image
	#image = image.filter(ImageFilter.SHARPEN)

	image.save(name + "_cropped_grey.png")
	
	# Apply binary threshold (convert to pure black and white)
	image_array = np.array(image)
	threshold = 160 # The text of both the enchantment name and level requirement are brighter than this
	image_array = ((image_array > threshold) * 255).astype(np.uint8)
	# Invert image so text is in black on white background
	image_array = 255 - image_array
	image = Image.fromarray(image_array)

	image.save(name + "_cropped_grey_thresh.png")

	# Configure tesseract
	# OEM: for OCR Engine Mode
	# PSM: 7 for single line text, 13 for raw single text line
	custom_config = f'--oem 0 --psm 7'
	if numbers_only:
		custom_config += ' -c tessedit_char_whitelist=0123456789'
	else:
		custom_config += ' -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
	
	# Extract text
	text = pytesseract.image_to_string(image, lang='eng', config=custom_config)

	return text.strip()

def enchant_book():
	#choose random enchantment level slot
	enchant_level_slot = random.randint(1,3)
	# calculate level slot height
	chosen_level_y1 = level_y1 + slotheight * (enchant_level_slot - 1)
	chosen_level_y2 = level_y2 + slotheight * (enchant_level_slot - 1)

	# Get books into cursor
	pyautogui.click(book_x, book_y, button='middle', _pause=False)
	time.sleep(0.1)
	# Insert book into enchantment table
	pyautogui.click(ench_slot_x, ench_slot_y, button='left', _pause=False)
	time.sleep(0.1)
	# Throw away other books
	pyautogui.click(throw_away_x, throw_away_y, button='left', _pause=False)
	time.sleep(0.1)

	# Capture the screen region
	image = capture_screen_region("images/level", level_x1, chosen_level_y1, level_x2, chosen_level_y2)
	
	# Extract text
	level = extract_text_from_image("images/level", image, True)
	
	print("Extracted text:")
	print("-" * 40)
	print(level)
	print("-" * 40)

	# Choose enchantment slot
	pyautogui.click(level_x1, chosen_level_y1, button='left', _pause=False)
	time.sleep(0.1)

	# Hover over enchanted book
	pyautogui.moveTo(ench_slot_x, ench_slot_y)
	
	# Capture the screen region
	image = capture_screen_region("images/ench", ench_x1, ench_y1, ench_x2, ench_y2)

	# Extract text
	ench = extract_text_from_image("images/ench", image, False)

	print("\nExtracted text:")
	print("-" * 40)
	print(ench)
	print("-" * 40)
	
	# Pick up the book
	pyautogui.click()
	time.sleep(0.1)
	
	# Throw the book out
	pyautogui.click(throw_away_x, throw_away_y)
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