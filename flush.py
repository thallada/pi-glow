#!/usr/bin/python

# Light painting / POV demo for Raspberry Pi using
# Adafruit Digital Addressable RGB LED flex strip.
# ----> http://adafruit.com/products/306

import RPi.GPIO as GPIO, Image, time

# Configurable values
dev       = "/dev/spidev0.0"

# Flush the LED strip
spidev    = file(dev, "wb")
spidev.flush()
