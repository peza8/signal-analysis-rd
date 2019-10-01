"""
    Script to analyze .wav files for RF signals
    Josh Perry
    September 2019
"""
# Includes
import matplotlib.pyplot as plt
import numpy as np
import wave
from scipy import signal
from digital_analysis import RCPacket, BitstreamPacket

# Test data
sample_315mhz = "Data/315.022_FM-Sample-Bit-Alt.wav"
sample_315mhz_2 = "Data/315.040_AM-squelsh-test.wav"
sample_315mhz_3 = "Data/315.038_AM-high-low_t1.wav"
rc_433mhz_1 = "Data/433.744_AM-RC-t1.wav"
rc_433mhz_3 = "Data/433.744_AM-RC-t3.wav"
rc_433mhz_7 = "Data/433.744_AM-RC-t7.wav"
rc_433mhz_cont_1 = "Data/433.740_AM-cont-p-t1.wav"

print("MAIN: Starting signal processing")

# tests
# x = np.linspace(0, 20, 100)  # Create a list of evenly-spaced numbers over the range
# plt.plot(x, np.sin(x))       # Plot the sine of each x point
# plt.show()                   # Display the plot

def main():
    raw_sig = wave.open(rc_433mhz_cont_1, 'rb')
    ReportWavMetrics(raw_sig)

    # Interpret
    sig_frames = GetFrameSignal(raw_sig)
    fs = raw_sig.getframerate()
    time = np.linspace(0, len(sig_frames), num=len(sig_frames))
    raw_sig.close()
    # PlotRFSignal(time, sig_frames, 1)

    # New code
    rc_packet_full = RCPacket("First continuous press", sig_frames, 48)

    # Packet A bounds
    """
    packet_A_start = 82000 - sample_start
    packet_A_end = 86600 - sample_start
    packet_A_sig = rf_digitized[packet_A_start : packet_A_end]
    rc_packet_A = RCPacket("A", packet_A_sig, 82000, 86600, False, 48)
    rc_packet_A.body.analyze_all_pulses()
    rc_packet_A.body.print_analysis()
    bitstreamA = rc_packet_A.body.bitstream
    PlotSignal(bitstreamA, 1, "Bitstream A")

    # Packet B
    packet_B_start = 87150 - sample_start
    packet_B_end = 91000 - sample_start
    packet_B_sig = rf_digitized[packet_B_start : packet_B_end]
    PlotSignal(packet_B_sig, 99, "Pakcet B Sig")
    rc_packet_B = RCPacket("B", packet_B_sig, 87000, 91000, False, 48)
    rc_packet_B.body.analyze_all_pulses()
    rc_packet_B.body.print_analysis()
    bitstreamB = rc_packet_B.body.bitstream
    PlotSignal(bitstreamB, 2, "Bitstream B")

    # Packet C
    packet_C_start = 92300 - sample_start
    packet_C_end = 96000 - sample_start
    packet_C_sig = rf_digitized[packet_C_start : packet_C_end]
    rc_packet_C = RCPacket("C", packet_C_sig, 92300, 96000, False, 48)
    rc_packet_C.body.analyze_all_pulses()
    rc_packet_C.body.print_analysis()
    bitstreamC = rc_packet_C.body.bitstream
    PlotSignal(bitstreamC, 3, "Bitstream C")

    # Packet D
    packet_D_start = 97550 - sample_start
    packet_D_end = 101200 - sample_start
    packet_D_sig = rf_digitized[packet_D_start : packet_D_end]
    rc_packet_D = RCPacket("D", packet_C_sig, 97550, 101200, False, 48)
    rc_packet_D.body.analyze_all_pulses()
    rc_packet_D.body.print_analysis()
    bitstreamD = rc_packet_D.body.bitstream
    PlotSignal(bitstreamD, 4, "Bitstream D")
    """

def ReportWavMetrics(wav_obj):
    print( "Number of channels",wav_obj.getnchannels())
    print ( "Sample width",wav_obj.getsampwidth())
    print ( "Frame rate.",wav_obj.getframerate())
    print ("Number of frames",wav_obj.getnframes())
    print ( "parameters:",wav_obj.getparams())

def GetFrameSignal(wav_obj):
    signal = wav_obj.readframes(-1)
    signal = np.fromstring(signal, 'Int16')
    return signal

def PlotRFSignal(x, y, figNum):
    plt.figure(figNum)
    plt.title('RF Signal as .wav file')
    plt.plot(x,y)
    plt.show()

def PlotSignal(y, figNum, title):
    plt.figure(figNum)
    plt.title(title)
    plt.plot(y)
    plt.show()

def LPF(sig_in, fc, fs):
    w = fc/(fs/2)           # Normalize cut off frequency
    b, a = signal.butter(5, w, 'low')
    output = signal.filtfilt(b, a, sig_in)
    return output

def DigitizeSignal(high_thresh, signal):
    # start
    digital_sig = [0]*len(signal)
    index = 0

    for element in signal:
        digital_val = 0
        if element > high_thresh:
            digital_val = 1
        digital_sig[index] = digital_val
        index = index + 1

    return digital_sig

main()