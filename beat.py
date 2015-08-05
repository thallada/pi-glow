#!/usr/bin/python
"""
Shine a random color at a given beats per minute.
"""

import random
import time
import argparse
import struct

# Set up command-line operations
parser = argparse.ArgumentParser(description="Make the LPD8806 LEDs display a "
                                 "random color at a given beats per minute.")
parser.add_argument('-b', '--bpm', type=int, default=140,
		help='The beats per minute to display a color and then dim.'
		'will be slower and smoother, higher will be faster but jumpier.')
parser.add_argument('-v', '--verbose', action='store_true', default=False,
		help='Display debug printouts of the current and target colors at every '
		'sub-interval')
parser.add_argument('-f', '--fake', action='store_true', default=False,
		help='Run the program but don\'t actually display lights on '
                'the LED strip.')

# Set the spi file
dev       = "/dev/spidev0.0"

# Open SPI device
spidev    = file(dev, "wb")

# Number of LEDs in my strip
height = 32

# Calculate gamma correction table.  This includes
# LPD8806-specific conversion (7-bit color w/high bit set).
gamma = bytearray(256)
for i in range(256):
	gamma[i] = 0x80 | int(pow(float(i) / 255.0, 2.5) * 127.0 + 0.5)

# Create a bytearray to display
# R, G, B byte per pixel, plus extra '0' byte at end for latch.
bpm = parser.parse_args().bpm
verbose = parser.parse_args().verbose
fake = parser.parse_args().fake
if verbose: print "Allocating..."
array = bytearray(height * 3 + 1)

def test_gamma(strip, gamma):
	# First a test:	
	for i, color in enumerate(gamma):
		print str(i) + ": " + str(color) + " (" + repr(struct.pack('>B', color)) + ")"
		for y in range(height):
			value = [0]*3
			y3 = y * 3
			strip[y3]     = color
			strip[y3 + 1] = color
			strip[y3 + 2] = color
                if not fake:
                    spidev.write(strip)
                    spidev.flush()
		time.sleep(0.5)

def rgb_to_gamma(color, gamma):
	"""Translate normal RGB colors to the first occurrence in the gamma array
	
	The LPD8806 skips over a lot of RGB colors by using the same color at many
	different indices. This method just takes a gamma index: color, finds what
	color byte the gamma array contains at that index, and then searches the
	array from the beginning to find the first occurrence of that color byte
	and returns that gamma index instead. That way, all representable colors can 
	be reduced to the indexes in gamma that start new colors, thereby making 
	equivalencies between colors that are actually equal a lot easier.

	Arguments:
	color -- triple tuple representing RGB respectively for the desired color
	gamma -- bytearray of 256 corrected colors to choose from for the LPD8806 LEDs
	
	"""
	gamma_r = gamma.index(struct.pack('>B', gamma[color[0]]))
	gamma_g = gamma.index(struct.pack('>B', gamma[color[1]]))
	gamma_b = gamma.index(struct.pack('>B', gamma[color[2]]))
	return gamma_r, gamma_g, gamma_b
	

def get_current_color(strip, gamma):
	"""Extract gamma-indexed RBG tuple from the first LED in the strip.

	The strip is ordered in GRB format, but this method returns RGB. Also note
	that this method only checks the color of the first LED, and does not take
	into account the rest of the strip's colors.
	
	Arguments:
	strip -- bytearray of the latest written colors to the LED strip. Array is
		 three times the length of the strip plus one for '0' byte latch.
	gamma -- bytearray of 256 corrected colors to choose from for the LPD8806 LEDs

	"""	
	gamma_r = gamma.index(struct.pack('>B', strip[1]))
	gamma_g = gamma.index(struct.pack('>B', strip[0]))
	gamma_b = gamma.index(struct.pack('>B', strip[2]))
	return gamma_r, gamma_g, gamma_b

