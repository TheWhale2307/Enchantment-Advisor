#!/usr/bin/env python3

# Given a file with Echantments and their maximum level write a new one with all respective lower levels included
# --- Example ---
#
# Input:
# Feather Falling IV
# Fire Aspect II
#
# Output:
# Feather Falling I
# Feather Falling II
# Feather Falling III
# Feather Falling IV
# Fire Aspect I
# Fire Aspect II

def main():
	arab_to_rom = ["I", "II", "III", "IV", "V"]
	rom_to_arab = {
		"I": 1,
		"II": 2,
		"III": 3,
		"IV": 4,
		"V": 5
	}

	with open("enchs_relevant_added.txt", "w") as outfile:
		with open("enchs_relevant.txt") as infile:
			for line in infile:
				segments = line.rstrip().split(" ")
				ench_max_level = rom_to_arab[segments[-1]]
				ench_name = " ".join(segments[:-1])

				for level in range(ench_max_level):
					outfile.write(ench_name + " " + arab_to_rom[level] + "\n")

if __name__ == "__main__":
	main()
