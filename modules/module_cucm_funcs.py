
import os
import ssl
from pathlib import Path
import datetime

import pexpect                      # pexpect
from suds.xsd.doctor import Import  # suds-jurko
from suds.xsd.doctor import ImportDoctor    # suds-jurko
from suds.client import Client      # suds-jurko
# from suds import WebFault         # suds-jurko


########################################################################################################################
def cucm_axl_query(CM_CREDS, command, query):
    """
    Utilize CUCM AXL interface using SOAP
    Uses a predefined WSDL file, which is stored locally.

    Used in: cucm_get_configured_devices

    :param CM_CREDS:
    :param command:
    :param query:
    :return: client
    """
    try:
        my_path = '/' + str(Path(os.getcwd()).parent).replace('\\', '/') + '/data/'     # Windows
        wsdl_file_location = 'file://{}AXLAPI.wsdl'.format(my_path)

        tns = 'http://schemas.cisco.com/ast/soap/'
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/', 'http://schemas.xmlsoap.org/soap/encoding/')
        imp.filter.add(tns)

        url_location = 'https://{}:{}/axl/'.format(CM_CREDS['cm_server_ip_address'], CM_CREDS['cm_server_port'])

        # Bypass certificate warning
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context

        client = Client(wsdl_file_location, location=url_location, username=CM_CREDS['soap_user'], \
                        password=CM_CREDS['soap_pass'], plugins=[ImportDoctor(imp)], faults=False)

        if command == "executeSQLQuery":
            return client.service.executeSQLQuery(query)
        elif command == "getPhone":
            return client.service.getPhone(name=query)
        elif command == "listPhone":
            return client.service.listPhone(query, returnedTags={'name': '', 'description': ''})

    except Exception as ex:
        print("cucm_axl_query exception: ", ex)
        return None


########################################################################################################################
def cucm_risport_query(CM_CREDS, command, query):
    """
    Utilize CUCM RisPort interface using SOAP

    Used in: cucm_fill_devices_status

    :param CM_CREDS: CUCM credentials
    :param command: eg: SelectCmDevice
    :param query: the query itself
    :return: client
    """
    try:
        tns = 'http://schemas.cisco.com/ast/soap/'
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/', 'http://schemas.xmlsoap.org/soap/encoding/')
        imp.filter.add(tns)

        wsdl = 'https://{}:{}/realtimeservice/services/RisPort?wsdl'.format(CM_CREDS['cm_server_ip_address'],
                                                                            CM_CREDS['cm_server_port'])
        location = 'https://{}:{}/realtimeservice/services/RisPort'.format(CM_CREDS['cm_server_ip_address'],
                                                                           CM_CREDS['cm_server_port'])
        # Bypass certificate warning
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context

        client = Client(wsdl, location=location, username=CM_CREDS['soap_user'], password=CM_CREDS['soap_pass'],
                        plugins=[ImportDoctor(imp)])
        if command == 'SelectCmDevice':
            return client.service.SelectCmDevice('', query)

    except Exception as ex:
        print("cucm_risport_query exception: ", ex)
        return None


########################################################################################################################
def cucm_get_configured_devices(CM_CREDS):
    """
    :param CM_CREDS: CUCM credentials
    :return: [mac_address, description, extension, alerting name, device type]
    """
    try:
        sql_query = "select a.name, a.description, b.dnorpattern, b.alertingname, c.display, d.name as type from device as a, \
        numplan as b, devicenumplanmap as c, typemodel as d where c.fkdevice = a.pkid and c.fknumplan = b.pkid and \
        a.tkmodel = d.enum and numplanindex = 1"

        result = cucm_axl_query(CM_CREDS, "executeSQLQuery", sql_query)

        device_list_full = result[1]['return'].row
        all_configured_devices = []
        for dev in device_list_full:
            if dev.name.startswith(("SEP", "ATA", "AALN", "AN", "CSF")):
                temp_dev = [str(dev.name), str(dev.description), str(dev.dnorpattern), str(dev.alertingname), str(dev.type)]
                all_configured_devices.append(temp_dev)
            else:
                continue

        return all_configured_devices

    except Exception as ex:
        print("cucm_get_configured_devices exception: ", ex)
        return None


########################################################################################################################
def cucm_count_interering_devices(devices):
    """
    :param devices: list of (configured) devices
    :return: [Total, IP Phones, ATA devices, ATA ports, Analog, Jabber]
    """
    try:
        device_count = [0] * 6
        for device in devices:
            if device[0].startswith("SEP"):
                device_count[0] += 1
                device_count[1] += 1
            elif device[0].startswith("ATA"):
                device_count[3] += 1        # ATA port count
                if not device[0].endswith("01"):
                    device_count[0] += 1
                    device_count[2] += 1    # ATA device count
            elif device[0].startswith("AN") or device[0].startswith("AALN"):
                device_count[0] += 1
                device_count[4] += 1
            elif device[0].startswith("CSF"):
                device_count[0] += 1
                device_count[5] += 1

        return device_count

    except Exception as ex:
        print("cucm_count_interering_devices exception: ", ex)
        return [0] * 5


