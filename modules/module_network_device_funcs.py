
import netmiko		# netmiko
import re
import time


########################################################################################################################
def device_connect(my_device, SW_CREDS):
    """
    :param my_device: the switch to connect
    :param SW_CREDS: switch credentials
    :return: switch connector
    """
    try:
        dev = dict(ip=my_device, device_type=SW_CREDS['my_connection_type'], username=SW_CREDS['sw_username'], \
                   password=SW_CREDS['sw_password'], secret=SW_CREDS['sw_enable'], \
                   port=SW_CREDS['sw_port'], verbose=SW_CREDS['sw_verbose'])
        conn = netmiko.ConnectHandler(**dev)
        conn.enable()

        return conn

    except Exception as ex:
        print("device_connect exception: ", ex.message)


########################################################################################################################
def get_cisco_cluster_members(conn):
    """
    :param conn: switch connector
    :return: list of switch cluster members, eg [0,1,2,3] or ['0'] if none
    """
    try:
        command = "show cluster members"
        module = "0"
        result = device_show_cmd(conn, command, module)

        modules = []
        lines = re.split('\n', result)
        for l in lines:
            m = re.search("^(\d+)\s?", l)
            if m is not None:
                modules.append(m.group(1))
        if modules is None:
            modules = ['0']

        return modules

    except Exception as ex:
        print("get_cisco_cluster_members exception: ", ex.message)


########################################################################################################################
def get_device_model(conn, module):
    """
    :param conn: switch connector
    :param module: cluster module number
    :return: device model (eg. WS-C2950C-24)
    """
    try:
        # Cisco
        command = "show version"
        result = device_show_cmd(conn, command, module)

        device_model = re.search(r'cisco (WS\-[\d\w\-\+]*)',result).group(1)

        return device_model

    except Exception as ex:
        print("get_device_model exception: ", ex.message)


########################################################################################################################
def device_show_cmd(conn, command, module):
    """
    :param conn: switch connector
    :param command: CLI command
    :param module: cluster member number
    :return: output for CLI show command
    """
    try:
        if module == "0":
            result = conn.send_command(command)

            return result
        else:
            conn.send_command("rcommand " + module, auto_find_prompt=False)
            # print(connection.find_prompt())
            result = conn.send_command(command)
            conn.send_command("exit", auto_find_prompt=False)

            return result

    except Exception as ex:
        print("device_show_cmd exception: ", ex.message)


########################################################################################################################
def get_switch_trunk_ports(connection, device_model, module):
    """
    :param connection: switch connector
    :param module: cluster member number
    :return: trunk interface list, eg. ['Fa0/1', 'Gi0/2']
    """
    try:
        # Cisco
        if re.search('WS-C', device_model):
            trunk_ports = []

            command = "show interface trunk"
            result = device_show_cmd(connection, command, module)
            trunk_ints = re.split('\n', result)

            for trunk in trunk_ints:
                try:
                    trunk_port = re.search(r'([FGT][aie][\d|\/]+).*trunking', trunk)
                    trunk_port = trunk_port.group(1)
                    trunk_ports.append(trunk_port)
                except:
                    pass


        return trunk_ports

    except Exception as ex:
        print("get_switch_trunk_ports exception: ", ex.message)


########################################################################################################################
def get_switch_mac_table(connection, device_model, module):
    """
    :param connection: switch connector
    :param device_model: switch model
    :param module: cluster member number
    :return: [vlan, mac address, port]
    """
    try:
        # Cisco
        if re.search('WS-C', device_model):
            if re.search('WS-C2950', device_model):
                command = "show mac-address-table"
            else:
                command = "show mac address-table"

            result = device_show_cmd(connection, command, module)
            mac_entries = re.split('\n', result)

            trunk_ports = get_switch_trunk_ports(connection, device_model, module)

            mac_entry_list = []
            for mac_entry in mac_entries:
                try:
                    my_port = re.search(r'.*([FGT][aie][\d|\/]+)', mac_entry).group(1)
                    if my_port not in trunk_ports:
                        # print(mac_entry)
                        entry = re.search(r'(\d+)\s+([\w\d]+\.[\w\d]+\.[\w\d]+)[\w\d\s]+[FG][ai].*\/(\d+)', mac_entry)
                        vlan = entry.group(1)
                        mac = entry.group(2)
                        port = entry.group(3)
                        mac_entry_list.append([vlan, mac, port])
                except:
                    pass


        return mac_entry_list

    except Exception as ex:
        print("get_switch_mac_table exception: ", ex.message)


