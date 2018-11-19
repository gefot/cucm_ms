import json
import datetime
import re

from modules import module_cucm_funcs, module_db_funcs, module_network_device_funcs


#####################################################################
# Constant Variables
#####################################################################
data = json.load(open('../data/access.json'))

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

SWITCH_FILE = '../data/voip_switches.txt'                               # Windows
MAIL_FILE = '../data/output/cucm_sanity_security.txt'
# SWITCH_FILE = '/stats/mrtg/scripts/voip_stats/cucm_ms/voip_switches.txt'      # Linux
# MAIL_FILE = '/stats/mrtg/scripts/voip_stats/cucm_ms/output/cucm_sanity_security.txt'

################################################################################
start = datetime.datetime.now()


################################################################################
# Get a list of and count all configured devices
# all_devices = [mac_address, description, extension, device type]
# all_devices_count = [Total, IP Phones, ATA ports, ATA devices, MGCP Analog]
################################################################################
try:
    all_devices = module_cucm_funcs.cucm_get_configured_devices(CM_PUB_CREDS)
    for device in all_devices:
        print(device)
    all_devices_count = module_cucm_funcs.cucm_count_interering_devices(all_devices)
    print("device count = ", all_devices_count)

    # Measure Script Execution
    print("\n--->Runtime After AXLAPI SQL query = {} \n\n\n".format(datetime.datetime.now() - start))

except Exception as ex:
    print(ex)
    exit(0)


# all_devices = [['SEP188B4519FDAA', 'FARM - g10', '91778', 'Cisco 3905'], ['SEP1CE85DC9CEC5', 'FARM - a04', '91701', 'Cisco 3905'], ['SEP3C5EC30C5D9A', 'FARM - a05', '91705', 'Cisco 3905'], ['SEP3C5EC30C5B39', 'FARM - b03', '91738', 'Cisco 3905'], ['SEP3C5EC30C5CE7', 'FARM - b04', '99999', 'Cisco 3905'], ['SEP3C5EC30C60D3', 'FARM - b05', '91741', 'Cisco 3905'], ['SEP1CE85DC950A1', 'FARM - c02', '91726', 'Cisco 3905'], ['SEP1CE85DC9FBFA', 'FARM - d02', '91714', 'Cisco 3905'], ['SEP3C5EC30C67E1', 'FARM - d03', '91722', 'Cisco 3905'], ['SEP1CE85DC9D3C1', 'FARM - d04', '91734', 'Cisco 3905'], ['SEP1CE85DC9FC0B', 'FARM - d05', '91791', 'Cisco 3905'], ['SEP3C5EC30C5B9A', 'FARM - e03', '91654', 'Cisco 3905'], ['SEP1CE85DC9FB70', 'FARM - e04', '91657', 'Cisco 3905'], ['SEP1CE85DC9FDA5', 'FARM - e05', '91662', 'Cisco 3905'], ['SEP1CE85DC9FD8A', 'FARM - e06', '91670', 'Cisco 3905'], ['SEP3C5EC30C5FC6', 'FARM - e07', '91664', 'Cisco 3905'], ['SEP188B4519C5C6', 'FARM - f02', '91785', 'Cisco 3905'], ['SEP188B4519C57A', 'FARM - f03', '91790', 'Cisco 3905'], ['SEP188B4519C558', 'FARM - g04', '91758', 'Cisco 3905'], ['SEP0041D2926A6B', 'FARM - g05', '91759', 'Cisco 3905'], ['SEP0041D2926727', 'FARM - g06', '91757', 'Cisco 3905'], ['SEP188B4519C535', 'FARM - g07', '91767', 'Cisco 3905'], ['SEP188B4519C5C4', 'FARM - g08', '91769', 'Cisco 3905'], ['SEP0041D2926A57', 'FARM - i06', '91728', 'Cisco 3905'], ['SEP0041D29266EC', 'FARM - j02', '91770', 'Cisco 3905'], ['SEP0041D29267B8', 'FARM - k05', '91762', 'Cisco 3905'], ['SEP0041D2926B09', 'FARM - k06', '91765', 'Cisco 3905']]

