"""
    Script to analyze bitstreams after wav processing
    Josh Perry
    September 2019
"""

import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import datetime

class RCPacket:
    def __init__ (self, packet_name, raw_signal, fs):
        # Class 'consts'
        self.digital_threshold = 2000 # can change

        self.name = packet_name
        self.analogue_signal = raw_signal
        self.digital_signal = None
        self.sample_freq = fs       # kHz
        self.bitstreams = []

        # Compute bitstreams
        self.discretize_signal()
        
        # Temp 
        # self.convolution_graph()
        
        self.getallpackets()

    # Discretize signal
    def discretize_signal(self):
        self.digital_signal = [0]*len(self.analogue_signal)
        index = 0

        for element in self.analogue_signal:
            digital_val = 0
            if element > self.digital_threshold:
                digital_val = 1
            self.digital_signal[index] = digital_val
            index = index + 1
        
        # Temp - plot the digital signal
        self.display_digital_sig("1", "Uncut digital signal")

    # Parse the whole signal and look for packets
    def getallpackets(self):
        print("RC PACKET: Getting all packets")

        # Loop state vars
        search_index = 0
        next_packet_name = 1

        while (search_index < len(self.digital_signal)):
            search_index = self.next_packet_search_start(search_index)
            if search_index < 0:
                break

            # New packet found
            next_packet = self.getpacket(next_packet_name, search_index)
            self.bitstreams.append(next_packet)

            search_index = next_packet.end_index
            #next_packet_name = chr(ord(next_packet_name) + 1) 
            next_packet_name = next_packet_name + 1

        # Got all bitstreams
        print("Got all bitstreams")
    
    def convolution_graph(self):
        window_len = 100
        accumulation_thresh = 10 
        integral_signal = []

        window = deque(self.digital_signal[0:window_len])
        integral = window.count(1)
        integral_signal.append(integral)

        for index in range(window_len, len(self.digital_signal)):
            next_bit = self.digital_signal[index]
            window.popleft()
            window.append(next_bit)
            integral = window.count(1)
            integral_signal.append(integral)

        RCPacket.plot_signal(integral_signal, 100, "Integral signal")


    def next_packet_search_start(self, start_index):
        # arb, based on common data pattern [specific to RC signal]
        window_len = 100
        accumulation_thresh = 10 

        window = deque(self.digital_signal[start_index : start_index + window_len])
        integral = window.count(1)
        if integral > accumulation_thresh:
            return start_index

        for index in range(start_index, len(self.digital_signal)):
            # sample is either 1 or zero
            window.popleft()
            next_bit = self.digital_signal[index]
            window.append(next_bit)

            # Compute the integral and add it to the array
            integral = window.count(1)
            if integral > accumulation_thresh:
                return index
        
        print("RC PACKET: End - no more packets. Total packets = %i" % len(self.bitstreams))
        return -1

    def getpacket(self, name, search_start_index): 
        packet_start = -1
        packet_end = -1

        for i in range(search_start_index, len(self.digital_signal)):
            bit = self.digital_signal[i]
            if bit == 1:
                # Look forward 5 samples
                filter_pass = True
                for j in range(5):
                    if self.digital_signal[i+j] == 0:
                        # Noise - false high pulse
                        filter_pass = False
                        print("RC PACKET: Noise found at index %i", i+j)
                        break
                    
                if not filter_pass:
                    continue

                # If here => true start of pre packet
                packet_start = i
                break

        # catch failed start find
        assert packet_start > 0

        # Found start, now look for end
        contiguous_lows = 0
        for k in range(packet_start, len(self.digital_signal)):
            if self.digital_signal[k] == 0:
                contiguous_lows = contiguous_lows + 1
            else:
                contiguous_lows = 0
            
            if contiguous_lows >= 50:
                # Found end + 50
                packet_end = k - 50
                break
        
        # Catch failure to find end
        assert packet_end > 0

        # Create and return bitstream
        packet_data = self.digital_signal[packet_start - 10 : packet_end + 10] # pad with 10 lows 
        packet = BitstreamPacket(name, packet_data, packet_start - 10, packet_end + 10, self.sample_freq)
        return packet 

    def display_digital_sig(self, fignum, title):
        RCPacket.plot_signal(self.digital_signal, fignum, title)

    # Analyze and print to text file - all packet data. Verbose and succinct.
    def analyze_bitstreams(self):
        print("RC PACKET: Analyzing all bitstreams")

        for bitstream in self.bitstreams:
            bitstream.analyze_all_pulses()
        
        print("RC PACKET: Completed bitstream analysis")

    def print_bitstream_analysis(self):
        for bitstream in self.bitstreams:
            bitstream.print_analysis()

    def write_bitstream_analysis_to_file(self):
        print("RC PACKET: Writing bitstream analysis to file")
        date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        filename = self.name + "_" + date_str + ".txt"
        path = "./Analysis/"
        full_path = path + filename
        out_file = open(full_path,"w") 

        for bitstream in self.bitstreams:
            bitstream.print_to_file(out_file)
        
        out_file.write("Bitstream bit comparison (ignoring pre-amble):\n\n")

        for bitstream in self.bitstreams:
            bitstream.print_bitstr_to_file(out_file, True)

        out_file.close()
        print("RC PACKET: Completed file write %s" % filename)
        
    @staticmethod
    def plot_signal(signal, fignum, title):
        plt.figure(fignum)
        plt.title(title)
        plt.plot(signal)
        plt.show()
         
