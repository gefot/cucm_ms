
import json
import datetime
import re

from modules import module_cucm_funcs, module_db_funcs, module_network_device_funcs


########################################################################################################################
# Constant Variables
########################################################################################################################
data = json.load(open('../data/access.json'))
SWITCH_FILE = '../data/voip_switches.txt'                               # Windows
MAIL_FILE = '../data/output/cucm_sanity_security.txt'
# SWITCH_FILE = '/stats/mrtg/scripts/voip_stats/cucm_ms/voip_switches.txt'      # Linux
# MAIL_FILE = '/stats/mrtg/scripts/voip_stats/cucm_ms/output/cucm_sanity_security.txt'


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


################################################################################
start = datetime.datetime.now()


########################################################################################################################
# Get a list of and count all configured devices
########################################################################################################################
try:
    all_devices = module_cucm_funcs.cucm_get_configured_devices(CM_PUB_CREDS)
    all_devices_count = module_cucm_funcs.cucm_count_interering_devices(all_devices)
except Exception as ex:
    print(ex)
    exit(0)

# for device in all_devices:
#     print(device)
# print("device count = ", all_devices_count)

# Measure Script Execution
print("\n--->Runtime After AXLAPI SQL query = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Fills in all_devices with database info
# all_devices = [mac_address, description, extension, alerting name, device type, username, unit_id, switchport, isPoE]
########################################################################################################################
try:
    conn = module_db_funcs.db_connect(DB_CREDS)
    cursor = conn.cursor()
    for device in all_devices:
        my_username, my_unit_id, my_switchport, my_isPoE = module_db_funcs.fetch_from_db_per_dn(cursor, device[2])
        device.extend((my_username, my_unit_id, my_switchport, my_isPoE))
    conn.close()
except Exception as ex:
    print(ex)
    conn.close()
    exit(0)

for device in all_devices:
    print(device)

# Measure Script Execution
print("\n--->Runtime After DB Queries = {} \n\n\n".format(datetime.datetime.now()-start))


########################################################################################################################
# Connect to voip switches and gathers info
# switch_devices_table: [MAC address, switchport]
# voice_vlan_mac_table: [vlan, MAC address, switchport]
########################################################################################################################
try:
    fd = open(SWITCH_FILE, "r")
    switch_list = fd.read().splitlines()
    fd.close()
    print(switch_list)
    # switch_list = ["bld67cbsmnt-sw", "bld34fl02-sw", "bld61fl00-sw"]
    switch_list = ["bld61fl00-sw"]

    switch_devices_table = []
    voice_vlan_mac_table = []

    for sw_device in switch_list:
        print("\nConnecting to switch: ", sw_device)

        conn = module_network_device_funcs.device_connect(sw_device, SW_CREDS)
        modules = module_network_device_funcs.get_cluster_members(conn)

        for module in modules:

            # Run 'show cdp neighbors' and get device and switchport
            result = module_network_device_funcs.device_show_cmd(conn, "show cdp neighbors", module)
            lines = result.split('\n')
            for l in lines:
                if re.match("^SEP", l) or re.match("^ATA", l):
                    mac_address = re.search("(\w\w\w[\w\d]*)", l).group(1).upper()
                    port = re.search(r'.*\/(\d+)\s', l).group(1)
                    my_dev = [mac_address, sw_device + "-m" + module + "-p" + str(int(port))]
                    switch_devices_table.append(my_dev)

            # Get switch full mac address table and keeps only voice MACs
            device_model = module_network_device_funcs.get_device_model(conn, module)
            full_mac_table = module_network_device_funcs.get_switch_mac_table(conn, device_model, module)
            for mac_entry in full_mac_table:
                if len(mac_entry[0]) == 3 and (mac_entry[0] == "111" or mac_entry[0].startswith('7')):
                    my_mac = (mac_entry[1].upper()).replace('.', '')
                    my_dev = [mac_entry[0], my_mac, sw_device + "-m" + module + "-p" + str(int(mac_entry[2]))]
                    voice_vlan_mac_table.append(my_dev)

        conn.disconnect()

    for device in switch_devices_table:
        print(device)
    for mac in voice_vlan_mac_table:
        print(mac)
except Exception as ex:
    print(ex)

# Measure Script Execution
print("\n--->Runtime After Accessing Switches = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Sanity and Security Check
# all_devices = [mac_address, description, extension, alerting name, device type, username, unit_id, switchport, isPoE]
# switch_devices_table: [MAC address, switchport]
# voice_vlan_mac_table: [vlan, MAC address, switchport]
########################################################################################################################
# Sanity Check
excluded_extensions = ['']
# excluded_extensions = ['99999']   # Exclude these extensions from the check
try:
    sanity_body = ""
    for my_device1 in all_devices:
        for my_device2 in switch_devices_table:
            try:
                if my_device1[0] == my_device2[0] and my_device1[2] not in excluded_extensions:      # MAC match check
                    if my_device1[7] == my_device2[1]:  # switch port check
                        pass
                    else:
                        sanity_text = "Mismatch: Extension %s (Device %s) found at switchport %s but is actually declared at %s\n" \
                                      % (my_device1[2], my_device1[0], my_device2[1], my_device1[7])
                        sanity_body += sanity_text
                else:
                    continue
            except Exception as ex:
                print(ex)
                sanity_text = "Could not find info for " + my_device2[0] + "\n"
                sanity_body += sanity_text
                pass
except Exception as ex:
    print(ex)
    exit(0)

# Security Check
excluded_macs = ['']
# Excluded MACs: cvoice-rc-gw, 5x RC IP Phones registered at the old CUCM
# excluded_macs = ['C89C1DA33D1E', 'C89C1D492B50', '001D70616E00', '503DE57D415E', '503DE5E93C10', '503DE5E947B1']

security_body = ""
for mac in voice_vlan_mac_table:
    found = False
    for device in all_devices:
        if mac[1] in device[0] or mac[1] in excluded_macs:
            found = True

    if found:
        pass
    else:
        security_body += "Ilegal MAC address %s at switchport %s in vlan %s\n" % (mac[1], mac[2], mac[0])


# Measure Script Execution
print("\n--->Runtime After Processing = {} \n\n\n".format(datetime.datetime.now()-start))


################################################################################
# Write file and send e-mail
################################################################################
mail_body = """
----------------------------------------------------------------------------------------------------------------------------------------------------------
Sanity check:

%s

----------------------------------------------------------------------------------------------------------------------------------------------------------
Security check:

%s

----------------------------------------------------------------------------------------------------------------------------------------------------------
""" % (sanity_body, security_body)

print(mail_body)

if sanity_body or security_body:
    print("\n\n", mail_body)
    target = open(MAIL_FILE, "w")
    target.write(mail_body)
    target.close()

# if sanity_body or security_body:
#     # os_command = "/usr/bin/mail -s \"CUCM Sanity and Security Check\" gfot@it.auth.gr < " + mail_file
#     os_command = "/usr/bin/mail -s \"CUCM Sanity and Security Check\" anemostaff@it.auth.gr < " + mail_file
#     os.system(os_command)


# Measure Script Execution
print("\n--->Runtime final = {} \n\n\n".format(datetime.datetime.now()-start))
