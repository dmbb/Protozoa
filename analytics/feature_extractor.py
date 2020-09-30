#!/usr/bin/env python
import sys
import collections
import dpkt
import socket
import os
import random
import math
import numpy as np
from scipy.stats import kurtosis, skew
from termcolor import colored 
from joblib import Parallel, delayed

def PrintColored(string, color):
    print(colored(string, color))

def PrintDynamic(string):
    print "\033[K", string, "\r",
    sys.stdout.flush()
    
def RoundToNearest(n, m):
        r = n % m
        return n + m - r if r + r >= m else n - r


DEST_IP = '192.168.5.101'
SOURCE_IP = '192.168.4.100'


def FeatureExtractionCombined(sampleFolder, cap_folder, baseline, featureFolder, baseline_name, profile, network_condition, start_time, end_time, baseline_size):
    traceInterval = end_time  # Amount of time in packet trace to consider for feature extraction

    feature_set_folder_stats = "extractedFeatures/" + cap_folder + "/" + baseline_name + "/" + profile + "/" + network_condition + '/Stats_' + str(start_time) + '_' + str(
        end_time) + "_" + str(baseline_size) + "/" + featureFolder
    if not os.path.exists(feature_set_folder_stats):
        os.makedirs(feature_set_folder_stats)

    feature_set_folder_out_stats = "extractedFeatures/" + cap_folder + "/" + baseline_name + "/" + profile + "/" + network_condition + '/OutStats_' + str(start_time) + '_' + str(
        end_time) + "_" + str(baseline_size) + "/" + featureFolder
    if not os.path.exists(feature_set_folder_out_stats):
        os.makedirs(feature_set_folder_out_stats)

    feature_set_folder_in_stats = "extractedFeatures/" + cap_folder + "/" + baseline_name + "/" + profile + "/" + network_condition + '/InStats_' + str(start_time) + '_' + str(
        end_time) + "_" + str(baseline_size) + "/" + featureFolder
    if not os.path.exists(feature_set_folder_in_stats):
        os.makedirs(feature_set_folder_in_stats)

    feature_set_folder_time_stats = "extractedFeatures/" + cap_folder + "/" + baseline_name + "/" + profile + "/" + network_condition + '/TimeStats_' + str(start_time) + '_' + str(
        end_time) + "_" + str(baseline_size) + "/" + featureFolder
    if not os.path.exists(feature_set_folder_time_stats):
        os.makedirs(feature_set_folder_time_stats)

    feature_set_folder_pl = "extractedFeatures/" + cap_folder + "/" + baseline_name + "/" + profile + "/" + network_condition + '/PL_' + str(start_time) + '_' + str(end_time) + "_" + str(
        baseline_size) + "/" + featureFolder
    if not os.path.exists(feature_set_folder_pl):
        os.makedirs(feature_set_folder_pl)


    arff_path_stats = feature_set_folder_stats + '/' + featureFolder + '.csv'
    arff_path_pl = feature_set_folder_pl + '/' + featureFolder + '.csv'

    arff_stats = open(arff_path_stats, 'wb')
    arff_pl = open(arff_path_pl, 'wb')

    written_header_stats = False
    written_header_pl = False

    udp_protocols_seen = set()

    for i, sample in enumerate(baseline):
        
        #print sampleFolder + "/" + sample + "/" + sample + "_out.pcap"
        if (".DS_Store" in sample):
            continue
        if not os.path.exists(sampleFolder + "/" + sample + "/" + sample + "_out.pcap"):
            print "Corresponding .pcap does not exist"
            continue
        statinfo = os.stat(sampleFolder + "/" + sample + "/" + sample + "_out.pcap")
        if statinfo.st_size <= 1048576:
            print "Size is less than 1MB, something went wrong with the .pcap"
            continue
        

        PrintDynamic(sampleFolder + "/" + sample + " " + str(i))

        f = open(sampleFolder + "/" + sample + "/" + sample + "_out.pcap")
        pcap = dpkt.pcap.Reader(f)

        # Analyse packets transmited
        totalPackets = 0
        totalPacketsIn = 0
        totalPacketsOut = 0

        # Analyse bytes transmitted
        totalBytes = 0
        totalBytesIn = 0
        totalBytesOut = 0

        # Analyse packet sizes
        packetSizes = []
        packetSizesIn = []
        packetSizesOut = []

        bin_dict = {}
        bin_dict2 = {}
        binWidth = 5
        # Generate the set of all possible bins
        for i in range(0, 1500, binWidth):
            bin_dict[i] = 0
            bin_dict2[i] = 0

        # Analyse inter packet timing
        packetTimes = []
        packetTimesIn = []
        packetTimesOut = []

        # Analyse outcoming bursts
        out_bursts_packets = []
        out_burst_sizes = []
        out_burst_times = []
        out_burst_start = 0
        out_current_burst = 0
        out_current_burst_start = 0
        out_current_burst_size = 0
        out_current_burst_time = 0

        # Analyse incoming bursts
        in_bursts_packets = []
        in_burst_sizes = []
        in_burst_times = []
        in_burst_start = 0
        in_current_burst = 0
        in_current_burst_start = 0
        in_current_burst_size = 0
        in_current_burst_time = 0

        prev_ts = 0
        absTimesOut = []
        firstTime = start_time
        setFirst = False
        for ts, buf in pcap:
            if (not (setFirst)):
                firstTime = ts
                setFirst = True

            if (ts < (firstTime + traceInterval)):

                eth = dpkt.ethernet.Ethernet(buf)
                ip_hdr = eth.data
                try:
                    src_ip_addr_str = socket.inet_ntoa(ip_hdr.src)
                    dst_ip_addr_str = socket.inet_ntoa(ip_hdr.dst)

                    udp_hdr = ip_hdr.data

                    # Target UDP communication between both cluster machines
                    if (ip_hdr.p == 17 and ((dst_ip_addr_str == SOURCE_IP and src_ip_addr_str == DEST_IP) or (src_ip_addr_str == SOURCE_IP and dst_ip_addr_str == DEST_IP)) and
                            (udp_hdr.data[0] != '\x00' and udp_hdr.data[1] != '\x01') and #Not STUN
                            (udp_hdr.data[0] != '\x01' and udp_hdr.data[1] != '\x01') and
                            (udp_hdr.data[0] != '\x01' and udp_hdr.data[1] != '\x11') and
                            (udp_hdr.data[0] != '\x00' and udp_hdr.data[1] != '\x02') and
                            (udp_hdr.data[0] != '\x01' and udp_hdr.data[1] != '\x02') and
                            (udp_hdr.data[0] != '\x01' and udp_hdr.data[1] != '\x12') and
                            (udp_hdr.data[0] != '\x01' and udp_hdr.data[1] != '\x15') and
                            (udp_hdr.data[0] != '\x16')): #Not DTLS

                        # General packet statistics
                        udp_protocols_seen.add(str(udp_hdr.data[0]) + ", " + str(udp_hdr.data[1]))
                        totalPackets += 1

                        # If source is recipient
                        if (src_ip_addr_str == DEST_IP):
                            totalPacketsIn += 1
                            packetSizesIn.append(len(buf))
                            binned = RoundToNearest(len(buf), binWidth)
                            bin_dict2[binned] += 1
                            if (prev_ts != 0):
                                ts_difference = max(0, ts - prev_ts)
                                packetTimesIn.append(ts_difference * 1000)

                            if (out_current_burst != 0):
                                if (out_current_burst > 1):
                                    out_bursts_packets.append(out_current_burst)  # packets on burst
                                    out_burst_sizes.append(out_current_burst_size)  # total bytes on burst
                                    out_burst_times.append(ts - out_current_burst_start)
                                out_current_burst = 0
                                out_current_burst_size = 0
                                out_current_burst_start = 0
                            if (in_current_burst == 0):
                                in_current_burst_start = ts
                            in_current_burst += 1
                            in_current_burst_size += len(buf)
                        # If source is caller
                        else:
                            totalPacketsOut += 1
                            absTimesOut.append(ts)
                            packetSizesOut.append(len(buf))
                            binned = RoundToNearest(len(buf), binWidth)
                            bin_dict[binned] += 1
                            if (prev_ts != 0):
                                ts_difference = max(0, ts - prev_ts)
                                packetTimesOut.append(ts_difference * 1000)
                            if (out_current_burst == 0):
                                out_current_burst_start = ts
                            out_current_burst += 1
                            out_current_burst_size += len(buf)

                            if (in_current_burst != 0):
                                if (in_current_burst > 1):
                                    in_bursts_packets.append(out_current_burst)  # packets on burst
                                    in_burst_sizes.append(out_current_burst_size)  # total bytes on burst
                                    in_burst_times.append(ts - out_current_burst_start)
                                in_current_burst = 0
                                in_current_burst_size = 0
                                in_current_burst_start = 0

                        # Bytes transmitted statistics
                        totalBytes += len(buf)
                        if (src_ip_addr_str == DEST_IP):
                            totalBytesIn += len(buf)
                        else:
                            totalBytesOut += len(buf)

                        # Packet Size statistics
                        packetSizes.append(len(buf))

                        # Packet Times statistics
                        if (prev_ts != 0):
                            # print "{0:.6f}".format(ts)
                            ts_difference = max(0, ts - prev_ts)
                            packetTimes.append(ts_difference * 1000)

                        prev_ts = ts
                except:
                    pass
        f.close()

        ################################################################
        ####################Compute statistics#####################
        ################################################################

        try:
            ##########################################################
            # Statistical indicators for packet sizes (total)
            meanPacketSizes = np.mean(packetSizes)
            medianPacketSizes = np.median(packetSizes)
            stdevPacketSizes = np.std(packetSizes)
            variancePacketSizes = np.var(packetSizes)
            kurtosisPacketSizes = kurtosis(packetSizes)
            skewPacketSizes = skew(packetSizes)
            maxPacketSize = np.amax(packetSizes)
            minPacketSize = np.amin(packetSizes)
            p10PacketSizes = np.percentile(packetSizes, 10)
            p20PacketSizes = np.percentile(packetSizes, 20)
            p30PacketSizes = np.percentile(packetSizes, 30)
            p40PacketSizes = np.percentile(packetSizes, 40)
            p50PacketSizes = np.percentile(packetSizes, 50)
            p60PacketSizes = np.percentile(packetSizes, 60)
            p70PacketSizes = np.percentile(packetSizes, 70)
            p80PacketSizes = np.percentile(packetSizes, 80)
            p90PacketSizes = np.percentile(packetSizes, 90)

            ##########################################################
            # Statistical indicators for packet sizes (in)
            meanPacketSizesIn = np.mean(packetSizesIn)
            medianPacketSizesIn = np.median(packetSizesIn)
            stdevPacketSizesIn = np.std(packetSizesIn)
            variancePacketSizesIn = np.var(packetSizesIn)
            kurtosisPacketSizesIn = kurtosis(packetSizesIn)
            skewPacketSizesIn = skew(packetSizesIn)
            maxPacketSizeIn = np.amax(packetSizesIn)
            minPacketSizeIn = np.amin(packetSizesIn)
            p10PacketSizesIn = np.percentile(packetSizesIn, 10)
            p20PacketSizesIn = np.percentile(packetSizesIn, 20)
            p30PacketSizesIn = np.percentile(packetSizesIn, 30)
            p40PacketSizesIn = np.percentile(packetSizesIn, 40)
            p50PacketSizesIn = np.percentile(packetSizesIn, 50)
            p60PacketSizesIn = np.percentile(packetSizesIn, 60)
            p70PacketSizesIn = np.percentile(packetSizesIn, 70)
            p80PacketSizesIn = np.percentile(packetSizesIn, 80)
            p90PacketSizesIn = np.percentile(packetSizesIn, 90)

            ##########################################################
            # Statistical indicators for packet sizes (out)
            meanPacketSizesOut = np.mean(packetSizesOut)
            medianPacketSizesOut = np.median(packetSizesOut)
            stdevPacketSizesOut = np.std(packetSizesOut)
            variancePacketSizesOut = np.var(packetSizesOut)
            kurtosisPacketSizesOut = kurtosis(packetSizesOut)
            skewPacketSizesOut = skew(packetSizesOut)
            maxPacketSizeOut = np.amax(packetSizesOut)
            minPacketSizeOut = np.amin(packetSizesOut)
            p10PacketSizesOut = np.percentile(packetSizesOut, 10)
            p20PacketSizesOut = np.percentile(packetSizesOut, 20)
            p30PacketSizesOut = np.percentile(packetSizesOut, 30)
            p40PacketSizesOut = np.percentile(packetSizesOut, 40)
            p50PacketSizesOut = np.percentile(packetSizesOut, 50)
            p60PacketSizesOut = np.percentile(packetSizesOut, 60)
            p70PacketSizesOut = np.percentile(packetSizesOut, 70)
            p80PacketSizesOut = np.percentile(packetSizesOut, 80)
            p90PacketSizesOut = np.percentile(packetSizesOut, 90)

            ##################################################################
            # Statistical indicators for Inter-Packet Times (total)

            meanPacketTimes = np.mean(packetTimes)
            medianPacketTimes = np.median(packetTimes)
            stdevPacketTimes = np.std(packetTimes)
            variancePacketTimes = np.var(packetTimes)
            kurtosisPacketTimes = kurtosis(packetTimes)
            skewPacketTimes = skew(packetTimes)
            maxIPT = np.amax(packetTimes)
            minIPT = np.amin(packetTimes)
            p10PacketTimes = np.percentile(packetTimes, 10)
            p20PacketTimes = np.percentile(packetTimes, 20)
            p30PacketTimes = np.percentile(packetTimes, 30)
            p40PacketTimes = np.percentile(packetTimes, 40)
            p50PacketTimes = np.percentile(packetTimes, 50)
            p60PacketTimes = np.percentile(packetTimes, 60)
            p70PacketTimes = np.percentile(packetTimes, 70)
            p80PacketTimes = np.percentile(packetTimes, 80)
            p90PacketTimes = np.percentile(packetTimes, 90)

            ##################################################################
            # Statistical indicators for Inter-Packet Times (in)
            meanPacketTimesIn = np.mean(packetTimesIn)
            medianPacketTimesIn = np.median(packetTimesIn)
            stdevPacketTimesIn = np.std(packetTimesIn)
            variancePacketTimesIn = np.var(packetTimesIn)
            kurtosisPacketTimesIn = kurtosis(packetTimesIn)
            skewPacketTimesIn = skew(packetTimesIn)
            maxPacketTimesIn = np.amax(packetTimesIn)
            minPacketTimesIn = np.amin(packetTimesIn)
            p10PacketTimesIn = np.percentile(packetTimesIn, 10)
            p20PacketTimesIn = np.percentile(packetTimesIn, 20)
            p30PacketTimesIn = np.percentile(packetTimesIn, 30)
            p40PacketTimesIn = np.percentile(packetTimesIn, 40)
            p50PacketTimesIn = np.percentile(packetTimesIn, 50)
            p60PacketTimesIn = np.percentile(packetTimesIn, 60)
            p70PacketTimesIn = np.percentile(packetTimesIn, 70)
            p80PacketTimesIn = np.percentile(packetTimesIn, 80)
            p90PacketTimesIn = np.percentile(packetTimesIn, 90)

            ##################################################################
            # Statistical indicators for Inter-Packet Times (out)
            meanPacketTimesOut = np.mean(packetTimesOut)
            medianPacketTimesOut = np.median(packetTimesOut)
            stdevPacketTimesOut = np.std(packetTimesOut)
            variancePacketTimesOut = np.var(packetTimesOut)
            kurtosisPacketTimesOut = kurtosis(packetTimesOut)
            skewPacketTimesOut = skew(packetTimesOut)
            maxPacketTimesOut = np.amax(packetTimesOut)
            minPacketTimesOut = np.amin(packetTimesOut)
            p10PacketTimesOut = np.percentile(packetTimesOut, 10)
            p20PacketTimesOut = np.percentile(packetTimesOut, 20)
            p30PacketTimesOut = np.percentile(packetTimesOut, 30)
            p40PacketTimesOut = np.percentile(packetTimesOut, 40)
            p50PacketTimesOut = np.percentile(packetTimesOut, 50)
            p60PacketTimesOut = np.percentile(packetTimesOut, 60)
            p70PacketTimesOut = np.percentile(packetTimesOut, 70)
            p80PacketTimesOut = np.percentile(packetTimesOut, 80)
            p90PacketTimesOut = np.percentile(packetTimesOut, 90)

            ########################################################################
            # Statistical indicators for Outgoing bursts

            out_totalBursts = len(out_bursts_packets)
            out_meanBurst = np.mean(out_bursts_packets)
            out_medianBurst = np.median(out_bursts_packets)
            out_stdevBurst = np.std(out_bursts_packets)
            out_varianceBurst = np.var(out_bursts_packets)
            out_maxBurst = np.amax(out_bursts_packets)
            out_kurtosisBurst = kurtosis(out_bursts_packets)
            out_skewBurst = skew(out_bursts_packets)
            out_p10Burst = np.percentile(out_bursts_packets, 10)
            out_p20Burst = np.percentile(out_bursts_packets, 20)
            out_p30Burst = np.percentile(out_bursts_packets, 30)
            out_p40Burst = np.percentile(out_bursts_packets, 40)
            out_p50Burst = np.percentile(out_bursts_packets, 50)
            out_p60Burst = np.percentile(out_bursts_packets, 60)
            out_p70Burst = np.percentile(out_bursts_packets, 70)
            out_p80Burst = np.percentile(out_bursts_packets, 80)
            out_p90Burst = np.percentile(out_bursts_packets, 90)

            ########################################################################
            # Statistical indicators for Outgoing bytes (sliced intervals)
            out_meanBurstBytes = np.mean(out_burst_sizes)
            out_medianBurstBytes = np.median(out_burst_sizes)
            out_stdevBurstBytes = np.std(out_burst_sizes)
            out_varianceBurstBytes = np.var(out_burst_sizes)
            out_kurtosisBurstBytes = kurtosis(out_burst_sizes)
            out_skewBurstBytes = skew(out_burst_sizes)
            out_maxBurstBytes = np.amax(out_burst_sizes)
            out_minBurstBytes = np.amin(out_burst_sizes)
            out_p10BurstBytes = np.percentile(out_burst_sizes, 10)
            out_p20BurstBytes = np.percentile(out_burst_sizes, 20)
            out_p30BurstBytes = np.percentile(out_burst_sizes, 30)
            out_p40BurstBytes = np.percentile(out_burst_sizes, 40)
            out_p50BurstBytes = np.percentile(out_burst_sizes, 50)
            out_p60BurstBytes = np.percentile(out_burst_sizes, 60)
            out_p70BurstBytes = np.percentile(out_burst_sizes, 70)
            out_p80BurstBytes = np.percentile(out_burst_sizes, 80)
            out_p90BurstBytes = np.percentile(out_burst_sizes, 90)

            ########################################################################
            # Statistical indicators for Incoming bursts

            in_totalBursts = len(in_bursts_packets)
            in_meanBurst = np.mean(in_bursts_packets)
            in_medianBurst = np.median(in_bursts_packets)
            in_stdevBurst = np.std(in_bursts_packets)
            in_varianceBurst = np.var(in_bursts_packets)
            in_maxBurst = np.amax(in_bursts_packets)
            in_kurtosisBurst = kurtosis(in_bursts_packets)
            in_skewBurst = skew(in_bursts_packets)
            in_p10Burst = np.percentile(in_bursts_packets, 10)
            in_p20Burst = np.percentile(in_bursts_packets, 20)
            in_p30Burst = np.percentile(in_bursts_packets, 30)
            in_p40Burst = np.percentile(in_bursts_packets, 40)
            in_p50Burst = np.percentile(in_bursts_packets, 50)
            in_p60Burst = np.percentile(in_bursts_packets, 60)
            in_p70Burst = np.percentile(in_bursts_packets, 70)
            in_p80Burst = np.percentile(in_bursts_packets, 80)
            in_p90Burst = np.percentile(in_bursts_packets, 90)

            ########################################################################
            # Statistical indicators for Incoming burst bytes (sliced intervals)
            in_meanBurstBytes = np.mean(in_burst_sizes)
            in_medianBurstBytes = np.median(in_burst_sizes)
            in_stdevBurstBytes = np.std(in_burst_sizes)
            in_varianceBurstBytes = np.var(in_burst_sizes)
            in_kurtosisBurstBytes = kurtosis(in_burst_sizes)
            in_skewBurstBytes = skew(in_burst_sizes)
            in_maxBurstBytes = np.amax(in_burst_sizes)
            in_minBurstBytes = np.amin(in_burst_sizes)
            in_p10BurstBytes = np.percentile(in_burst_sizes, 10)
            in_p20BurstBytes = np.percentile(in_burst_sizes, 20)
            in_p30BurstBytes = np.percentile(in_burst_sizes, 30)
            in_p40BurstBytes = np.percentile(in_burst_sizes, 40)
            in_p50BurstBytes = np.percentile(in_burst_sizes, 50)
            in_p60BurstBytes = np.percentile(in_burst_sizes, 60)
            in_p70BurstBytes = np.percentile(in_burst_sizes, 70)
            in_p80BurstBytes = np.percentile(in_burst_sizes, 80)
            in_p90BurstBytes = np.percentile(in_burst_sizes, 90)
        except:
            print "Error when processing " + sampleFolder + "/" + sample + "/" + sample + "_out.pcap"
            print "Skipping sample"
            continue

        label = featureFolder

        # Write sample features to the csv file
        f_names_stats = []
        f_values_stats = []

        f_names_pl = []
        f_values_pl = []

        od_dict = collections.OrderedDict(sorted(bin_dict.items(), key=lambda t: float(t[0])))
        bin_list = []
        for i in od_dict:
            bin_list.append(od_dict[i])

        od_dict2 = collections.OrderedDict(sorted(bin_dict2.items(), key=lambda t: float(t[0])))
        bin_list2 = []
        for i in od_dict2:
            bin_list2.append(od_dict2[i])

        ###################################################################
        # Global Packet Features
        f_names_stats.append('TotalPackets')
        f_values_stats.append(totalPackets)
        f_names_stats.append('totalPacketsIn')
        f_values_stats.append(totalPacketsIn)
        f_names_stats.append('totalPacketsOut')
        f_values_stats.append(totalPacketsOut)
        f_names_stats.append('totalBytes')
        f_values_stats.append(totalBytes)
        f_names_stats.append('totalBytesIn')
        f_values_stats.append(totalBytesIn)
        f_names_stats.append('totalBytesOut')
        f_values_stats.append(totalBytesOut)

        ###################################################################
        # Packet Length Features
        f_names_stats.append('minPacketSize')
        f_values_stats.append(minPacketSize)
        f_names_stats.append('maxPacketSize')
        f_values_stats.append(maxPacketSize)
        # f_names_stats.append('medianPacketSizes')
        # f_values_stats.append(medianPacketSizes)
        f_names_stats.append('meanPacketSizes')
        f_values_stats.append(meanPacketSizes)
        f_names_stats.append('stdevPacketSizes')
        f_values_stats.append(stdevPacketSizes)
        f_names_stats.append('variancePacketSizes')
        f_values_stats.append(variancePacketSizes)
        f_names_stats.append('kurtosisPacketSizes')
        f_values_stats.append(kurtosisPacketSizes)
        f_names_stats.append('skewPacketSizes')
        f_values_stats.append(skewPacketSizes)

        f_names_stats.append('p10PacketSizes')
        f_values_stats.append(p10PacketSizes)
        f_names_stats.append('p20PacketSizes')
        f_values_stats.append(p20PacketSizes)
        f_names_stats.append('p30PacketSizes')
        f_values_stats.append(p30PacketSizes)
        f_names_stats.append('p40PacketSizes')
        f_values_stats.append(p40PacketSizes)
        f_names_stats.append('p50PacketSizes')
        f_values_stats.append(p50PacketSizes)
        f_names_stats.append('p60PacketSizes')
        f_values_stats.append(p60PacketSizes)
        f_names_stats.append('p70PacketSizes')
        f_values_stats.append(p70PacketSizes)
        f_names_stats.append('p80PacketSizes')
        f_values_stats.append(p80PacketSizes)
        f_names_stats.append('p90PacketSizes')
        f_values_stats.append(p90PacketSizes)

        ###################################################################
        # Packet Length Features (in)
        f_names_stats.append('minPacketSizeIn')
        f_values_stats.append(minPacketSizeIn)
        f_names_stats.append('maxPacketSizeIn')
        f_values_stats.append(maxPacketSizeIn)
        # f_names_stats.append('medianPacketSizesIn')
        # f_values_stats.append(medianPacketSizesIn)
        f_names_stats.append('meanPacketSizesIn')
        f_values_stats.append(meanPacketSizesIn)
        f_names_stats.append('stdevPacketSizesIn')
        f_values_stats.append(stdevPacketSizesIn)
        f_names_stats.append('variancePacketSizesIn')
        f_values_stats.append(variancePacketSizesIn)
        f_names_stats.append('skewPacketSizesIn')
        f_values_stats.append(skewPacketSizesIn)
        f_names_stats.append('kurtosisPacketSizesIn')
        f_values_stats.append(kurtosisPacketSizesIn)

        f_names_stats.append('p10PacketSizesIn')
        f_values_stats.append(p10PacketSizesIn)
        f_names_stats.append('p20PacketSizesIn')
        f_values_stats.append(p20PacketSizesIn)
        f_names_stats.append('p30PacketSizesIn')
        f_values_stats.append(p30PacketSizesIn)
        f_names_stats.append('p40PacketSizesIn')
        f_values_stats.append(p40PacketSizesIn)
        f_names_stats.append('p50PacketSizesIn')
        f_values_stats.append(p50PacketSizesIn)
        f_names_stats.append('p60PacketSizesIn')
        f_values_stats.append(p60PacketSizesIn)
        f_names_stats.append('p70PacketSizesIn')
        f_values_stats.append(p70PacketSizesIn)
        f_names_stats.append('p80PacketSizesIn')
        f_values_stats.append(p80PacketSizesIn)
        f_names_stats.append('p90PacketSizesIn')
        f_values_stats.append(p90PacketSizesIn)

        ###################################################################
        # Packet Length Features (out)
        f_names_stats.append('minPacketSizeOut')
        f_values_stats.append(minPacketSizeOut)
        f_names_stats.append('maxPacketSizeOut')
        f_values_stats.append(maxPacketSizeOut)
        # f_names_stats.append('medianPacketSizesOut')
        # f_values_stats.append(medianPacketSizesOut)
        f_names_stats.append('meanPacketSizesOut')
        f_values_stats.append(meanPacketSizesOut)
        f_names_stats.append('stdevPacketSizesOut')
        f_values_stats.append(stdevPacketSizesOut)
        f_names_stats.append('variancePacketSizesOut')
        f_values_stats.append(variancePacketSizesOut)
        f_names_stats.append('skewPacketSizesOut')
        f_values_stats.append(skewPacketSizesOut)
        f_names_stats.append('kurtosisPacketSizesOut')
        f_values_stats.append(kurtosisPacketSizesOut)

        f_names_stats.append('p10PacketSizesOut')
        f_values_stats.append(p10PacketSizesOut)
        f_names_stats.append('p20PacketSizesOut')
        f_values_stats.append(p20PacketSizesOut)
        f_names_stats.append('p30PacketSizesOut')
        f_values_stats.append(p30PacketSizesOut)
        f_names_stats.append('p40PacketSizesOut')
        f_values_stats.append(p40PacketSizesOut)
        f_names_stats.append('p50PacketSizesOut')
        f_values_stats.append(p50PacketSizesOut)
        f_names_stats.append('p60PacketSizesOut')
        f_values_stats.append(p60PacketSizesOut)
        f_names_stats.append('p70PacketSizesOut')
        f_values_stats.append(p70PacketSizesOut)
        f_names_stats.append('p80PacketSizesOut')
        f_values_stats.append(p80PacketSizesOut)
        f_names_stats.append('p90PacketSizesOut')
        f_values_stats.append(p90PacketSizesOut)

        ###################################################################
        # Packet Timing Features
        f_names_stats.append('maxIPT')
        f_values_stats.append(maxIPT)
        f_names_stats.append('minIPT')
        f_values_stats.append(minIPT)
        # f_names_stats.append('medianPacketTimes')
        # f_values_stats.append(medianPacketTimes)
        f_names_stats.append('meanPacketTimes')
        f_values_stats.append(meanPacketTimes)
        f_names_stats.append('stdevPacketTimes')
        f_values_stats.append(stdevPacketTimes)
        f_names_stats.append('variancePacketTimes')
        f_values_stats.append(variancePacketTimes)
        f_names_stats.append('kurtosisPacketTimes')
        f_values_stats.append(kurtosisPacketTimes)
        f_names_stats.append('skewPacketTimes')
        f_values_stats.append(skewPacketTimes)

        f_names_stats.append('p10PacketTimes')
        f_values_stats.append(p10PacketTimes)
        f_names_stats.append('p20PacketTimes')
        f_values_stats.append(p20PacketTimes)
        f_names_stats.append('p30PacketTimes')
        f_values_stats.append(p30PacketTimes)
        f_names_stats.append('p40PacketTimes')
        f_values_stats.append(p40PacketTimes)
        f_names_stats.append('p50PacketTimes')
        f_values_stats.append(p50PacketTimes)
        f_names_stats.append('p60PacketTimes')
        f_values_stats.append(p60PacketTimes)
        f_names_stats.append('p70PacketTimes')
        f_values_stats.append(p70PacketTimes)
        f_names_stats.append('p80PacketTimes')
        f_values_stats.append(p80PacketTimes)
        f_names_stats.append('p90PacketTimes')
        f_values_stats.append(p90PacketTimes)

        ###################################################################
        # Packet Timing Features (in)
        f_names_stats.append('minPacketTimesIn')
        f_values_stats.append(minPacketTimesIn)
        f_names_stats.append('maxPacketTimesIn')
        f_values_stats.append(maxPacketTimesIn)
        # f_names_stats.append('medianPacketTimesIn')
        # f_values_stats.append(medianPacketTimesIn)
        f_names_stats.append('meanPacketTimesIn')
        f_values_stats.append(meanPacketTimesIn)
        f_names_stats.append('stdevPacketTimesIn')
        f_values_stats.append(stdevPacketTimesIn)
        f_names_stats.append('variancePacketTimesIn')
        f_values_stats.append(variancePacketTimesIn)
        f_names_stats.append('skewPacketTimesIn')
        f_values_stats.append(skewPacketTimesIn)
        f_names_stats.append('kurtosisPacketTimesIn')
        f_values_stats.append(kurtosisPacketTimesIn)

        f_names_stats.append('p10PacketTimesIn')
        f_values_stats.append(p10PacketTimesIn)
        f_names_stats.append('p20PacketTimesIn')
        f_values_stats.append(p20PacketTimesIn)
        f_names_stats.append('p30PacketTimesIn')
        f_values_stats.append(p30PacketTimesIn)
        f_names_stats.append('p40PacketTimesIn')
        f_values_stats.append(p40PacketTimesIn)
        f_names_stats.append('p50PacketTimesIn')
        f_values_stats.append(p50PacketTimesIn)
        f_names_stats.append('p60PacketTimesIn')
        f_values_stats.append(p60PacketTimesIn)
        f_names_stats.append('p70PacketTimesIn')
        f_values_stats.append(p70PacketTimesIn)
        f_names_stats.append('p80PacketTimesIn')
        f_values_stats.append(p80PacketTimesIn)
        f_names_stats.append('p90PacketTimesIn')
        f_values_stats.append(p90PacketTimesIn)

        ###################################################################
        # Packet Timing Features (out)
        f_names_stats.append('minPacketTimesOut')
        f_values_stats.append(minPacketTimesOut)
        f_names_stats.append('maxPacketTimesOut')
        f_values_stats.append(maxPacketTimesOut)
        # f_names_stats.append('medianPacketTimesOut')
        # f_values_stats.append(medianPacketTimesOut)
        f_names_stats.append('meanPacketTimesOut')
        f_values_stats.append(meanPacketTimesOut)
        f_names_stats.append('stdevPacketTimesOut')
        f_values_stats.append(stdevPacketTimesOut)
        f_names_stats.append('variancePacketTimesOut')
        f_values_stats.append(variancePacketTimesOut)
        f_names_stats.append('skewPacketTimesOut')
        f_values_stats.append(skewPacketTimesOut)
        f_names_stats.append('kurtosisPacketTimesOut')
        f_values_stats.append(kurtosisPacketTimesOut)

        f_names_stats.append('p10PacketTimesOut')
        f_values_stats.append(p10PacketTimesOut)
        f_names_stats.append('p20PacketTimesOut')
        f_values_stats.append(p20PacketTimesOut)
        f_names_stats.append('p30PacketTimesOut')
        f_values_stats.append(p30PacketTimesOut)
        f_names_stats.append('p40PacketTimesOut')
        f_values_stats.append(p40PacketTimesOut)
        f_names_stats.append('p50PacketTimesOut')
        f_values_stats.append(p50PacketTimesOut)
        f_names_stats.append('p60PacketTimesOut')
        f_values_stats.append(p60PacketTimesOut)
        f_names_stats.append('p70PacketTimesOut')
        f_values_stats.append(p70PacketTimesOut)
        f_names_stats.append('p80PacketTimesOut')
        f_values_stats.append(p80PacketTimesOut)
        f_names_stats.append('p90PacketTimesOut')
        f_values_stats.append(p90PacketTimesOut)

        #################################################################
        # Outgoing Packet number of Bursts features
        f_names_stats.append('out_totalBursts')
        f_values_stats.append(out_totalBursts)
        f_names_stats.append('out_maxBurst')
        f_values_stats.append(out_maxBurst)
        f_names_stats.append('out_meanBurst')
        f_values_stats.append(out_meanBurst)
        # f_names_stats.append('out_medianBurst')
        # f_values_stats.append(out_medianBurst)
        f_names_stats.append('out_stdevBurst')
        f_values_stats.append(out_stdevBurst)
        f_names_stats.append('out_varianceBurst')
        f_values_stats.append(out_varianceBurst)
        f_names_stats.append('out_kurtosisBurst')
        f_values_stats.append(out_kurtosisBurst)
        f_names_stats.append('out_skewBurst')
        f_values_stats.append(out_skewBurst)

        f_names_stats.append('out_p10Burst')
        f_values_stats.append(out_p10Burst)
        f_names_stats.append('out_p20Burst')
        f_values_stats.append(out_p20Burst)
        f_names_stats.append('out_p30Burst')
        f_values_stats.append(out_p30Burst)
        f_names_stats.append('out_p40Burst')
        f_values_stats.append(out_p40Burst)
        f_names_stats.append('out_p50Burst')
        f_values_stats.append(out_p50Burst)
        f_names_stats.append('out_p60Burst')
        f_values_stats.append(out_p60Burst)
        f_names_stats.append('out_p70Burst')
        f_values_stats.append(out_p70Burst)
        f_names_stats.append('out_p80Burst')
        f_values_stats.append(out_p80Burst)
        f_names_stats.append('out_p90Burst')
        f_values_stats.append(out_p90Burst)

        #################################################################
        # Outgoing Packet Bursts data size features
        f_names_stats.append('out_maxBurstBytes')
        f_values_stats.append(out_maxBurstBytes)
        f_names_stats.append('out_minBurstBytes')
        f_values_stats.append(out_minBurstBytes)
        f_names_stats.append('out_meanBurstBytes')
        f_values_stats.append(out_meanBurstBytes)
        # f_names_stats.append('out_medianBurstBytes')
        # f_values_stats.append(out_medianBurstBytes)
        f_names_stats.append('out_stdevBurstBytes')
        f_values_stats.append(out_stdevBurstBytes)
        f_names_stats.append('out_varianceBurstBytes')
        f_values_stats.append(out_varianceBurstBytes)
        f_names_stats.append('out_kurtosisBurstBytes')
        f_values_stats.append(out_kurtosisBurstBytes)
        f_names_stats.append('out_skewBurstBytes')
        f_values_stats.append(out_skewBurstBytes)

        f_names_stats.append('out_p10BurstBytes')
        f_values_stats.append(out_p10BurstBytes)
        f_names_stats.append('out_p20BurstBytes')
        f_values_stats.append(out_p20BurstBytes)
        f_names_stats.append('out_p30BurstBytes')
        f_values_stats.append(out_p30BurstBytes)
        f_names_stats.append('out_p40BurstBytes')
        f_values_stats.append(out_p40BurstBytes)
        f_names_stats.append('out_p50BurstBytes')
        f_values_stats.append(out_p50BurstBytes)
        f_names_stats.append('out_p60BurstBytes')
        f_values_stats.append(out_p60BurstBytes)
        f_names_stats.append('out_p70BurstBytes')
        f_values_stats.append(out_p70BurstBytes)
        f_names_stats.append('out_p80BurstBytes')
        f_values_stats.append(out_p80BurstBytes)
        f_names_stats.append('out_p90BurstBytes')
        f_values_stats.append(out_p90BurstBytes)

        #################################################################
        # Incoming Packet number of Bursts features
        f_names_stats.append('in_totalBursts')
        f_values_stats.append(in_totalBursts)
        f_names_stats.append('in_maxBurst')
        f_values_stats.append(in_maxBurst)
        f_names_stats.append('in_meanBurst')
        f_values_stats.append(in_meanBurst)
        f_names_stats.append('in_stdevBurst')
        f_values_stats.append(in_stdevBurst)
        f_names_stats.append('in_varianceBurst')
        f_values_stats.append(in_varianceBurst)
        f_names_stats.append('in_kurtosisBurst')
        f_values_stats.append(in_kurtosisBurst)
        f_names_stats.append('in_skewBurst')
        f_values_stats.append(in_skewBurst)

        f_names_stats.append('in_p10Burst')
        f_values_stats.append(in_p10Burst)
        f_names_stats.append('in_p20Burst')
        f_values_stats.append(in_p20Burst)
        f_names_stats.append('in_p30Burst')
        f_values_stats.append(in_p30Burst)
        f_names_stats.append('in_p40Burst')
        f_values_stats.append(in_p40Burst)
        f_names_stats.append('in_p50Burst')
        f_values_stats.append(in_p50Burst)
        f_names_stats.append('in_p60Burst')
        f_values_stats.append(in_p60Burst)
        f_names_stats.append('in_p70Burst')
        f_values_stats.append(in_p70Burst)
        f_names_stats.append('in_p80Burst')
        f_values_stats.append(in_p80Burst)
        f_names_stats.append('in_p90Burst')
        f_values_stats.append(in_p90Burst)

        #################################################################
        # Incoming Packet Bursts data size features
        f_names_stats.append('in_maxBurstBytes')
        f_values_stats.append(in_maxBurstBytes)
        f_names_stats.append('in_minBurstBytes')
        f_values_stats.append(in_minBurstBytes)
        f_names_stats.append('in_meanBurstBytes')
        f_values_stats.append(in_meanBurstBytes)
        # f_names_stats.append('in_medianBurstBytes')
        # f_values_stats.append(in_medianBurstBytes)
        f_names_stats.append('in_stdevBurstBytes')
        f_values_stats.append(in_stdevBurstBytes)
        f_names_stats.append('in_varianceBurstBytes')
        f_values_stats.append(in_varianceBurstBytes)
        f_names_stats.append('in_kurtosisBurstBytes')
        f_values_stats.append(in_kurtosisBurstBytes)
        f_names_stats.append('in_skewBurstBytes')
        f_values_stats.append(in_skewBurstBytes)

        f_names_stats.append('in_p10BurstBytes')
        f_values_stats.append(in_p10BurstBytes)
        f_names_stats.append('in_p20BurstBytes')
        f_values_stats.append(in_p20BurstBytes)
        f_names_stats.append('in_p30BurstBytes')
        f_values_stats.append(in_p30BurstBytes)
        f_names_stats.append('in_p40BurstBytes')
        f_values_stats.append(in_p40BurstBytes)
        f_names_stats.append('in_p50BurstBytes')
        f_values_stats.append(in_p50BurstBytes)
        f_names_stats.append('in_p60BurstBytes')
        f_values_stats.append(in_p60BurstBytes)
        f_names_stats.append('in_p70BurstBytes')
        f_values_stats.append(in_p70BurstBytes)
        f_names_stats.append('in_p80BurstBytes')
        f_values_stats.append(in_p80BurstBytes)
        f_names_stats.append('in_p90BurstBytes')
        f_values_stats.append(in_p90BurstBytes)


        # Write Stats csv
        f_names_stats.append('Class')
        f_values_stats.append(label)

        if (not written_header_stats):
            arff_stats.write(', '.join(f_names_stats))
            arff_stats.write('\n')
            written_header_stats = True

        l = []
        for v in f_values_stats:
            l.append(str(v))
        arff_stats.write(', '.join(l))
        arff_stats.write('\n')


        # Write PL csv
        f_names_pl = []
        f_values_pl = []

        for i, b in enumerate(bin_list):
            f_names_pl.append('packetLengthBin_' + str(i))
            f_values_pl.append(b)

        for i, b in enumerate(bin_list2):
            f_names_pl.append('packetLengthBin2_' + str(i))
            f_values_pl.append(b)

        f_names_pl.append('Class')
        f_values_pl.append(label)

        if (not written_header_pl):
            arff_pl.write(', '.join(f_names_pl))
            arff_pl.write('\n')
            written_header_pl = True

        l = []
        for v in f_values_pl:
            l.append(str(v))
        arff_pl.write(', '.join(l))
        arff_pl.write('\n')

    arff_stats.close()
    arff_pl.close()

    print "UDP Protocols seen: " + str(udp_protocols_seen)


