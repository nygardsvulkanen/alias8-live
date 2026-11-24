# Alias8 - Ableton Live control surface script for the Livid Alias 8.
# Copy this folder to ~/Music/Ableton/User Library/Remote Scripts/ and pick "Alias8" under
# Settings > Link, Tempo & MIDI > Control Surface.
from __future__ import absolute_import, print_function, unicode_literals

from .Alias8 import Alias8


def create_instance(c_instance):
    return Alias8(c_instance)
