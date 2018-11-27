import json
import datetime

from modules import module_cucm_funcs


########################################################################################################################
# Constant Variables
########################################################################################################################
data = json.load(open('../data/access.json'))                 # Windows
REPORT_FILE_1 = '../data/output/report_devices.txt'
REPORT_FILE_2 = '../data/output/report_devices_unregistered.txt'

# data = json.load(open('/home/pbx/cucm_ms/data/access.json'))  # Linux
# DEVICE_REPORT_FILE = '/stats/mrtg/scripts/voip_stats/cucm_ms/output/device_report.txt'

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


########################################################################################################################
start = datetime.datetime.now()


########################################################################################################################
# Get a list of all configured devices
########################################################################################################################
try:
    all_devices = module_cucm_funcs.cucm_get_configured_devices(CM_PUB_CREDS)
except Exception as ex:
    print(ex)
    exit(0)

# Measure Script Execution
print("\n--->Runtime After AXLAPI SQL query = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Fill the list of the configured devices with info from RIS database
########################################################################################################################
try:
    module_cucm_funcs.cucm_fill_device_status(CM_PUB_CREDS, all_devices)
    # Sort Phone list by registration timestamp
    all_devices.sort(key=lambda x: x.description, reverse=False)
except Exception as ex:
    print(ex)
    exit(0)

# Measure Script Execution
print("\n--->Runtime After RIS query = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
for dev in all_devices:
    dev.print_device_ris()
all_devices_count = module_cucm_funcs.cucm_count_interering_devices(all_devices)
print("device count = ", all_devices_count)


########################################################################################################################
#  Construct report files
########################################################################################################################
try:
    # All devices report file
    fd_1 = open(REPORT_FILE_1, "w")
    for dev in all_devices:
        fd_1.write("{}, {}, {}, {}, {}, {}, {}\n".format(dev.name, dev.description, dev.device_type, dev.extension, \
                                             dev.alerting_name, dev.status, dev.timestamp))
    fd_1.close()

    # Unregistered devices report file with general info
    fd_2 = open(REPORT_FILE_2, "w")
    unreg_devices = 0
    ignored_devices = 0
    for dev in all_devices:
        if dev.description.startswith("_"):
            ignored_devices += 1
        if (not dev.description.startswith("_")) and dev.status == "unregistered":
            unreg_devices += 1
    fd_2.write("Device Summary (Registered / Total: {} / {}\n\n".format(all_devices_count[0]-unreg_devices, all_devices_count[0]))
    fd_2.write("Total IP Phones = {}\n".format(all_devices_count[1]))
    fd_2.write("Total ATA Ports = {} (Devices = {})\n".format(all_devices_count[3], all_devices_count[2]))
    fd_2.write("Total Analog Ports = {}\n".format(all_devices_count[4]))
    fd_2.write("Total Jabber Devices = {}\n".format(all_devices_count[5]))

    all_devices.sort(key=lambda x: x.timestamp, reverse=True)
    fd_2.write("\n\nUnregistered devices ({}):\n".format(unreg_devices))
    for dev in all_devices:
        if (not dev.description.startswith("_")) and dev.status == "unregistered":
            fd_2.write("{}, {}, {}, {}, {}, {}, {}\n".format(dev.name, dev.description, dev.device_type, dev.extension, \
                                                             dev.alerting_name, dev.status, dev.timestamp))
    fd_2.write("\n\nIgnored devices ({}):\n".format(ignored_devices))
    for dev in all_devices:
        if dev.description.startswith("_"):
            fd_2.write("{}, {}, {}, {}, {}, {}, {}\n".format(dev.name, dev.description, dev.device_type, dev.extension, \
                                                             dev.alerting_name, dev.status, dev.timestamp))
    fd_2.close()
except Exception as ex:
    print(ex)
    exit(0)


# Measure Script Execution
print("\n--->Runtime at end = {} \n\n\n".format(datetime.datetime.now() - start))
