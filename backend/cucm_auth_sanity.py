
import json
import datetime
import re
from threading import Thread

from modules import module_cucm_funcs, module_db_funcs, module_network_device_funcs


########################################################################################################################
def get_cdp_mac_mthread(sw_dev):

    try:
        if sw_dev == "noc-clust-sw":
            conn = module_network_device_funcs.device_connect(sw_dev, RT_CREDS)
        else:
            conn = module_network_device_funcs.device_connect(sw_dev, SW_CREDS)

        modules = module_network_device_funcs.get_cisco_cluster_members(conn)

        for module in modules:
            vendor = "cisco"

            # Get CDP neighbors and construct the corresponding list
            cdp_devices = module_network_device_funcs.discover_phones(conn, vendor, module)
            if cdp_devices != []:
                for dev in cdp_devices:
                    dev.insert(2, sw_dev)
                    # mac_address = re.search("[SA][ET][PA]([\w\d]+)", dev[0]).group(1)
                    port = re.search(r'[\w]+ \S+/([\d]+)$', dev[1]).group(1)
                    my_dev = [dev[0], sw_dev + "-m" + module + "-p" + str(int(port))]
                    switch_devices_table.append(my_dev)

            # Get switch full mac address table and keeps only voice MACs
            full_mac_table = module_network_device_funcs.get_switch_mac_table(conn, vendor, module)
            for mac_entry in full_mac_table:
                if len(mac_entry[0]) == 3 and (mac_entry[0] == "111" or mac_entry[0].startswith('7')):
                    my_mac = (mac_entry[1].upper()).replace('.', '')
                    my_dev = [mac_entry[0], my_mac, sw_dev + "-m" + module + "-p" + str(int(mac_entry[2]))]
                    voice_vlan_mac_table.append(my_dev)

        conn.disconnect()

        # Get access_outlet_IDs for every switch for DB checks (to check is an outlet is type "IPphone" without having an IP Phone
        db_conn = module_db_funcs.db_connect(DB_CREDS)
        cursor = db_conn.cursor()
        query = "select access_outlet_id from access_ports where access_node_id = '{}'".format(sw_dev)
        rows = module_db_funcs.execute_db_query(cursor, query)
        db_conn.close()
        for row in rows:
            if row[0] != "" and row[0] is not None:
                voice_access_outlet_ids.append(str(row[0]))



    except:
        print("device_connect_multithread -> Can not connect to device {}\n".format(sw_dev))


########################################################################################################################
# Constant Variables
########################################################################################################################

data = json.load(open('../data/access.json'))                       # Windows
SWITCH_FILE = '../data/voip_switches.txt'
MAIL_FILE = '../data/output/report_sanity_security.txt'

data = json.load(open('/home/gfot/cucm_ms/data/access.json'))       # Linux
SWITCH_FILE = '/home/gfot/cucm_ms/data/voip_switches.txt'
MAIL_FILE = '/home/gfot/cucm_ms/data/output/report_sanity_security.txt'

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


################################################################################
start = datetime.datetime.now()


########################################################################################################################
# Get a list of all configured devices
########################################################################################################################
all_devices = []

try:
    all_devices = module_cucm_funcs.cucm_get_configured_devices(CM_PUB_CREDS)
except Exception as ex:
    print(ex)
    exit(0)

