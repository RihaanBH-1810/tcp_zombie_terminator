import psutil
from scapy.all import sr, IP, TCP, IPv6
from multiprocessing import Process, Queue
import subprocess

not_interested = ["LISTEN", "NONE", "SYN_SENT"]
connections_list = []
working = []
zombie_list = []
result_queue = Queue()
zombie_queue = Queue()
processes = []

for con in psutil.net_connections():
    if con.status not in not_interested:
        connections_list.append(con)

def probe_the_port(ip, port, pid, l_ip, l_port,  ip6=False, result_queue=None, zombie_queue=None):
    zombie_count = 0
    working_count = 0
    for i in range(7):
        if ip6:
            packet = IPv6(dst=ip) / TCP(dport=port, flags="S",)
            ans, unanswered = sr(packet, timeout=1,verbose = False )
        else:
            packet = IP(dst=ip) / TCP(dport=port, flags="S", )
            ans, unanswered = sr(packet, timeout=1, verbose = False)
        if ans:
            working_count += 1
        else:
            zombie_count += 1  
    #print(f"ip {ip} port {port} pid {pid} l_ip = {l_ip} l_port = {l_port} zombie count {zombie_count} working count {working_count}")
    if zombie_count == 7:
        zombie_queue.put((ip, port, l_ip, l_port, pid, ))  
    else:
        result_queue.put((ip, ans[0][1].sprintf('%TCP.flags%')))

if connections_list:
    for con in connections_list:
        print(con.raddr)
    for connection in connections_list:
        if str(connection.family) == "AddressFamily.AF_INET6":
            process = Process(target=probe_the_port, args=(connection.raddr[0], connection.raddr[1],connection.pid, connection.laddr[0], connection.laddr[1] , True, result_queue, zombie_queue))
            processes.append(process)
            process.start()
        elif str(connection.family) == "AddressFamily.AF_INET":
            process = Process(target=probe_the_port, args=(connection.raddr[0], connection.raddr[1],connection.pid, connection.laddr[0], connection.laddr[1] , False, result_queue, zombie_queue))
            processes.append(process)
            process.start()

for process in processes:
    process.join()

while not result_queue.empty():
    result = result_queue.get()
    working.append(result)

while not zombie_queue.empty():
    zombie_result = zombie_queue.get()
    zombie_list.append(zombie_result)

print("Working:")
for work in working:
    print(work)

print("Zombie:")
for zombie in zombie_list:
    print(f"Killing connection on local port {zombie[4]}")
    pid = zombie[4]
    print(zombie)
    print(pid)
    if pid != None:
       s_pid = str(pid)
       subprocess.call(["kill", "-9", s_pid])
    
    if pid == None:
        print(f"found without pid on port {zombie[3]}")
