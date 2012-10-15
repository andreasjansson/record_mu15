import sys
import alsaaudio
import struct
import signal
import wave
import pypm
import time
import os
import os.path

sr = 44100
channels = 2

inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE)
inp.setchannels(channels)
inp.setrate(sr)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

mid = float(2 ** 15)

pypm.Initialize()
midi = pypm.Output(2)

def sgn(x):
    return -1 if x < 0 else 1 if x > 0 else 0

class State:
    BEFORE = 0
    DURING = 1
    AFTER = 2
    DONE = 3

def all_notes_off():
    for c in range(16):
        midi.WriteShort(0xB0 + c, 0x7B, 0)

def record_note(filename, channel, pitch, velocity, length = 3):

    midi.WriteShort(0x90 + channel, pitch, velocity)

    outwav = wave.open(filename, 'wb')
    outwav.setnchannels(2)
    outwav.setsampwidth(2)
    outwav.setframerate(44100)

    state = State.BEFORE
    frames_read = 0
    silent_threshold = 10

    prev_left = None
    prev_right = None

    timeout = sr * length * 2
    absolute_frames_read = 0

    while state != State.DONE and absolute_frames_read < timeout:
        #rms_left = 0
        #rms_right = 0
        l, data = inp.read()

        absolute_frames_read += l

        for i in range(0, l * 4, 4):

            left = struct.unpack('<h', data[i : i + 2])[0]
            right = struct.unpack('<h', data[i + 2 : i + 4])[0]
            #rms_left += pow(left / mid, 2)
            #rms_right += pow(right / mid, 2)

            if state == State.BEFORE:
                if abs(left) > silent_threshold or abs(right) > silent_threshold:
                    state = State.DURING

            elif state == State.DURING:
                frames_read += 1
                outwav.writeframesraw(struct.pack('<h', left) + struct.pack('<h', right))  

                if frames_read >= sr * length:
                    state = State.AFTER
                    prev_left = left
                    prev_right = right

            elif state == State.AFTER:
                if sgn(prev_left) != sgn(left) and sgn(prev_right) != sgn(right):
                    all_notes_off()
                    left = right = 0
                    state = State.DONE

                elif sgn(prev_left) != sgn(left):
                    left = 0
                    prev_right = right
                elif sgn(prev_right) != sgn(right):
                    right = 0
                    prev_left = left
                else:
                    prev_left = left
                    prev_right = right

                outwav.writeframesraw(struct.pack('<h', left) + struct.pack('<h', right))

        #rms_left = int(40 * rms_left / l)
        #rms_right = int(40 * rms_right / l)
        #print '%s|%s\r' % (' ' * (40 - rms_left) + '#' * rms_left, '#' * rms_right + ' ' * (40 - rms_right)),
        #sys.stdout.flush()

    #print '\n'
    outwav.close()

instruments = [
    'piano',
    'marimba',
    'organ',
    'nylon_guitar',
    'dist_guitar',
    'aco_bass',
    'syn_bass',
    'strings',
    'choir',
    'brass',
    'flute',
    'synth',
    'crystal',
    'steel_drum',
    'scream',
    '808'
    ]

pitches = range(24, 107)
velocities = [60, 100, 127]

all_notes_off()

for channel, instrument in enumerate(instruments):
    for pitch in pitches:
        for velocity in velocities:
            filename = 'output/%s/%d_%d.wav' % (instrument, pitch, velocity)

            folder = os.path.dirname(filename)
            if not os.path.exists(folder):
                os.makedirs(folder)

            print 'Recording %s' % filename
            try:
                record_note(filename, channel, pitch, velocity)
                time.sleep(1)
            except Exception, e:
                print 'ERROR: Failed to record %s: %s' % (filename, e)