########################################################################################################################
def get_port_label(device_model):
    """
    :param device_model: device model
    :return: the preceding port label (eg. "Fa0/")depending on switch model
    """
    try:
        # Cisco
        if re.search('WS-C', device_model):
            if re.search('WS-C2960X',device_model) or re.search('WS-C2960S',device_model):
                port_label = "Gi1/0/"
            elif re.search('WS-C2960G',device_model):
                port_label = "Gi0/"
            elif re.search('WS-C2960-',device_model) or re.search('WS-C2960\+',device_model):
                port_label = "Fa0/"
            elif re.search('WS-C2950',device_model):
                port_label = "Fa0/"
            else:
                port_label = "Fa0/"

        return port_label

    except Exception as ex:
        print("get_port_label exception: ", ex.message)


########################################################################################################################
def get_port_status(connection, device_model, module, port):
    """
    :param connection: switch connector
    :param device_model: switch model
    :param module: cluster member number
    :param port: port number
    :return: port status (up/down)
    """
    try:
        # Cisco
        if re.search('WS-C', device_model):
            port_label = get_port_label(device_model)

            command = "show int " + port_label + port
            result = device_show_cmd(connection, command, module)

            if re.findall("line protocol is up", result):
                port_status = "up"
            elif re.findall("line protocol is down", result):
                port_status = "down"


        return port_status

    except Exception as ex:
        print("get_port_status exception: ", ex.message)


#######################################################################################################################
def get_port_power_status(connection, device_model, module, port):
    """
    :param connection: switch connector
    :param device_model: switch model
    :param module: cluster member number
    :param port: port number
    :return: port power status
    """
    try:
        # Cisco
        if re.search('WS-C', device_model):
            port_label = get_port_label(device_model)

            if re.search('WS-C.*[PL]C',device_model):
                command = "show power inline | include " + port_label + port
                result = device_show_cmd(connection, command, module)
                print(result)

                power_output = re.split(" {2,}", result)
                if power_output[2] == "off":
                    port_power = "PoE Port - Off"
                elif power_output[2] == "on":
                    if power_output[4] == "Ieee PD":
                        port_power = "PoE Port - Ieee PD - " + power_output[6]
                    elif re.search('IP Phone', power_output[4]):
                        port_power = "PoE Port - IP Phone - " + power_output[6] + "W"
                    else:
                        port_power = "PoE Port - No Power"
            else:
                port_power = "PoE Injector"


        return port_power

    except Exception as ex:
        print("get_port_power exception: ", ex.message)

########################################################################################################################
def get_port_cabling(connection, device_model, module, port):
    """
    :param connection: switch connector
    :param device_model: switch model
    :param module: cluster member number
    :param port: port number
    :return: cabling diagnostics
    """
    try:
        # Cisco
        if re.search('WS-C', device_model):
            port_label = get_port_label(device_model)

            if re.search('WS-C2960',device_model):
                command = "test cable-diagnostics tdr interface " + port_label + port
                result = device_show_cmd(connection, command, module)
                time.sleep(1)
                command = "show cable-diagnostics tdr interface " + port_label + port
                result = device_show_cmd(connection, command, module)
                port_cabling = re.search(r'(Fa|Gi)[\w\d\/\s\+\-]*',result).group()
            else:
                port_cabling = "Not Supported"


        return port_cabling

    except Exception as ex:
        print("get_port_cabling exception: ", ex.message)


########################################################################################################################
# # Return a list of MAC addresses for a specific port
# def get_port_macs(connection, device_model, module, port_label, port):
# 	try:
# 		if re.search('WS-C2950',device_model):
# 			command = "show mac-address-table interface "+port_label+port
# 		elif re.search('WS-C2960',device_model):
# 			command = "show mac address-table interface "+port_label+port
# 		else:
# 			command = "show mac address-table interface "+port_label+port
#
# 		result = device_show_cmd(connection,command,module)
# 		macs = re.findall("[\w\d]+\.[\w\d]+\.[\w\d]+",result)
#
# 		return macs
#
# 	except Exception as e:
# 		print "-8.Exception:",e.message
# 		raise RuntimeError("Could not get MAC addresses")
#
#

