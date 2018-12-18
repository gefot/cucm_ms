
import sys
# This is needed so as to be run on CLI
sys.path.append('/home/gfot/cucm_ms')

import json
import datetime
import re
from threading import Thread

from backend import classes
from modules import module_cucm_funcs, module_db_funcs, module_network_device_funcs


########################################################################################################################
def tshoot_device_mthread(dev):
    try:
        if dev.switchport != "unknown":
            m = re.match("([\w\d\S]+-sw)-m(\d)-p(\d+)", dev.switchport)
            sw_device = m.group(1)
            module = m.group(2)
            port = m.group(3)

            if sw_device == "noc-clust-sw":
                conn = module_network_device_funcs.device_connect(sw_device, RT_CREDS)
            else:
                conn = module_network_device_funcs.device_connect(sw_device, SW_CREDS)

            vendor = "cisco"

            port_status = module_network_device_funcs.get_port_status(conn, vendor, module, port)
            port_power_status = module_network_device_funcs.get_port_power_status(conn, vendor, module, port)
            port_cabling_status = module_network_device_funcs.get_port_cabling(conn, vendor, module, port)
            port_macs = module_network_device_funcs.get_port_macs(conn, vendor, module, port)

            dev.switchport_status = port_status
            dev.switchport_power_status = port_power_status
            dev.switchport_cabling = port_cabling_status
            dev.switchport_macs = port_macs
    except:
        print("device_connect_multithread -> Can not connect to switchport {} for {}\n".format(dev.switchport, dev.name))

########################################################################################################################


########################################################################################################################
# Constant Variables
########################################################################################################################

data = json.load(open('../data/access.json'))                 # Windows
UNREG_REPORT_FILE = '../data/output/report_devices_unregistered.txt'
TSHOOT_REPORT_FILE = '../data/output/report_tshoot_unregistered.txt'

# data = json.load(open('/home/gfot/cucm_ms/data/access.json'))  # Linux
# UNREG_REPORT_FILE = '/home/gfot/cucm_ms/data/output/report_devices_unregistered.txt'
# TSHOOT_REPORT_FILE = '/home/gfot/cucm_ms/data/output/report_tshoot_unregistered.txt'

CM_PUB_CREDS = {'cm_server_hostname': str(data["cucm"]["pub_hostname"]), \
                'cm_server_ip_address': str(data["cucm"]["pub_ip_address"]), \
                'cm_server_port': str(data["cucm"]["cm_port"]), \
                'soap_user': str(data["cucm"]["soap_user"]), \
                'soap_pass': str(data["cucm"]["soap_pass"])
                }

DB_CREDS = {'db_host': str(data["db1"]["db_host"]), \
            'db_username': str(data["db1"]["db_username"]), \
            'db_password': str(data["db1"]["db_password"]), \
            'db_name': str(data["db1"]["db_name"])
            }

SW_CREDS = {'my_connection_type': str(data["switch"]["device_connection_type"]), \
            'sw_username': str(data["switch"]["sw_username"]), \
            'sw_password': str(data["switch"]["sw_password"]), \
            'sw_enable': str(data["switch"]["sw_enable"]), \
            'sw_port': str(data["switch"]["sw_port"]), \
            'sw_verbose': str(data["switch"]["sw_verbose"])
            }

RT_CREDS = {'my_connection_type': str(data["router"]["device_connection_type"]), \
            'sw_username': str(data["router"]["sw_username"]), \
            'sw_password': str(data["router"]["sw_password"]), \
            'sw_enable': str(data["router"]["sw_enable"]), \
            'sw_port': str(data["router"]["sw_port"]), \
            'sw_verbose': str(data["router"]["sw_verbose"])
            }


########################################################################################################################
start = datetime.datetime.now()

########################################################################################################################
# Get unregistered devices from device report
# Construct a Phone list with name, description, extension, calling_name
########################################################################################################################
unreg_devices = []
try:
    fd = open(UNREG_REPORT_FILE, "r")
    for line in fd:
        if "Unregistered devices" in line:
            new_line = fd.readline().strip('\n')
            while new_line != '':
                device = new_line.split('\t\t')
                temp_dev = classes.Phone(device[0], device[3], device[1], device[4])
                unreg_devices.append(temp_dev)
                new_line = fd.readline().strip('\n')
    fd.close()

except Exception as ex:
    print(ex)
    exit(0)

########################################################################################################################
# Replace 3-digit internal extensions with the corresponding translation patterns
########################################################################################################################
try:
    xlation_patterns = module_cucm_funcs.cucm_get_translation_patterns(CM_PUB_CREDS)
    # print(xlation_patterns)
    for dev in unreg_devices:
        try:
            if len(dev.extension) == 3:
                dev.extension = xlation_patterns[dev.extension]
        except:
            continue
except Exception as ex:
    print(ex)
    exit(0)


########################################################################################################################
# Fill in all_devices with database info
########################################################################################################################
try:
    conn = module_db_funcs.db_connect(DB_CREDS)
    cursor = conn.cursor()
    for dev in unreg_devices:
        my_username, my_unit_id, my_switchport, my_isPoE, my_access_outlet_id, my_outlet_status, my_outlet_usedFor = module_db_funcs.auth_fetch_from_db_per_dn(cursor, dev.extension)
        dev.responsible_person = my_username
        dev.switchport = my_switchport
    conn.close()
except Exception as ex:
    print(ex)
    conn.disconnect()
    exit(0)


# Measure Script Execution
print("\n--->Runtime After database SQL query = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Troubleshooting Section
########################################################################################################################
threads = []
try:
    for dev in unreg_devices:
        try:
            process = Thread(target=tshoot_device_mthread, args=[dev])
            process.start()
            threads.append(process)

        except:
            continue
except Exception as ex:
    print(ex)
    exit(0)

for process in threads:
    process.join()

print("\n\n\n\n\n")
for dev in unreg_devices:
    dev.print_device_full_net()


# Measure Script Execution
print("\n--->Runtime After Tshoot Section = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Create Report File
########################################################################################################################
try:
    fd1 = open(UNREG_REPORT_FILE, "r")
    fd2 = open(TSHOOT_REPORT_FILE, "w")

    for line in fd1:
        fd2.write(line)
        if "Unregistered devices" in line:
            new_line = fd1.readline().strip('\n')
            while new_line != '':
                myline = new_line+'\n'
                fd2.write(myline)
                new_line = fd1.readline().strip('\n')
            fd2.write('\n\n\n')
            break
    fd1.close()

    for dev in unreg_devices:
        tshoot_str = """
-------------------------------------------------------------
%s (%s) - %s
Username: %s
Switchport: %s
Port Status: %s
Port Power: %s
Found MAC: %s
TDR: %s
""" % (dev.name, dev.extension, dev.description, dev.responsible_person, dev.switchport, dev.switchport_status, \
             dev.switchport_power_status, dev.switchport_found_mac, dev.switchport_cabling)
        print(tshoot_str)
        fd2.write(tshoot_str)

    fd2.close()

except Exception as ex:
    print(ex)
    exit(0)




# Measure Script Execution
print("\n--->Runtime final = {} \n\n\n".format(datetime.datetime.now()-start))
