"""A tiny fake of Live's Python API and the parts of _Framework the Alias8 script uses.

Install it with install(), then import Alias8. Only what the script touches is faked; it's enough to
check the script's own logic (banks, buttons, lights), not Live's mapping engine.
"""
import contextlib
import sys
import types


class Track(object):
    def __init__(self, name, color=0xFF0000, can_be_armed=True, devices=()):
        self.name, self.color, self.can_be_armed = name, color, can_be_armed
        self.mute = self.solo = self.arm = False
        self.devices = list(devices)


class Param(object):
    def __init__(self, name, value=0.0, lo=0.0, hi=127.0, enabled=True):
        self.name, self.value, self.min, self.max, self.is_enabled = name, value, lo, hi, enabled

    def str_for_value(self, v):
        return "%d" % round(v)


class Device(object):
    """A plain device (can_have_chains False) or a rack with 16 macros."""
    def __init__(self, name, rack=False, type=1, macros_mapped=None, values=None):
        self.name, self.can_have_chains, self.type = name, rack, type
        values = values or [0.0] * 16
        self.parameters = [Param("Device On", 1, 0, 1)] + [Param("Macro %d" % (n + 1), values[n]) for n in range(16)]
        if macros_mapped is not None:
            self.macros_mapped = macros_mapped


class Song(object):
    def __init__(self, tracks):
        self.visible_tracks = list(tracks)
        self.view = types.SimpleNamespace(selected_track=None)


class Element(object):
    def __init__(self, *args):
        self.args = args
        self.listeners = []
        self.sent = []

    def add_value_listener(self, cb, identify_sender=False):
        self.listeners.append(cb)

    def receive(self, value):
        for cb in list(self.listeners):
            cb(value)

    def send_value(self, value, force=False):
        self.sent.append(value)


class ChannelStrip(object):
    def __init__(self):
        self.volume = None
        self.sends = None
        self.pan = None

    def set_volume_control(self, c):
        self.volume = c

    def set_send_controls(self, cs):
        self.sends = cs

    def set_pan_control(self, c):
        self.pan = c


class MixerComponent(object):
    def __init__(self, num_tracks, *a):
        self._strips = [ChannelStrip() for _ in range(num_tracks)]
        self._master = ChannelStrip()

    def channel_strip(self, i):
        return self._strips[i]

    def master_strip(self):
        return self._master


class SessionComponent(object):
    def __init__(self, num_tracks, num_scenes):
        self._offset = 0
        self.mixer = None

    def set_mixer(self, m):
        self.mixer = m

    def track_offset(self):
        return self._offset

    def scene_offset(self):
        return 0

    def set_offsets(self, t, s):
        self._offset = t


class ControlSurface(object):
    _song = None

    def __init__(self, c_instance):
        self.messages = []
        self.midi_out = []
        self.scheduled = []
        self.highlight = None

    @contextlib.contextmanager
    def component_guard(self):
        yield

    def song(self):
        return ControlSurface._song

    def schedule_message(self, ticks, cb):
        self.scheduled.append(cb)

    def run_scheduled(self):
        jobs, self.scheduled = self.scheduled, []
        for cb in jobs:
            cb()

    def show_message(self, m):
        self.messages.append(m)

    def _send_midi(self, data):
        self.midi_out.append(tuple(data))

    def set_highlighting_session_component(self, s):
        self.highlight = s

    def update_display(self):
        pass

    def handle_sysex(self, data):
        pass

    def disconnect(self):
        pass


def install(song):
    ControlSurface._song = song
    mods = {
        "Live": types.ModuleType("Live"),
        "_Framework": types.ModuleType("_Framework"),
        "_Framework.ControlSurface": types.ModuleType("_Framework.ControlSurface"),
        "_Framework.InputControlElement": types.ModuleType("_Framework.InputControlElement"),
        "_Framework.SliderElement": types.ModuleType("_Framework.SliderElement"),
        "_Framework.ButtonElement": types.ModuleType("_Framework.ButtonElement"),
        "_Framework.SessionComponent": types.ModuleType("_Framework.SessionComponent"),
        "_Framework.MixerComponent": types.ModuleType("_Framework.MixerComponent"),
    }
    mods["_Framework.ControlSurface"].ControlSurface = ControlSurface
    mods["_Framework.InputControlElement"].MIDI_CC_TYPE = 1
    mods["_Framework.InputControlElement"].MIDI_NOTE_TYPE = 0
    mods["_Framework.SliderElement"].SliderElement = Element
    mods["_Framework.ButtonElement"].ButtonElement = Element
    mods["_Framework.SessionComponent"].SessionComponent = SessionComponent
    mods["_Framework.MixerComponent"].MixerComponent = MixerComponent
    sys.modules.update(mods)
