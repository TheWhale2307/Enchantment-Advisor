#!/usr/bin/env python3

from difflib import SequenceMatcher
from collections import defaultdict
from pynput import keyboard as kb
from PIL import Image
import numpy as np
import pytesseract
import subprocess
import pyautogui
import hashlib
import pprint
import random
import json
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

possible_enchs = []
with open("enchs_relevant_added.txt", "r") as file:
	for line in file:
		possible_enchs.append(line.strip())

# Add keyboard listener to interrupt the program even when Minecraft has focus and not the terminal
w_pressed = False

def on_press(key):
	global w_pressed
	try:
		if key.char == 'w':
			w_pressed = True
	except AttributeError:
		pass

listener = kb.Listener(on_press=on_press)
listener.start()

def nested_defaultdict_from_dict(d, depth):
	"""Recursively convert a dict to nested defaultdicts with proper depth"""
	# Create all the factories upfront
	factories = [int]  # Base factory
	for i in range(1, depth):
		prev_factory = factories[-1]
		factories.append(lambda pf=prev_factory: defaultdict(pf))
	
	def convert(data, current_depth):
		if current_depth == 0:
			return data
		
		result = defaultdict(factories[current_depth - 1])
		
		for key, value in data.items():
			if isinstance(value, dict):
				result[key] = convert(value, current_depth - 1)
			else:
				result[key] = value
		
		return result
	
	return convert(d, depth)

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
	
	# Passed arguments mean: Fullscreen, Background, Nonotify, Output
	result = subprocess.run(
		['spectacle', '-f', '-b', '-n', '-o', output_path],
		capture_output=True,
		text=True
	)
	
	if result.returncode != 0:
		raise RuntimeError(f"Spectacle failed: {result.stderr}")
	
	# Open image and crop to specified region
	image = Image.open(output_path)
	image = image.crop((x1, y1, x2, y2))
	image.save(name + "_cropped.png")

	# Convert to grayscale
	image = image.convert('L')
	image.save(name + "_cropped_grey.png")
	
	# Apply binary threshold (convert to pure black and white)
	image_array = np.array(image)
	# The text of both the enchantment name and level requirement are brighter than this
	threshold = 160
	image_array = ((image_array > threshold) * 255).astype(np.uint8)
	# Invert image so text is in black on white background
	image_array = 255 - image_array
	image = Image.fromarray(image_array)
	image.save(name + "_cropped_grey_thresh.png")
	
	return image

def extract_text_from_image(image, numbers_only):
	"""
	Extract text from an image using OCR.
	
	Args:
		image: PIL Image object
		numbers_only: Boolean whether or not the settings for numbers should be used
	
	Returns:
		Extracted text as string
	"""

	# Configure tesseract
	# OEM: for OCR Engine Mode, 0 means legacy, works best here
	# PSM: 7 for single line text, 13 would be for raw single text line
	custom_config = f'--oem 0 --psm 7'
	if numbers_only:
		custom_config += ' -c tessedit_char_whitelist=0123456789'
	else:
		custom_config += ' -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
	
	# Extract text
	text = pytesseract.image_to_string(image, lang='eng', config=custom_config).strip()

	return text

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