class BitstreamPacket:
    def __init__(self, packet_name, bitstream, sample_start_index, sample_end_index, fs):
        self.name = packet_name
        self.bitstream = bitstream
        self.start_index = sample_start_index
        self.end_index = sample_end_index
        self.sample_freq = fs                   # In kHz
        self.sample_count = len(bitstream)

        # Defaults
        self.pulse_width_s = -1
        self.pulse_width_t = -1
        self.pulse_count = -1
        self.binary_str = "Not computed"

        # Bit determination
        self.pulses = []
        self.long_pulse_s = -1
        self.long_pulse_t = -1
        self.long_pulse_c = -1
        self.long_pulse_r = -1
        self.short_pulse_s = -1
        self.short_pulse_t = -1
        self.short_pulse_r = -1
        self.short_pulse_c = -1

        # Have a look at bitstream
        # self.display_bitstream(self.name, "Bitstream " + str(self.name))

        # Isolate pulses
        self.get_pulses()

            
    def get_pulses(self):
        pulse_count = 0
        current_bin_state = 0
        last_pulse_start_index = -1
        pulse_widths_s = []

        # Get index of first pulse [Will optimize]
        for i in range(0, self.sample_count):
            bit = self.bitstream[i]
            if bit == 1 and current_bin_state == 0:
                # Look forward 5 samples (filter)
                for j in range(i, i+5):
                    forward_bit = self.bitstream[j]
                    if j != 1:
                        continue
                
                # Found true rising edge
                pulse_count = 1
                
                # Set state
                last_pulse_start_index = i
                current_bin_state = 1
                break

        for i in range(last_pulse_start_index, self.sample_count):
            bit = self.bitstream[i]
            
            # Rising edge
            if bit == 1 and current_bin_state == 0:
                # Look forward 5 samples (filter)
                filter_pass = True
                for j in range(i, i+5):
                    forward_bit = self.bitstream[j]
                    if forward_bit != 1:
                        filter_pass = False
                        print("RE: Found noise at sample index %i" % i+j)
                        break
                if not filter_pass:
                    continue
                
                # Found true rising edge - set data
                pulse_data = self.bitstream[last_pulse_start_index : i]
                new_pulse = Pulse(pulse_data, self.sample_freq)
                self.pulses.append(new_pulse)

                # Set state
                last_pulse_start_index = i
                current_bin_state = 1

            # Falling edge
            elif bit == 0 and current_bin_state == 1:
                # Filter
                filter_pass = True
                for j in range(i, i+5):
                    forward_bit = self.bitstream[j]
                    if forward_bit != 0:
                        filter_pass = False
                        fail_index = i+j
                        print("FE: Found noise at sample index %i" % fail_index)
                        break
                if not filter_pass:
                    continue

                # Reset state
                current_bin_state = 0

        # Last pulse won't have terminal rising edge
        # Temp - think about this **
        last_pulse_width_s = self.pulses[-1].width_s
        pulse_data = self.bitstream[last_pulse_start_index : last_pulse_start_index + last_pulse_width_s]
        new_pulse = Pulse(pulse_data, self.sample_freq)
        self.pulses.append(new_pulse)

    """
        Computation of:
            1. long / short pulse (PWM encoding)
            2. Pulse count
            3. Packet length (samples + time)
    """

    def analyze_all_pulses(self): 
        self.pulse_count = len(self.pulses)
        if self.pulse_count == 0:
            print("BITSTREAM: Error - tried to analyze pulses without any registered")
            return
    
        self.binary_str = ""
        total_pulse_width_s = 0
        total_pulse_width_t = 0
        
        # Long pulse metrics
        total_lp_s = 0
        lp_count = 0
        cum_lp_ratio = 0

        # Short pulse metrics
        total_sp_s = 0
        sp_count = 0
        cum_sp_ratio = 0

        for pulse in self.pulses:
            pulse.compute_metrics()
            self.binary_str = self.binary_str + pulse.bin
            total_pulse_width_s = total_pulse_width_s + pulse.width_s

            if pulse.type == "Long":
                total_lp_s = total_lp_s + pulse.width_s
                lp_count = lp_count + 1
                cum_lp_ratio = cum_lp_ratio + pulse.ratio
            
            elif pulse.type == "Short":
                total_sp_s = total_sp_s + pulse.width_s
                sp_count = sp_count + 1
                cum_sp_ratio = cum_sp_ratio + pulse.ratio

            else:
                print("BITSTREAM: Error - unknown pulse type")
                assert False

        # Compute averages
        # Long pulses
        self.long_pulse_c = lp_count
        self.long_pulse_s = total_lp_s/lp_count
        self.long_pulse_t = self.long_pulse_s/self.sample_freq
        self.long_pulse_r = cum_lp_ratio/lp_count
        
        # Short pulses
        self.short_pulse_c = sp_count
        self.short_pulse_s = total_sp_s/sp_count
        self.short_pulse_t = self.short_pulse_s/self.sample_freq
        self.short_pulse_r = cum_sp_ratio/sp_count

        # Generic
        self.pulse_width_s = total_pulse_width_s
        self.pulse_width_t = self.pulse_width_s/self.sample_freq

    def print_analysis(self):
        print("BITSTREAM: Displaying analysis for bitstream %s:" % self.name)
        print("Total pulses: %i    len(t): %2.2f ms    len(s): %i samples" % (self.pulse_count, self.pulse_width_t, self.pulse_width_s))
        print("Long  pulses: %i    len(t): %2.2f ms    len(s)  %i samples    H/L ratio: %f" % (self.long_pulse_c, self.long_pulse_t, self.long_pulse_s, self.long_pulse_r))
        print("Short pulses: %i    len(t): %2.2f ms    len(s)  %i samples    H/L ratio: %f" % (self.short_pulse_c, self.short_pulse_t, self.short_pulse_s, self.short_pulse_r))
        print("Bitstream: %s" % self.binary_str)
        print("\n")

    def print_to_file(self, out_file):
        l1 = "BITSTREAM: Displaying analysis for bitstream " + str(self.name) + "\n"
        l2 = "Total pulses: %i    len(t): %2.2f ms    len(s): %i samples\n" % (self.pulse_count, self.pulse_width_t, self.pulse_width_s)
        l3 = "Long  pulses: %i    len(t): %2.2f ms    len(s)  %i samples    H/L ratio: %f\n" % (self.long_pulse_c, self.long_pulse_t, self.long_pulse_s, self.long_pulse_r)
        l4 = "Short pulses: %i    len(t): %2.2f ms    len(s)  %i samples    H/L ratio: %f\n" % (self.short_pulse_c, self.short_pulse_t, self.short_pulse_s, self.short_pulse_r)
        l5 = "Bitstream: %s\n\n" % self.binary_str
        lines = [l1,l2, l3, l4, l5]
        out_file.writelines(lines)

    def print_bitstr_to_file(self, out_file, skip_preamble):
        # Writes all bitstreams to file
        if not skip_preamble:
            bitstr = self.binary_str + "\n"
            out_file.write(bitstr)
            return

        # Will only write bitstreams == 66 bits to file
        if len(self.binary_str) == 13:
            bitstr = self.binary_str + "\n"
            out_file.write(bitstr)

    def display_bitstream(self, fignum, title):
        plt.figure(fignum)
        plt.title(title)
        plt.plot(self.bitstream)
        plt.show()

