#!/bin/bash

# Function: run the ring topology for various
# value of N

# Exit on any failure
set -e

# Check for uninitialized variables
set -o nounset

ctrlc() {
	killall -9 python
	mn -c
	exit
}

trap ctrlc SIGINT

start=`date`
exptid=`date +%b%d-%H:%M`

bw=10
DEALYLIST={"0ms 1ms 3ms"}
LOSSLIST= {"0 1"}
# Note: you need to make sure you report the results
# for the correct port!
# In this example, we are assuming that each
# client is connected to port 2 on its switch.
for delay in $DEALYLIST ;do
    for loss in $LOSSLIST ;do
        for n in  4 5 6; do
            rootdir=Ring-$exptid-Single-Delay$delay-Loss$loss
            dir=$rootdir/n$n
            python ringsingle.py --bw $bw \
                --dir $dir \
                --delay $delay\
                --loss $loss\
                -t 30 \
                -n $n
            python util/plot_rate.py --rx \
                --maxy $bw \
                --xlabel 'Time (s)' \
                --ylabel 'Rate (Mbps)' \
                -i 's.*-eth1' \
                -f $dir/bwm.txt \
                -o $dir/rate.png
            python util/plot_tcpprobe.py \
                -f $dir/tcp_probe.txt \
                -o $dir/cwnd.png
        done
    done
done
echo "Started at" $start
echo "Ended at" `date`
echo "Output saved to $rootdir"