def fade_to_color(color, strip, gamma, step=1, interval=0.1, pause=1):
	"""Increment/Decrement LED colors to the target color and pause.
	
	Will convert the RGB color to the gamma-indexed version internally.

	Arguments:
	color -- triple tuple representing RGB respectively for the desired color
	strip -- bytearray of the latest written colors to the LED strip. Array is
		 three times the length of the strip plus one for '0' byte latch.
	gamma -- bytearray of 256 corrected colors to choose from for the LPD8806 LEDs
	
	Keyword Arguments:
	step -- amount in RGB to increment/decrement at each interval (default 1)
	interval -- time in seconds between each increment/decrement (default 0.1)
	pause -- time in seconds to wait once fade is complete (default 1)

	"""
	if verbose: print "color desired: " + str(color)
	# Convert color to a gamma-indexed value that this method will certainly reach
	color = rgb_to_gamma(color, gamma)
	if verbose: print "gamma-indexed color: " + str(color)
	strip_length = (len(strip) - 1) / 3
	current = get_current_color(strip, gamma)
	counter = 0
	while (current != color):
		# Near the end of the gamma spectrum, some colors are missing, so skip over
		# them if they are encountered.
		skip_nums = [234, 235, 242, 243, 248, 249, 252, 253]
		skip_g = 1
		skip_r = 1
		skip_b = 1
		if current[1] in skip_nums: skip_g = 2
		if current[0] in skip_nums: skip_r = 2
		if current[2] in skip_nums: skip_b = 2
		# Fill strip with next color
		for y in range(strip_length):
			y3 = y * 3
			strip[y3] = gamma[current[1]] + \
					(cmp(color[1], current[1]) * skip_g)
			strip[y3 + 1] = gamma[current[0]] + \
					(cmp(color[0], current[0]) * skip_r)
			strip[y3 + 2] = gamma[current[2]] + \
					(cmp(color[2], current[2]) * skip_b)
		# Increment counter. If at next step, then write to spi and wait
		counter = counter + 1
		if counter % step == 0: 
                        if not fake:
                            spidev.write(strip)
                            spidev.flush()
			time.sleep(interval)
		# Update the current color for the while condition comparison
		current = get_current_color(strip, gamma)
		if verbose: print str(current) + " | " + str(color)

def display_color(color, strip, gamma):
    """Subset of fade_to_color that just displays one color."""
    if verbose: print "color desired: " + str(color)
    color = rgb_to_gamma(color, gamma)
    if verbose: print "gamma-indexed color: " + str(color)
    strip_length = (len(strip) - 1) / 3
    # Fill strip with next color
    for y in range(strip_length):
        y3 = y * 3
        strip[y3] = color[1]
        strip[y3 + 1] = color[0]
        strip[y3 + 2] = color[2]
    if not fake:
        spidev.write(strip)
        spidev.flush()

def clear(array, gamma):
    # clear out array
    for y in range(height):
        value = [0]*3
        y3 = y * 3
        array[y3]     = gamma[value[1]]
        array[y3 + 1] = gamma[value[0]]
        array[y3 + 2] = gamma[value[2]]
    if not fake:
        spidev.write(array)
        spidev.flush()


# Now write to the spi port!
if verbose: print "Displaying..."

# Firstly, clear the strip and set array to values that are known
for y in range(height):
	value = [0]*3
	y3 = y * 3
	array[y3]     = gamma[value[1]]
	array[y3 + 1] = gamma[value[0]]
	array[y3 + 2] = gamma[value[2]]
if not fake:
    spidev.write(array)
    spidev.flush()

wait_time = (1.0 / (bpm / 60.0))
print "wait_time: " + str(wait_time)
# Now, glow
raw_input("Press Enter to start the beat...")
while True:
    color = (0, 0, 0)
    while color[0] < 100 and color[1] < 100 and color[2] < 100:
        color = tuple([random.randint(65, len(gamma)-1) for x in range(3)])
    # Wrap in try/except block for graceful exiting via KeyboardInterrupt
    try:
        display_color(color, array, gamma)
        time.sleep(wait_time/2.0)
        clear(array, gamma)
        time.sleep(wait_time/2.0)
    except KeyboardInterrupt:
        clear(array, gamma)
        exit(0)