class Pulse:
    def __init__(self, pulse_data, fs):
        self.data = pulse_data
        self.sampling_freq = fs

        # defaults
        self.width_s = len(pulse_data)
        self.width_t = self.width_s/self.sampling_freq

        # PWM 
        self.type = "Unknown"  # Long / Short
        self.bin = "*"         # 1 / 0
        self.high_s = -1
        self.high_t = -1
        self.low_s = -1
        self.low_t = -1
        self.ratio = -1

    """
        All pulses should be of the form:
         ---
        |   |
             -----
        Where the first index is high, and the 
        requirement is to look for the falling edge
    """
    def compute_metrics(self):
        # Ensure pulse is well formed
        assert self.data[0] == 1
        falling_edge_index = -1

        # Search for falling egde
        for i in range (0, self.width_s):
            bit = self.data[i]

            if bit == 0:
                filterpass = True
                for j in range(i, i+5):
                    if self.data[j] != 0:
                        filterpass = False

                if not filterpass:
                    # false falling edge - noise
                    continue
                else:
                    # true falling edge
                    falling_edge_index = i
                    break
        
        # Falling edge sould have been found
        assert falling_edge_index > 0

        # Compute based on falling edge
        self.high_s = falling_edge_index
        self.high_t = self.high_s/self.sampling_freq
        self.low_s = self.width_s - self.high_s
        self.low_t = self.low_s/self.sampling_freq
        self.ratio = self.high_s/self.width_s

        if self.ratio > 0.6:
            self.type = "Long"
            self.bin = "0"
        else:
            self.type = "Short"
            self.bin = "1"

