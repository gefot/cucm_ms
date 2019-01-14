
import sys
# This is needed so as to be run on CLI
sys.path.append('/home/gfot/cucm_ms')

import json
import datetime
import re
from threading import Thread

from modules import module_cucm_funcs, module_db_funcs, module_network_device_funcs


########################################################################################################################
def get_switch_info_mthread(sw_dev):

    try:
        if sw_dev == "noc-clust-sw":
            conn = module_network_device_funcs.device_connect(sw_dev, RT_CREDS)
        else:
            conn = module_network_device_funcs.device_connect(sw_dev, SW_CREDS)

        modules = module_network_device_funcs.get_cisco_cluster_members(conn)

        for module in modules:
            vendor = "cisco"

            print("a")
        conn.disconnect()

    except:
        print("device_connect_multithread -> Can not connect to device {}\n".format(sw_dev))


########################################################################################################################
# Constant Variables
########################################################################################################################

# data = json.load(open('../data/access.json'))                       # Windows
# SWITCH_FILE = '../data/voip_switches.txt'
# MAIL_FILE = '../data/output/report_sanity_security.txt'

data = json.load(open('/home/gfot/cucm_ms/data/access.json'))       # Linux
SWITCH_FILE = '/home/gfot/cucm_ms/data/voip_switches.txt'
REPORT_FILE = '/home/gfot/cucm_ms/data/output/report_sanity_security.txt'

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


################################################################################
start = datetime.datetime.now()

########################################################################################################################
#
########################################################################################################################
try:
    switch_list = []
    threads = []
    for sw_device in switch_list:
        try:
            print("\nConnecting to switch: ", sw_device)
            process = Thread(target=get_switch_info_mthread, args=[sw_device])
            process.start()
            threads.append(process)
        except:
            continue

    for process in threads:
        process.join()


except Exception as ex:
    print(ex)
    exit(0)

# Measure Script Execution
print("\n--->Runtime After Accessing Switches = {} \n\n\n".format(datetime.datetime.now() - start))




# Measure Script Execution
print("\n--->Runtime final = {} \n\n\n".format(datetime.datetime.now()-start))
