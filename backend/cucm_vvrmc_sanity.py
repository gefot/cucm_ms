
import json
import datetime
import re
from threading import Thread

from backend.classes import Phone
from modules import module_cucm_funcs, module_db_funcs, module_network_device_funcs


########################################################################################################################
def device_connect_multithread(sw_dev):
    try:

        print("\nConnecting to switch: ", sw_dev)
        vendor = "dell"
        module = "0"

        try:
            conn = module_network_device_funcs.device_connect(sw_dev, SW_CREDS)
        except:
            conn = module_network_device_funcs.device_connect(sw_dev, SW_CREDS2)

        devices = module_network_device_funcs.discover_phones(conn, vendor, module)
        conn.disconnect()

        for dev in devices:
            dev.insert(2, sw_dev)
        all_devices.extend(devices)
    except:
        print("device_connect_multithread -> Can not connect to switchport {} for {}\n".format(sw_dev.switchport, dev.name))


########################################################################################################################


########################################################################################################################
# Constant Variables
########################################################################################################################
data = json.load(open('../data/access.json'))

SWITCH_FILE = '../data/voip_switches.txt'                               # Windows
# UNREG_REPORT_FILE = '../data/output/report_devices_unregistered.txt'

# data = json.load(open('/home/pbx/cucm_ms/data/access.json'))  # Linux
# DEVICE_REPORT_FILE = '/stats/mrtg/scripts/voip_stats/cucm_ms/output/device_report.txt'

CM_PUB_CREDS = {'cm_server_hostname': str(data["cucm"]["pub_hostname"]), \
                'cm_server_ip_address': str(data["cucm"]["pub_ip_address"]), \
                'cm_server_port': str(data["cucm"]["cm_port"]), \
                'soap_user': str(data["cucm"]["soap_user"]), \
                'soap_pass': str(data["cucm"]["soap_pass"])
                }

SW_CREDS = {'my_connection_type': str(data["switch"]["device_connection_type"]), \
            'sw_username': str(data["switch"]["sw_username"]), \
            'sw_password': str(data["switch"]["sw_password"]), \
            'sw_enable': str(data["switch"]["sw_enable"]), \
            'sw_port': str(data["switch"]["sw_port"]), \
            'sw_verbose': str(data["switch"]["sw_verbose"])
            }

SW_CREDS2 = {'my_connection_type': str(data["switch2"]["device_connection_type"]), \
            'sw_username': str(data["switch2"]["sw_username"]), \
            'sw_password': str(data["switch2"]["sw_password"]), \
            'sw_enable': str(data["switch2"]["sw_enable"]), \
            'sw_port': str(data["switch2"]["sw_port"]), \
            'sw_verbose': str(data["switch2"]["sw_verbose"])
            }


########################################################################################################################
start = datetime.datetime.now()

all_devices = []
try:
    fd = open(SWITCH_FILE, "r")
    switch_list = fd.read().splitlines()
    fd.close()
    print(switch_list)
    # switch_list = ['100.100.100.110', '100.100.100.125']

    threads = []
    for sw_device in switch_list:
        try:
            process = Thread(target=device_connect_multithread, args=[sw_device])
            process.start()
            threads.append(process)
        except:
            continue

    for process in threads:
        process.join()

except Exception as ex:
    print(ex)


for dev in all_devices:
    print(dev)



# ########################################################################################################################
# # Get unregistered devices from device report
# # Construct a Phone list with name, description, extension, calling_name
# ########################################################################################################################
# unreg_devices = []
# try:
#     fd = open(UNREG_REPORT_FILE, "r")
#     for line in fd:
#         if "Unregistered devices" in line:
#             new_line = fd.readline().strip('\n')
#             while new_line != '':
#                 # print(repr(new_line))
#                 device = new_line.split('\t\t')
#                 # print("device=",device)
#                 temp_dev = Phone(device[0], device[3], device[1], device[4])
#                 unreg_devices.append(temp_dev)
#                 new_line = fd.readline().strip('\n')
#     fd.close()
# except:
#     exit(0)
#
# for dev in unreg_devices:
#     dev.print_device_full()
#
# ########################################################################################################################
# # Troubleshooting Section
# ########################################################################################################################
# threads = []
# try:
#     for dev in unreg_devices:
#         try:
#             process = Thread(target=device_connect_multithread, args=[dev])
#             process.start()
#             threads.append(process)
#
#         except:
#             continue
# except Exception as ex:
#     print(ex)
#     exit(0)
#
# for process in threads:
#     process.join()
#
# print("\n\n\n\n\n")
# for dev in unreg_devices:
#     dev.print_device_full_net()
#
#
# # Measure Script Execution
# print("\n--->Runtime After Tshoot Section = {} \n\n\n".format(datetime.datetime.now() - start))


# Measure Script Execution
print("\n--->Runtime final = {} \n\n\n".format(datetime.datetime.now()-start))