# Measure Script Execution
print("\n--->Runtime After AXLAPI SQL query = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Replace 3-digit internal extensions with the corresponding translation patterns
########################################################################################################################
try:
    xlation_patterns = module_cucm_funcs.cucm_get_translation_patterns(CM_PUB_CREDS)
    # print(xlation_patterns)
    for dev in all_devices:
        try:
            if len(dev.extension) == 3:
                dev.extension = xlation_patterns[dev.extension]
        except:
            continue
except Exception as ex:
    print(ex)
    exit(0)

# Measure Script Execution
print("\n--->Runtime After AXLAPI SQL query 2 = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Fill in all_devices with database info
########################################################################################################################
conn = ""
try:
    conn = module_db_funcs.db_connect(DB_CREDS)
    cursor = conn.cursor()

    for dev in all_devices:
        my_username, my_unit_id, my_switchport, my_isPoE, my_access_outlet_id, my_outlet_status, my_outlet_usedFor = module_db_funcs.auth_fetch_from_db_per_dn(cursor, dev.extension)
        dev.responsible_person = my_username
        dev.switchport = my_switchport
        dev.outlet_id = my_access_outlet_id
        dev.outlet_status = my_outlet_status
        dev.outlet_usedFor = my_outlet_usedFor
    conn.close()
except Exception as ex:
    print(ex)
    conn.close()
    exit(0)


# Measure Script Execution
print("\n--->Runtime After DB Queries = {} \n\n\n".format(datetime.datetime.now()-start))

for dev in all_devices:
    dev.print_device_full()


########################################################################################################################
# Connect to voip switches and gathers info
# switch_devices_table: [MAC address, switchport]
# voice_vlan_mac_table: [vlan, MAC address, switchport]
########################################################################################################################
switch_devices_table = []
voice_vlan_mac_table = []
voice_access_outlet_ids = []

try:
    fd = open(SWITCH_FILE, "r")
    switch_list = fd.read().splitlines()
    fd.close()
    print(switch_list)
    # switch_list = ["bld34fl02-sw"]
    # switch_list = ["bld61fl00-sw", "bld34fl00-sw"]

    threads = []
    for sw_device in switch_list:
        try:
            print("\nConnecting to switch: ", sw_device)
            process = Thread(target=get_cdp_mac_mthread, args=[sw_device])
            process.start()
            threads.append(process)
        except:
            continue

    for process in threads:
        process.join()

    # for device in switch_devices_table:
    #     print(device)
    # for mac in voice_vlan_mac_table:
    #     print(mac)
    # for id in voice_access_outlet_ids:
    #     print(id)

    # Remove from voice_access_outlet_ids the ones that are assigned to an IP Phone
    for dev in all_devices:
        for i, id in enumerate(voice_access_outlet_ids):
            if id == dev.outlet_id:
                voice_access_outlet_ids.pop(i)

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
# excluded_extensions = ['']
excluded_extensions = ['99999']   # Exclude these extensions from the check
sanity_body = ""
try:
    for my_device1 in all_devices:
        for my_device2 in switch_devices_table:
            try:
                if my_device1.name == my_device2[0] and my_device1.extension not in excluded_extensions:      # MAC match check
                    if my_device1.switchport == my_device2[1]:  # switch port check
                        pass
                    else:
                        if not my_device1.mac.startswith('34DBFD'):         # Exclude ATAs fro checks
                            sanity_text = "Mismatch: Extension %s (Device %s) found at switchport %s but is actually declared at %s\n" \
                                          % (my_device1.extension, my_device1.mac, my_device2[1], my_device1.switchport)
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


# Database Check
# excluded_extensions = ['']
excluded_extensions = ['99999']
db_body = ""
try:
    for dev in all_devices:
        if dev.outlet_id != "unknown":
            if dev.name.startswith("ATA") or dev.name.startswith("AALN")  or dev.outlet_usedFor == "Private" or dev.outlet_usedFor =="PcLabs" or dev.outlet_status == "Active Enforced":
                continue

            if dev.outlet_status != "Active":
                if dev.outlet_status == "Locked":
                    conn = module_db_funcs.db_connect(DB_CREDS)
                    cursor = conn.cursor()
                    query = "select statusReason from access_outlets where id = '{}'".format(dev.outlet_id)
                    rows = module_db_funcs.execute_db_query(cursor, query)
                    conn.close()
                    if rows[0] != "":
                        continue
                db_text = "Extension {} is not properly declared in authDB. Status is {}\n".format(dev.extension, dev.outlet_status)
                db_body += db_text
            if dev.outlet_usedFor != "IPphone":
                db_text = "Extension {} is not properly declared in authDB. Type is {}\n".format(dev.extension, dev.outlet_usedFor)
                db_body += db_text

except Exception as ex:
    print(ex)
    exit(0)


# Database Check - 2
db_body2 = ""
try:
    db_conn = module_db_funcs.db_connect(DB_CREDS)
    cursor = db_conn.cursor()
    for id in voice_access_outlet_ids:
        query = "select usedFor, floor_building_id, name from access_outlets where id = '{}'".format(id)
        row = module_db_funcs.execute_db_query(cursor, query)
        usedFor = row[0][0]
        floor_building_id = row[0][1]
        outlet_id = row[0][2]

        if usedFor == "IPphone":
            # print(usedFor, floor_building_id, outlet_id)
            query2 = "select building_id, floor_id from floor_buildings where id = '{}'".format(floor_building_id)
            row2 = module_db_funcs.execute_db_query(cursor, query2)
            building_id = row2[0][0]
            floor_id = row2[0][1]
            # print(building_id, floor_id)

            db_text = "Outlet {}-{}-{} is type {} but no IP phone is registered to it\n".format(building_id, floor_id, outlet_id, usedFor)
            db_body2 += db_text

    db_conn.close()

except Exception as ex:
    print(ex)
    exit(0)

# Security Check
# Excluded MACs: cvoice-rc-gw, 5x RC IP Phones registered at the old CUCM, old CUCMs, EIKASTIKES2 ATA
# excluded_macs = ['']
excluded_macs = ['C89C1D492B50', '000C2905DB8B', '000C291D59FB', '000C2950DF27', '000C31E9F121', 'C89C1D893390', 'E41F13252289', 'E41F1325280B', '34DBFD1835D9']

security_body = ""
for mac in voice_vlan_mac_table:
    found = False
    for device1 in all_devices:
        if mac[1] in device1.mac or mac[1] in excluded_macs:
            found = True

    if found:
        pass
    else:
        security_body += "Ilegal MAC address %s at switchport %s in vlan %s\n" % (mac[1], mac[2], mac[0])


# Measure Script Execution
print("\n--->Runtime After Processing = {} \n\n\n".format(datetime.datetime.now()-start))


################################################################################
# Construct report file
################################################################################
mail_body = """
------------------------------------------------------------------------------------------------------------------------
Sanity check:

%s

------------------------------------------------------------------------------------------------------------------------
DB check (check if outlets with an IP Phone have the correct status):

%s

------------------------------------------------------------------------------------------------------------------------
DB check (check if type "IPphone" outlets actually have an IP phone assigned:

%s

------------------------------------------------------------------------------------------------------------------------
Security check:

%s

------------------------------------------------------------------------------------------------------------------------
""" % (sanity_body, db_body, db_body2, security_body)

print(mail_body)

if sanity_body or security_body:
    target = open(MAIL_FILE, "w")
    target.write(mail_body)
    target.close()


# Measure Script Execution
print("\n--->Runtime final = {} \n\n\n".format(datetime.datetime.now()-start))
