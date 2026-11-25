"""A tiny fake of Live's Python API and the parts of _Framework the Alias8 script uses.

Install it with install(), then import Alias8. Only what the script touches is faked; it's enough to
check the script's own logic (banks, buttons, lights), not Live's mapping engine.
"""
import contextlib
import sys
import types

LOG = []          # everything sent to the controller, in order: ("midi", bytes) or ("led", element args, value)


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


class Wrapper(object):
    """Like Live's Python objects: a new wrapper on every read, equal (==) to the same track but not identical."""
    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def __setattr__(self, name, value):
        setattr(self._obj, name, value)

    def __eq__(self, other):
        return self._obj is (other._obj if isinstance(other, Wrapper) else other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return id(self._obj)


class View(object):
    def __init__(self):
        self._selected = None
        self.wrap = True           # hand out a new wrapper on every read, as Live does

    @property
    def selected_track(self):
        if self.wrap and self._selected is not None:
            return Wrapper(self._selected)
        return self._selected

    @selected_track.setter
    def selected_track(self, t):
        self._selected = t._obj if isinstance(t, Wrapper) else t


class Song(object):
    def __init__(self, tracks):
        self.visible_tracks = list(tracks)
        self.view = View()


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
        LOG.append(("led", self.args, value))


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


class FakeAlias8(object):
    """Answers the script's questions like an Alias 8: 'request setting <cmd>' -> the setting; a setting
    message changes it. relative=True: the encoder's CC mode is relative. answers=False: never answers.
    drop={cmd: n}: ignore the first n questions about cmd. delay=True: answers wait for deliver()."""
    HEADER = (240, 0, 1, 97, 11)

    def __init__(self, relative=False, answers=True, drop=None, delay=False, settings=None):
        self.settings = {34: (0, 7, 6, 5, 1, 4, 3, 2), 16: (126, 1, 42, 1, 43, 1, 44, 1),
                         17: (2, 0) if relative else (0, 0), 26: (0,),
                         4: (1, 0, 0, 0, 0, 0, 0, 0),           # button 1 saved red, the rest off
                         37: (1,) + (0,) * 119}                 # all banks (the real Alias 8 may not answer)
        self.leds_from_notes = 0                                # LED messages received (notes)
        self.settings.update(settings or {})
        self.answers, self.drop, self.delay = answers, dict(drop or {}), delay
        self.pending = []
        self.surface = None

    def receive(self, data):
        if data[0] & 0xF0 in (0x90, 0x80):            # (not used: the fake elements don't send MIDI)
            return
        if data[:5] != self.HEADER or len(data) < 7:
            return
        cmd = data[5]
        if cmd == 7:                                   # a question
            asked = data[6]
            if not self.answers or asked not in self.settings:
                return
            if self.drop.get(asked, 0) > 0:
                self.drop[asked] -= 1
                return
            reply = self.HEADER + (asked,) + tuple(self.settings[asked]) + (247,)
            if self.delay:
                self.pending.append(reply)
            else:
                self.surface.handle_sysex(reply)
        elif cmd in self.settings:                     # a setting
            self.settings[cmd] = tuple(data[6:-1])

    def deliver(self):
        replies, self.pending = self.pending, []
        for r in replies:
            self.surface.handle_sysex(r)


class ControlSurface(object):
    _song = None
    device = None

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

    def log_message(self, m):
        self.messages.append(m)

    def _send_midi(self, data):
        self.midi_out.append(tuple(data))
        LOG.append(("midi", tuple(data)))
        if self.device is not None:
            self.device.receive(tuple(data))

    def set_highlighting_session_component(self, s):
        self.highlight = s

    def update_display(self):
        pass

    def handle_sysex(self, data):
        pass

    def disconnect(self):
        pass


def install(song):
    del LOG[:]
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
