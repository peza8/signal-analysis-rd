"""
    Script to analyze bitstreams after wav processing
    Josh Perry
    September 2019
"""

class RCPacket:
    def __init__ (self, packet_name, digital_signal, sample_start_index, sample_end_index, pre_packet, fs):
        self.name = packet_name
        self.signal = digital_signal
        self.start_index = sample_start_index
        self.end_index = sample_end_index
        self.pre_packet = pre_packet
        self.sample_freq = fs       # kHz

        if self.pre_packet:
            self.pre_packet = self.getpacket(self.name + "pp", 0)
            self.body = self.getpacket(self.name, self.pre_packet.end_index + 5)
        else:
            self.body = self.getpacket(self.name, 0)
            
    def getpacket(self, name, search_start_index): 
        packet_start = -1
        packet_end = -1

        for i in range(search_start_index, len(self.signal)):
            bit = self.signal[i]
            if bit == 1:
                # Look forward 5 samples
                filter_pass = True
                for j in range(5):
                    if self.signal[i+j] == 0:
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
        for k in range(packet_start, len(self.signal)):
            if self.signal[k] == 0:
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
        packet_data = self.signal[packet_start - 10 : packet_end + 10] # pad with 10 lows 
        packet = BitstreamPacket(self.name, packet_data, packet_start - 10, packet_end + 10, self.sample_freq)
        return packet 


         
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
                        print("FE: Found noise at sample index %i" % i+j)
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
            self.bin = "1"
        else:
            self.type = "Short"
            self.bin = "0"

