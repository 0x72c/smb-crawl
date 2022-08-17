#!/usr/bin/python3
# This python script reads a list of cidr addresses and converts them to individual IPs, then checks for open shares
import os
import sys
from sys import platform
import threading
import multiprocessing
import ipaddress
from subprocess import run, PIPE
from time import sleep

# Function to actually attempt the connection
def connect(ips,outfile,threadNum):
    print("Started thread " + str(threadNum))
    # Run through each IP and try to connect
    for ip in ips:
        if running == False:
            print("Exiting thread " + str(threadNum))
            break
        else:
            # Create command to run (-L = list, -U is Guest user and -N no password, timout is 5 seconds)
            comm = ["smbclient","-L",str(ip),"-U","Guest","-N","-t",sys.argv[3]]
            # Fetch results from the command
            try:
                result = run(comm,stdout=PIPE, stderr=PIPE, universal_newlines=True)
                print("Checking " + str(ip)) # Give the user a friendly status update
            # Handle failures and notify user
            except Exception: 
                print("Failed to check " + str(ip) + "\n")
                continue
            # Write out if successful
            if result.returncode == 0:
                of = open(outfile,"a")
                of.write(str(ip) + " " + str(result.stdout) + "\n")
                of.close()
                print("Found something... " + str(result.stdout))
    
    print("Finished thread " + str(threadNum))

# Main function, will split off threads when needed for odd and even IPs
def main():
    global running
    # Handle bad argument input
    if len(sys.argv) != 4:
        print('''smb-crawl help: 
        Dependencies: smbclient
        Usage: smb-crawl <target file path or single target> <output directory path> <timeout seconds>
        Example: smb-crawl 192.168.1.1/32 /output/directory 3
        Example: smb-crawl /path/to/target/file.txt /output/directory 5
        Format: Do not put a file name at the end of the output-path since it will have smb-crawl-out.txt appended.
                Targets can be single IPs or CIDR notation but each line in the target file must have only one target and the file must be plain text.
        ''')
        sys.exit(0)
    elif platform != "linux":
        print("I only run on Linux")
        sys.exit()
    # Make sure there are adequate CPUs
    elif multiprocessing.cpu_count() < 2:
        print("Not enough threads, exiting.")
        sys.exit()

    # Open the target file passed, read each target into a list
    try:
        # Check if the target is a file
        if os.path.exists(sys.argv[1]):
            f = open(sys.argv[1])
            targets = f.readlines()
            f.close()
            targetType = "multi"
        # If not, try to read it as a single ip or network
        elif ipaddress.ip_network(sys.argv[1]):
            targets = ipaddress.ip_network(sys.argv[1])
            targetType = "single"
    except Exception as e:
        print("Error: " + str(e))
        sys.exit()

    # Open an output file to write to
    try:
        outdir = sys.argv[2] 
        if outdir.endswith("/") == False:
            outdir = outdir + "/"
        outfile = outdir + "smb-crawl-out.txt"
        print("outfile is " + outfile)
        #of = open(outfile,"a")
    except Exception as e:
        print("Error: " + str(e))
    # Lists to hold targets for threading
    odds = []
    evens = []
    try:
        # Run through the list of addresses
        for target in targets:
            # Clean up cidr
            if targetType == "multi" and target.endswith("\n"):
                target = target.strip("\n")
            # Read as cidr, works even with single IPs by reading as a /32 network
            ips = ipaddress.ip_network(target)
            # Split up ips into odd and evens for two threads
            for ip in ips:
                # Break off last octet and check if odd or even
                last_octet = str(ip).split(".")[3]
                if int(last_octet)%2 == 0:
                    evens.append(ip)
                else:
                    odds.append(ip)
        # Split off threads
        t1 = threading.Thread(target=connect, args=(odds,outfile,1))
        t2 = threading.Thread(target=connect, args=(evens,outfile,2))
        running = True
        t1.start()
        t2.start()
        t1.join()
        t2.join()
               
    # Exit on keyboard interrupt ctrl + c
    except KeyboardInterrupt:
        running = False
        # Give time for both threads to stop
        sleep(2)
        print("Adios!")
        sys.exit()

if __name__ == "__main__":
    print("Welcome to smb-crawl, an 'easy' to use bulk SMB share scanner that uses the built in *nix OS smbclient functionality to find shares on networks.\n")
    main()