################################################################################
# Connect to DB and get [username, unit_id, switchport, isPoE] for each device
# Append this list to configured IP phones
# (new) all_devices = [mac_address, description, extension, device type, username, unit_id, switchport, isPoE]
################################################################################
try:
    conn = module_db_funcs.db_connect(DB_CREDS)
    cur = conn.cursor()

    for device in all_devices:
        # print(device)
        my_username, my_unit_id, my_switchport, my_isPoE = module_db_funcs.fetch_from_db_per_dn(cur, device[2])
        device.append(my_username)
        device.append(my_unit_id)
        device.append(my_switchport)
        device.append(my_isPoE)

    conn.close()
    for device in all_devices:
        print(device)

    # Measure Script Execution
    print("\n--->Runtime After DB Queries = {} \n\n\n".format(datetime.datetime.now()-start))

except Exception as ex:
    print(ex)
    conn.close()
    exit(0)


################################################################################
# Connect to voip switches and gathers info
# switch_devices_table:  [MAC address, switchport]
# voice_vlan_mac_table: [vlan, MAC address, switchport]
################################################################################
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
        print("Connect at switch: ", sw_device)
        conn = module_network_device_funcs.device_connect(sw_device, SW_CREDS)
        # Get cluster member IDs (modules)
        modules = module_network_device_funcs.get_cluster_members(conn)
        # print("Modules =", modules)

        for module in modules:
            device_model = module_network_device_funcs.get_device_model(conn, module)
            # print(device_model)

            # Run 'show cdp neighbors' and construct devices_table
            result = module_network_device_funcs.device_show_cmd(conn, "show cdp neighbors", module)
            lines = result.split('\n')
            for l in lines:
                # print("l = ",l)
                if re.match("^SEP", l) or re.match("^ATA", l):
                    mac_address = re.search("(\w\w\w[\w\d]*)", l).group(1).upper()
                    port = re.search(r'.*\/(\d+)\s', l).group(1)
                    my_dev = [mac_address, sw_device + "-m" + module + "-p" + str(int(port))]
                    switch_devices_table.append(my_dev)

            # Get 'full_mac_table' (switch full mac address table) and 'voip_mac_table' (keeps only voice macs)
            full_mac_table = module_network_device_funcs.get_switch_mac_table(conn, device_model, module)
            # print(full_mac_table)
            for mac_entry in full_mac_table:
                if len(mac_entry[0]) == 3 and (mac_entry[0] == "111" or mac_entry[0].startswith('7')):
                    # print(mac_entry[0])
                    my_mac = (mac_entry[1].upper()).replace('.', '')
                    my_dev = [mac_entry[0], my_mac, sw_device + "-m" + module + "-p" + str(int(mac_entry[2]))]
                    voice_vlan_mac_table.append(my_dev)

        conn.disconnect()

    for device in switch_devices_table:
        print(device)

    for mac in voice_vlan_mac_table:
        print(mac)

    ## Measure Script Execution
    print("\n--->Runtime After Accessing Switches = {} \n\n\n".format(datetime.datetime.now() - start))

except Exception as ex:
    print(ex)


################################################################################
# Sanity and Security Check
# all_devices = [mac_address, description, extension, device type, username, unit_id, switchport, isPoE]
# switch_devices_table:  [MAC address, switchport]
# voice_vlan_mac_table: [vlan, MAC address, switchport]
################################################################################

# Sanity Check
# excluded_extensions = ['99999']     # Exclude these extensions from the check
excluded_extensions = ['']     # Exclude these extensions from the check
try:
    sanity_body = ""
    for my_device1 in all_devices:
        for my_device2 in switch_devices_table:
            try:
                if my_device1[0] == my_device2[0] and my_device1[2] not in excluded_extensions:      # MAC match check
                    if my_device1[6] == my_device2[1]:  # switch port check
                        pass
                    else:
                        sanity_text = "Mismatch: Extension %s (Device %s) found at switchport %s but is actually declared at %s\n" \
                                      % (my_device1[2], my_device1[0], my_device2[1], my_device1[6])
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
# Excluded MACs: cvoice-rc-gw, 5x RC IP Phones registered at the old CUCM
# excluded_macs = ['C89C1D492B50', '001D70616E00', '503DE57D415E', '503DE5E93C10', '503DE5E947B1', 'C89C1DA33D1E']
excluded_macs = ['']

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


## Measure Script Execution
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


## Measure Script Execution
print("\n--->Runtime final = {} \n\n\n".format(datetime.datetime.now()-start))
