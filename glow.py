#!/usr/bin/python

# Testing the LED lights

import random
import time
import argparse
import struct

# Set up command-line operations
parser = argparse.ArgumentParser(description="Make the LPD8806 LEDs glow random colors")
parser.add_argument('-s', '--step', type=int, default=1,
		help='Amount in RGB to increase/decrease at every interval. Lower value '
		'will be slower and smoother, higher will be faster but jumpier.')
parser.add_argument('-i', '--interval', type=float, default=0.1,
		help='Time in seconds to wait between every interval (step). Lower value '
		'will be slower and more jagged and jumpy, higher will be faster and smoother.')
parser.add_argument('-g', '--glow_pause', type=float, default=2,
		help='Time in seconds to wait at maximum glow')
parser.add_argument('-d', '--dim_pause', type=float, default=1,
		help='Time in seconds to wait while LEDs are off')
parser.add_argument('-m', '--minimum', type=int, default=0,
		help='The minimum value to fade out to, the "dim" setting. (0 - 255)')
parser.add_argument('-n', '--no_dim', action='store_true', default=False,
		help='Instead of fading out to a dim minimum, only pause at max glow'
		'and then fade to the next random color.')
parser.add_argument('-L', '--min_color', type=int, default=0,
		help='Minimum of the range to select color values from. A higher value will'
		'make brighter colors. (valid range: 0-255)')
parser.add_argument('-H', '--max_color', type=int, default=255,
		help='Maximum of the range to select color values from. A lower value will'
		'make dimmer colors. (valid range: 0-255)')
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

step = parser.parse_args().step
interval = parser.parse_args().interval
glow_pause = parser.parse_args().glow_pause
dim_pause = parser.parse_args().dim_pause
minimum = parser.parse_args().minimum
min_color = parser.parse_args().min_color
max_color = parser.parse_args().max_color
no_dim = parser.parse_args().no_dim
verbose = parser.parse_args().verbose
fake = parser.parse_args().fake
# Create a bytearray to display
# R, G, B byte per pixel, plus extra '0' byte at end for latch.
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

# Now, glow
while True:
	color = tuple([random.randint(min_color, max_color) for x in range(3)])
	# Wrap in try/except block for graceful exiting via KeyboardInterrupt
	try:
		fade_to_color(color, array, gamma, step=step,
				interval=interval, pause=glow_pause)
		time.sleep(glow_pause)
		if not no_dim:
			fade_to_color((minimum, minimum, minimum), array, gamma, step=step,
					interval=interval, pause=dim_pause)
			time.sleep(dim_pause)
	except KeyboardInterrupt:
		# Clear out array
		for y in range(height):
			value = [0]*3
			y3 = y * 3
			array[y3]     = gamma[value[1]]
			array[y3 + 1] = gamma[value[0]]
			array[y3 + 2] = gamma[value[2]]
                if not fake:
                    spidev.write(array)
                    spidev.flush()
		exit(0)