########################################################################################################################
def cucm_fill_devices_status(CM_CREDS, all_devices):
    """
    :param CM_CREDS: CUCM Credentials
    :param all_devices: configured devices
    :return: [mac_address, description, extension, alerting name, device type, status, timestamp]
    """
    try:
        command = "SelectCmDevice"
        query = {'SelectBy': 'Name', 'Status': 'Any', 'Class': 'Any', 'MaxReturnedDevices': '5000'}

        result = cucm_risport_query(CM_CREDS, command, query)

        for device in all_devices:
            found_device = False
            for node in result['SelectCmDeviceResult']['CmNodes']:
                if node['Name'] in CM_CREDS['cm_server_ip_address']:
                    for status_device in node['CmDevices']:
                        if device[0] == status_device['Name']:
                            found_device = True
                            timestamp = datetime.datetime.fromtimestamp(int(status_device['TimeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
                            device.append(str(status_device['Status']).lower())
                            device.append(timestamp)

            if not found_device:
                device.append("unregistered")
                device.append("More than a week")

        return all_devices

    except Exception as ex:
        print("cucm_fill_devices_status exception: ", ex)
        return None

#################################################################################
# Connect to CUCM PerfmonPort interface using SOAP
# def cucm_perfmonport(cmserver, cmport, soap_user, soap_pass, perfmon_counter):
#     try:
#         tns = 'http://schemas.cisco.com/ast/soap/'
#         imp = Import('http://schemas.xmlsoap.org/soap/encoding/', 'http://schemas.xmlsoap.org/soap/encoding/')
#         imp.filter.add(tns)
#         wsdl = 'https://' + cmserver + ':' + cmport + '/perfmonservice/services/PerfmonPort?wsdl'
#         location = 'https://' + cmserver + ':' + cmport + '/perfmonservice/services/PerfmonPort?wsdl'
#
#         client = Client(wsdl, location=location, username=soap_user, password=soap_pass, plugins=[ImportDoctor(imp)])
#
#         if perfmon_counter == "all":
#             return client.service.PerfmonListCounter(cmserver)
#         else:
#             return str(client.service.PerfmonCollectCounterData(cmserver, perfmon_counter))
#
#     except:
#         return None


#################################################################################
# # Connect to CUCM CLI, run a command and return output
# def cucm_cli_cmd(server_ip, server_user, server_pass, cmd):
#     try:
#         child = pexpect.spawn('ssh %s@%s' % (server_user, server_ip))
#
#         child.timeout = 60
#         child.expect('password:')
#         child.sendline(server_pass)
#         child.expect('admin:')
#         child.sendline(cmd)
#         child.expect('admin:')
#         output = child.before
#         child.sendline('quit')
#
#         return output
#
#     except:
#         return None



#################################################################################
# def cucm_risport_get_mac_per_dn(cmserver_hostname, cmserver_ip, cmport, soap_user, soap_pass, dn):
#     try:
#         # Get MAC address according to DN
#         command = "SelectCmDevice"
#         item_name = dn
#         query = {'SelectBy': 'DirNumber', 'Status': 'Any', 'Class': 'Any',
#                  'SelectItems': {'SelectItem': {'Item': item_name}}}
#         result = cucm_risport(cmserver_hostname, cmport, soap_user, soap_pass, command, query)
#         for node in result['SelectCmDeviceResult']['CmNodes']:
#             if node['Name'] in cmserver_ip:
#                 for device in node['CmDevices']:
#                     mac_address = device['Name']
#         return mac_address
#     except:
#         return None


#################################################################################
# def cucm_risport_get_info(cmserver_hostname, cmserver_ip, cmport, soap_user, soap_pass, mac_address, dn, ip_address,
#                           description):
#     try:
#         command = "SelectCmDevice"
#
#         if mac_address is not "":
#             mac_address = "*" + mac_address + "*"
#             item_name = mac_address
#             query = {'SelectBy': 'Name', 'Status': 'Any', 'Class': 'Any',
#                      'SelectItems': {'SelectItem': {'Item': item_name}}}
#             result = cucm_risport(cmserver_hostname, cmport, soap_user, soap_pass, command, query)
#         elif dn is not "":
#             dn = "*" + dn + "*"
#             item_name = dn
#             query = {'SelectBy': 'DirNumber', 'Status': 'Any', 'Class': 'Any',
#                      'SelectItems': {'SelectItem': {'Item': item_name}}}
#             result = cucm_risport(cmserver_hostname, cmport, soap_user, soap_pass, command, query)
#         elif ip_address is not "":
#             ip_address = "*" + ip_address + "*"
#             item_name = ip_address
#             query = {'SelectBy': 'IpAddress', 'Status': 'Any', 'Class': 'Any',
#                      'SelectItems': {'SelectItem': {'Item': item_name}}}
#             result = cucm_risport(cmserver_hostname, cmport, soap_user, soap_pass, command, query)
#         elif description is not "":
#             description = "*" + description + "*"
#             item_name = description
#             query = {'SelectBy': 'Description', 'Status': 'Any', 'Class': 'Any',
#                      'SelectItems': {'SelectItem': {'Item': item_name}}}
#             result = cucm_risport(cmserver_hostname, cmport, soap_user, soap_pass, command, query)
#
#         all_devices = []
#         my_device = []
#         i = 0
#         for node in result['SelectCmDeviceResult']['CmNodes']:
#             if node['Name'] in cmserver_ip:
#                 for device in node['CmDevices']:
#                     timestamp = datetime.datetime.fromtimestamp(int(device['TimeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
#                     my_device = [device['Name'], device['DirNumber'], device['Status'], device['Description'],
#                                  device['IpAddress'], timestamp]
#                     all_devices.append(my_device)
#
#         return all_devices
#     except:
#         return []


#################################################################################