def enchant_book(hashes):
	#choose random enchantment level slot
	enchant_level_slot = random.randint(1,3)
	# calculate level slot height
	chosen_level_y1 = level_y1 + slotheight * (enchant_level_slot - 1)
	chosen_level_y2 = level_y2 + slotheight * (enchant_level_slot - 1)

	# Get books into cursor
	pyautogui.click(book_x, book_y, button='middle', _pause=False)
	#time.sleep(0.1)
	# Insert book into enchantment table
	pyautogui.click(ench_slot_x, ench_slot_y, button='left', _pause=False)
	#time.sleep(0.1)
	# Throw away other books
	pyautogui.click(throw_away_x, throw_away_y, button='left', _pause=False)
	#time.sleep(0.1)

	# Capture the screen region
	image = capture_screen_region("images/level", level_x1, chosen_level_y1, level_x2, chosen_level_y2)

	# Hash the image
	hash = hashlib.sha256(image.tobytes()).hexdigest()
	
	if hash in hashes:
		level = hashes[hash]
	else:
		# Extract text
		likely_level = extract_text_from_image(image, True)
		# Show image to user for verification
		image.show()
		user_input = input("What number is being shown in the image? Hit Return to accept " + likely_level + ". ")
		level = likely_level if user_input == "" else user_input
		# Save for later
		hashes[hash] = level

	# Choose enchantment slot
	pyautogui.click(level_x1, chosen_level_y1, button='left', _pause=False)

	# Hover over enchanted book
	pyautogui.moveTo(ench_slot_x, ench_slot_y)
	
	# Capture the screen region
	image = capture_screen_region("images/ench", ench_x1, ench_y1, ench_x2, ench_y2)

	# Hash the image
	hash = hashlib.sha256(image.tobytes()).hexdigest()
	
	if hash in hashes:
		ench = hashes[hash]
	else:
		# Extract text
		likely_ench = extract_text_from_image(image, False)
		match, ratio = find_best_match(likely_ench, possible_enchs)
		# Show image to user for verification
		image.show()
		user_input = input("What enchantment is being shown in the image? Hit Return to accept " + match + ". ")
		ench = match if user_input == "" else user_input
		# Save for later
		hashes[hash] = ench
	
	# Pick up the book
	pyautogui.click(ench_slot_x, ench_slot_y)
	
	# Throw the book out
	pyautogui.click(throw_away_x, throw_away_y)

	return level, ench

def sort_key(item):
	key = item[0]
	
	# If it's a string that represents a number, treat it as a number
	if isinstance(key, str) and key.isdigit():
		return (0, int(key))
	# Otherwise treat it as a string
	else:
		return (1, key)
	
def sort_val(item):
	key = item[1]
	
	# If it's a string that represents a number, treat it as a number
	if isinstance(key, str) and key.isdigit():
		return (0, int(key))
	# Otherwise treat it as a string
	else:
		return (1, key)
	
def sort_nested_dict(d):
	"""Recursively sort a dict/defaultdict with proper numeric ordering for string keys"""
	result = {}
	
	for key, value in sorted(d.items(), key=sort_key):
		if isinstance(value, dict):
			result[key] = sort_nested_dict(value)
		else:
			result[key] = value
	return result

def main():
	global w_pressed

	try:
		with open("hashes.json") as file:
			hashes=json.load(file)
	except:
		print("Hashes file does not exist or is corrupted, creating a new one...")
		hashes = {}

	# Slightly cursed datatype (I refuse to use databases, they are for nerds)
	try:
		with open("data.json") as file:
			data = nested_defaultdict_from_dict(json.load(file), 3)
	except:
		print("Data file does not exist or is corrupted, creating a new one...")
		data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

	print("Starting in 3 seconds... Move mouse to corner to abort")
	time.sleep(3)

	while True:
		try:
			if w_pressed:
				w_pressed = False
				raise KeyboardInterrupt
			level, ench = enchant_book(hashes)
			print("Got " + ench + " for " + level + " levels.")
			data["123"][level][ench] += 1
		except KeyboardInterrupt:
			print("\nCtrl+C caught! Do you want to quit? (y/n)")
			choice = input()
			if choice.lower() == 'y':
				print("Number of hashes in the lookup table: " + str(len(hashes.keys())))
				with open ('hashes.json', 'w') as outfile:
					# Sort by value alphabetically to make checking for missing (not yet encountered) values easier
					hashes = {k: v for k, v in sorted(hashes.items(), key=sort_val)}
					json.dump(hashes, outfile, indent=4)
				
				with open ('data.json', 'w') as outfile:
					data = sort_nested_dict(data)
					json.dump(data, outfile, indent=4)
				print("Exiting...")
				break
			else:
				print("Continuing...")

if __name__ == "__main__":
	main()