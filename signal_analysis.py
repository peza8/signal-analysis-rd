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
rc_433mhz_cont_1 = "Data/433.740_AM-cont-p-t1.wav"
rc_433mhz_cont_2 = "Data/433.744_AM-cont-p-t2.wav"
rc_433mhz_cont_3 = "Data/433.740_AM-cont-p-t3.wav"
rc_403mhz_cont_PC_MW_1 = "Data/403.546_AM-MW-cont-p-t1.wav"
rc_403mhz_cont_PC_MW_2 = "Data/403.546_AM-MW-cont-p-t2.wav"

print("MAIN: Starting signal processing")

# tests
# x = np.linspace(0, 20, 100)  # Create a list of evenly-spaced numbers over the range
# plt.plot(x, np.sin(x))       # Plot the sine of each x point
# plt.show()                   # Display the plot

def main():
    raw_sig = wave.open(rc_403mhz_cont_PC_MW_1, 'rb')
    ReportWavMetrics(raw_sig)

    # Interpret
    sig_frames = GetFrameSignal(raw_sig)
    fs = raw_sig.getframerate()
    time = np.linspace(0, len(sig_frames), num=len(sig_frames))
    raw_sig.close()
    # PlotRFSignal(time, sig_frames, 1)

    # New code
    rc_packet_full = RCPacket("403MHz-cont-p-LC-MW-t1", sig_frames[39900:79600], 48)
    rc_packet_full.analyze_bitstreams()
    rc_packet_full.print_bitstream_analysis()
    rc_packet_full.write_bitstream_analysis_to_file()

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