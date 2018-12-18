
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
def device_connect_multithread(dev):
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
# data = json.load(open('../data/access.json'))                 # Windows
# UNREG_REPORT_FILE = '../data/output/report_devices_unregistered.txt'

data = json.load(open('/home/gfot/cucm_ms/data/access.json'))  # Linux
UNREG_REPORT_FILE = '/home/gfot/cucm_ms/data/output/report_devices_unregistered.txt'

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
                # print(repr(new_line))
                device = new_line.split('\t\t')
                # print("device=",device)
                temp_dev = classes.Phone(device[0], device[3], device[1], device[4])
                unreg_devices.append(temp_dev)
                new_line = fd.readline().strip('\n')
    fd.close()
except:
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
            process = Thread(target=device_connect_multithread, args=[dev])
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
# Create Report
########################################################################################################################
# if len(unreg_devices) != len(username):
# 	"Error: Unequal Lists\n"
# 	exit(0)
#
# ## List Unregistered Devices
# unreg_devices_str =""
# for device in unreg_devices:
# 	unreg_devices_str = unreg_devices_str + device[0] + "\t\t" + device[2] + "\t" + device[3] + "\t" + device[1] + "\n"
#
# ## Calculate unregistered devices
# unreg_device_count = [0]*5
# reg_devices_count = map(operator.sub, all_devices_count, unreg_devices_count)
# print all_devices_count
# print unreg_devices_count
# print reg_devices_count
#
# ## Prepare standard mail body
# mail_body = """
# Device Summary (Total / Reg) : %d / %d
#
# Total IP Phones = %d
# Total ATA Ports = %d (Devices = %d)
# Total MGCP Ports = %d
#
# Registered IP Phones = %d
# Registered ATA Ports = %d (Devices = %d)
# Registered MGCP Ports = %d
#
# Unregistered Devices (%d):\n%s""" % (all_devices_count[0], reg_devices_count[0], all_devices_count[1], all_devices_count[2], all_devices_count[3], all_devices_count[4], reg_devices_count[1], reg_devices_count[2], reg_devices_count[3], reg_devices_count[4], unreg_devices_count[0], unreg_devices_str)
# print mail_body
#
#
# ## Prepare troubleshooting message, if tshoot is requested at CLI command
# tshoot_str = "\n\n"
# if len(sys.argv) == 3 and sys.argv[2] == "tshoot":
# 	# Construct tshoot string
# 	switchport_str = []
# 	for i,device in enumerate(unreg_devices):
# 		if switchport[i] != "unknown":
# 			switchport_str.append(switchport[i][0]+"-m"+str(int(switchport[i][1]))+"-p"+str(int(switchport[i][2])))
# 		else:
# 			switchport_str.append("unknown")
#
# 		tshoot_str = tshoot_str + """
# -------------------------------------------------------------
# %s (%s) - %s
# Username: %s
# Switchport: %s (%s)
# Port Status: %s
# Port Power: %s
# Found MAC: %s
# TDR: %s
# """ % (device[0], device[2], device[1], username[i], switchport_str[i], device_model[i], port_status[i], port_power[i], found_mac[i], port_tdr[i])
#
# 	print tshoot_str
# mail_body += tshoot_str
#
#
#
# #############################
# ## Write file and send e-mail
# #############################
# #print "\n---\nmail_body:\n",mail_body
# target = open(mail_file, "w")
# target.write(mail_body)
# target.close()
# os_command = "/usr/bin/mail -s \"CUCM Device Report\" anemostaff@it.auth.gr < "+mail_file
# #os_command = "/usr/bin/mail -s \"CUCM Device Report\" gfot@it.auth.gr < "+mail_file
# os.system(os_command)
#
# ## Measure Script Execution
# print "\n\n--->Runtime final = ",datetime.datetime.now()-start
#
#

# Measure Script Execution
print("\n--->Runtime final = {} \n\n\n".format(datetime.datetime.now()-start))
