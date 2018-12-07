
import json
import datetime
import re
from threading import Thread

from backend.classes import Phone
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
data = json.load(open('../data/access.json'))

UNREG_REPORT_FILE = '../data/output/report_devices_unregistered.txt'

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
            while new_line is not '':
                # print(repr(new_line))
                device = new_line.split('\t\t')
                # print("device=",device)
                temp_dev = Phone(device[0], device[3], device[1], device[4])
                unreg_devices.append(temp_dev)
                new_line = fd.readline().strip('\n')
    fd.close()
except:
    exit(0)

for dev in unreg_devices:
    dev.print_device_full()

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


# Measure Script Execution
print("\n--->Runtime final = {} \n\n\n".format(datetime.datetime.now()-start))
