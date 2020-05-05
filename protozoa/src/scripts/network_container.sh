#!/bin/bash

#Generate Protozoa network namespace
echo 'Deleting namespace'
ip netns del PROTOZOA_ENV
ip link delete veth0
echo 'Flushing iptables'
iptables -F

mkdir -p /etc/netns/PROTOZOA_ENV
echo 'nameserver 8.8.8.8' > /etc/netns/PROTOZOA_ENV/resolv.conf

ip netns add PROTOZOA_ENV
ip link add veth0 type veth peer name veth1
ip link set veth1 netns PROTOZOA_ENV



#Set up iptables rules for packet queueing

if [ $1 == "client" ]; then
    ifconfig veth0 10.10.10.11 netmask 255.255.255.0 up
    ip netns exec PROTOZOA_ENV ifconfig veth1 10.10.10.10 netmask 255.255.255.0 up
    ip netns exec PROTOZOA_ENV ip route add default via 10.10.10.11
    ip netns exec PROTOZOA_ENV route add default gw 10.10.10.11

    # Enqueue packets generated inside PROTOZOA_ENV to queue no. 0 - feeding ClientThread on client side
    iptables -I FORWARD -s 10.10.10.10 -j NFQUEUE --queue-num 0

    #Transparently forward traffic from veth1(netns) to ens33 (vmware) / enp0s17 (vbox) /enp0s8 (vagrant)
    echo 1 > /proc/sys/net/ipv4/ip_forward
    iptables -t nat -F
    iptables -t nat -A POSTROUTING -s 10.10.10.10/24 -o enp0s8 -j MASQUERADE
    iptables -A FORWARD -i enp0s8 -o veth0 -j ACCEPT
    iptables -A FORWARD -o enp0s8 -i veth0 -j ACCEPT

else
    ifconfig veth0 20.20.20.21 netmask 255.255.255.0 up
    ip netns exec PROTOZOA_ENV ifconfig veth1 20.20.20.20 netmask 255.255.255.0 up
    ip netns exec PROTOZOA_ENV ip route add default via 20.20.20.21
    ip netns exec PROTOZOA_ENV route add default gw 20.20.20.21

    # Enqueue packets towards server-side PROTOZOA_ENV to queue no. 1 - feeding ClientThread on server side
    iptables -I FORWARD -d 10.10.10.10 -j NFQUEUE --queue-num 1

    #Transparently forward traffic from veth1(netns) to ens33 (vmware) / enp0s17 (vbox) /enp0s8 (vagrant)
    echo 1 > /proc/sys/net/ipv4/ip_forward
    iptables -t nat -F
    iptables -t nat -A POSTROUTING -s 20.20.20.20/24 -o enp0s8 -j MASQUERADE
    iptables -A FORWARD -i enp0s8 -o veth0 -j ACCEPT
    iptables -A FORWARD -o enp0s8 -i veth0 -j ACCEPT
    ip netns exec PROTOZOA_ENV ssh -i ~/.ssh/id_rsa -N -D 0.0.0.0:1080 vagrant@20.20.20.21 &
fi