def profile_processing(network_condition_type, profile_type, b, data_folder):
    cfgs = [
        # start_time, end_time, baseline_size
        [0, 30, 250],
    ]
    network_condition = network_condition_type
    profile = profile_type
    
    PrintColored("Analyzing " + network_condition + " Network Condition", "yellow")
    samples_folder = data_folder + "/" + b + "/" + profile + "/" + network_condition

    #For different splits of baseline sizes (currently half of each dataset = 250 samples)
    for cfg in cfgs:
        start_time = cfg[0]
        end_time = cfg[1]
        baseline_size = cfg[2]
        PrintColored("Parsing data for start_time " + str(start_time) + ", end_time " + str(end_time) + ", baseline_size " + str(baseline_size), 'red')

        random.seed(a=1)
        samples_random_list = os.listdir(samples_folder)
        samples_random_list = [e for e in samples_random_list]
        samples_random_list.sort()
        random.shuffle(samples_random_list)

        samples_baselines = []
        number_samples_baselines = int(math.ceil(len(samples_random_list) / float(baseline_size)))

        PrintColored("Generating " + str(number_samples_baselines) + " Baselines for " + b, 'red')
        for i in range(0, number_samples_baselines):
            samples_baselines.append(samples_random_list[i * baseline_size:i * baseline_size + baseline_size])


        ## Combined Feature Extraction
        for i, baseline in enumerate(samples_baselines):
            PrintColored("Generating feature sets for " + b + "_" + str(i), 'green')
            FeatureExtractionCombined(samples_folder, cap_folder_name, baseline, b + "_" + str(i), b, profile, network_condition, start_time, end_time, baseline_size)
            print "\n"



