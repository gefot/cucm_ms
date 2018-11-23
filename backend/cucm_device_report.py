
import json
import datetime
import operator

from modules import module_cucm_funcs, module_db_funcs, module_network_device_funcs


########################################################################################################################
# Constant Variables
########################################################################################################################
data = json.load(open('../data/access.json'))                 # Windows
DEVICE_REPORT_FILE = '../data/output/device_report.txt'

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
# Get a list of and count all configured devices
########################################################################################################################
try:
    all_devices = module_cucm_funcs.cucm_get_configured_devices(CM_PUB_CREDS)
    # print(all_devices)
except Exception as ex:
    print(ex)
    exit(0)

# Measure Script Execution
print("\n--->Runtime After AXLAPI SQL query = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Fill the list of the configured devices with info from RIS database
########################################################################################################################
try:
    all_devices = module_cucm_funcs.cucm_fill_devices_status(CM_PUB_CREDS, all_devices)
    all_devices = sorted(all_devices, key=operator.itemgetter(1), reverse=False)
except Exception as ex:
    print(ex)
    exit(0)

# Measure Script Execution
print("\n--->Runtime After RIS query = {} \n\n\n".format(datetime.datetime.now() - start))


########################################################################################################################
# Construct unred_devices and fill in with info from the database
########################################################################################################################
try:
    conn = module_db_funcs.db_connect(DB_CREDS)
    cursor = conn.cursor()
    unreg_devices = []
    for device in all_devices:
        if device[5] == "unregistered":
            unreg_dev = device.copy()
            my_username, my_unit_id, my_switchport, my_isPoE = module_db_funcs.fetch_from_db_per_dn(cursor, device[2])
            unreg_dev.extend((my_username, my_unit_id, my_switchport, my_isPoE))
            unreg_devices.append(unreg_dev)
    conn.close()
except Exception as ex:
    print(ex)
    conn.close()
    exit(0)

# Measure Script Execution
print("\n--->Runtime After DB Queries = {} \n\n\n".format(datetime.datetime.now() - start))




########################################################################################################################
all_devices_count = module_cucm_funcs.cucm_count_interering_devices(all_devices)
print("device count = ", all_devices_count)
unreg_devices_count = module_cucm_funcs.cucm_count_interering_devices(unreg_devices)
print("unreg device count = ", unreg_devices_count)

print('======================================')
for dev in all_devices:
    print(dev)
print('======================================')
for dev in unreg_devices:
    print(dev)


########################################################################################################################
# Troubleshooting Section
########################################################################################################################
# device_model = []
# port_status = []
# port_power = []
# port_tdr = []
# found_mac = []
#
# if len(sys.argv) == 3 and sys.argv[2] == "tshoot":
# 	for i,device in enumerate(unreg_devices):
# 		#print "device = ",device
# 		try:
# 			if (switchport[i] == "unknown"):
# 				print "->Not trying any device"
# 				device_model.append("unknown")
# 				port_status.append("unknown")
# 				port_power.append("unknown")
# 				port_tdr.append("unknown")
# 				found_mac.append("unknown")
# 			else:
# 				sw_device = switchport[i][0]
# 				module = str(int(switchport[i][1]))
# 				port = str(int(switchport[i][2]))
# 				#print sw_device,module,port
#
# 				print "->Trying switch: ",sw_device
# 				conn = MOD_device_funcs.device_connect(sw_connection_type,sw_device,sw_username,sw_password,sw_enable,sw_port,sw_verbose)
#
# 				my_device_model = MOD_device_funcs.get_device_model(conn, module)
# 				port_label = MOD_device_funcs.get_port_label(conn, my_device_model, module)
# 				my_port_status = MOD_device_funcs.get_port_status(conn, my_device_model, module, port_label, port)
# 				my_port_power = MOD_device_funcs.get_port_power(conn, my_device_model, module, port_label, port)
# 				my_port_tdr = MOD_device_funcs.get_port_tdr(conn, my_device_model, module, port_label, port)
# 				my_port_macs = MOD_device_funcs.get_port_macs(conn, my_device_model, module, port_label, port)
#
# 				conn.disconnect()
#
# 				# Check if port_macs contains unreg_device MAC address
# 				#print "my_port_macs =",my_port_macs
# 				if my_port_macs:
# 					found = False
# 					for my_mac in my_port_macs:
# 						mac = "SEP"+(my_mac.replace('.','')).upper()
# 						if found == False and mac == device[0]:
# 							found = True
#
# 					if found == True:
# 						my_found_mac = "Yes"
# 						# Perform shut/no shut
# 						# conn = MOD_device_funcs.device_connect(sw_connection_type,sw_device,sw_username,sw_password,sw_enable,sw_port,sw_verbose)
# 						# my_device_model = MOD_device_funcs.get_device_model(conn, module)
# 					else:
# 						my_found_mac = "No"
# 				else:
# 					my_found_mac = "No"
#
# 				device_model.append(my_device_model)
# 				port_status.append(my_port_status)
# 				port_power.append(my_port_power)
# 				port_tdr.append(my_port_tdr)
# 				found_mac.append(my_found_mac)
#
#
# 		except Exception as e:
# 			print "Exception:",e.message
# 			device_model.append("unknown")
# 			port_status.append("unknown")
# 			port_power.append("unknown")
# 			port_tdr.append("unknown")
# 			found_mac.append("unknown")
#
# 	print "\n\n"
# 	print device_model
# 	print port_status
# 	print port_power
# 	print port_tdr
# 	print found_mac
#
#
# 	## Measure Script Execution
# 	print "\n\n--->Runtime after Tshoot Section = ",datetime.datetime.now()-start
#
#
#
# ################################
# ## Format output for e-mail body
# ################################
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