if __name__ == "__main__":

    if(len(sys.argv) < 2):
        print "Error: Please input sample folder location"
        sys.exit(0)

    cap_folder_name = sys.argv[1]
    


    ######################### Configure Accordingly ################################
    data_folder = "/home/vagrant/SharedFolder/ProtozoaCaps/" + cap_folder_name + "/"
    ################################################################################



    baselines = os.listdir(data_folder)
    baselines = [e for e in baselines if ".DS_Store" not in e]

    #For kinds of traffic (Protozoa | Regular versions)
    for b in baselines:
        PrintColored("Analyzing " + b + " Baseline", "yellow")
        profiles = os.listdir(data_folder + "/" + b)
        profiles = [e for e in profiles if ".DS_Store" not in e]
        
        
        for profile in profiles:
            PrintColored("Analyzing " + profile + " Video Profile", "yellow")
            network_conditions = os.listdir(data_folder + "/" + b + "/" + profile)
            network_conditions = [e for e in network_conditions if ".DS_Store" not in e]

            #For each video profile (Chat, LiveCoding, Gaming, Sports)
            Parallel(n_jobs=-1, backend="multiprocessing")(delayed(profile_processing)(network_condition_type=network_condition, profile_type=profile, b=b, data_folder=data_folder) for network_condition in network_conditions)

        
