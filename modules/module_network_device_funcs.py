
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
def device_show_cmd(connection, command, vendor, module):
    """
    :param connection: switch connector
    :param command: CLI command
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number

    :return: output of the the CLI show command
    """

    try:
        show_output = ""

        if vendor == "cisco":
            if module == "0":
                show_output = connection.send_command(command)
            else:
                connection.send_command("rcommand " + module, auto_find_prompt=False)
                # print(connection.find_prompt())
                show_output = connection.send_command(command)
                # Use delay factor to ensure netmiko properly exits from member switch
                connection.send_command("exit", auto_find_prompt=False, delay_factor=2)

        elif vendor == "dell":
            connection.send_command("terminal length 0\n", delay_factor=2)
            show_output = connection.send_command(command, delay_factor=2)

        return show_output

    except Exception as ex:
        print("device_show_cmd exception: ", ex.message)


########################################################################################################################
def get_device_model(connection, vendor, module):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number

    :return: device model (eg. WS-C2950C-24)
    """

    try:
        device_model = ""

        if vendor == "cisco":
            command = "show version"
            result = device_show_cmd(connection, command, vendor, module)
            device_model = re.search(r'cisco (WS\-[\d\w\-\+]*)',result).group(1)

        elif vendor == "dell":
            command = "show version"
            result = device_show_cmd(connection, command, vendor, module)
            device_model = re.search(r'System Model ID\.+ ([\w\d]+)', result).group(1)


        return device_model

    except Exception as ex:
        print("get_device_model exception: ", ex.message)


########################################################################################################################
def get_cisco_cluster_members(connection):
    """
    :param connection: switch connector

    :return: list of switch cluster members, eg [0,1,2,3] or ['0'] if none
    """

    try:
        command = "show cluster members"
        vendor = "cisco"
        module = "0"
        result = device_show_cmd(connection, command, vendor, module)

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
def get_switch_trunk_ports(connection, vendor, module):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number

    :return: trunk interface list, eg. ['Fa0/1', 'Gi0/2']
    """

    try:
        trunk_ports = []

        if vendor == "cisco":
            command = "show interface trunk"
            result = device_show_cmd(connection, command, vendor, module)
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
def discover_phones(connection, vendor, module):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number

    :return: [device name, interface, module]
    """

    try:
        neighbor_devices = []

        if vendor == "cisco":
            command = "show cdp neighbors"
            result = device_show_cmd(connection, command, vendor, module)
            dev_list = result.split('\n')
            for dev in dev_list:
                # print(repr(dev))
                try:
                    entry = re.search(r'([SA][ET][PA][\w\d]+)\s+([\S]+ [\S]+)', dev)
                    name = entry.group(1).upper()
                    interface = entry.group(2)
                    temp_neighbor_device = [name, interface, module]
                    neighbor_devices.append(temp_neighbor_device)
                except:
                    pass

        elif vendor == "dell":
            command = "show isdp neighbors"
            result = device_show_cmd(connection, command, vendor, module)
            # for res int result:
            #     neighbor_devices.append(res)
            dev_list = result.split('\n')
            for dev in dev_list:
                # print(repr(dev))
                try:
                    entry = re.search(r'([SA][ET][PA][\w\d]+)\s+([\S]+)', dev)
                    name = entry.group(1)
                    interface = entry.group(2)
                    temp_neighbor_device = [name, interface, module]
                    neighbor_devices.append(temp_neighbor_device)
                except:
                    pass


        return neighbor_devices

    except Exception as ex:
        print("discover_phones exception: ", ex.message)


########################################################################################################################
def get_switch_mac_table(connection, vendor, module):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number

    :return: [vlan, mac address, port]
    """

    try:
        mac_entry_list = []

        if vendor == "cisco":
            device_model = get_device_model(connection, vendor, module)
            if re.search('WS-C2950', device_model):
                command = "show mac-address-table"
            else:
                command = "show mac address-table"

            result = device_show_cmd(connection, command, vendor, module)
            mac_entries = re.split('\n', result)

            trunk_ports = get_switch_trunk_ports(connection, vendor, module)

            mac_entry_list = []
            for mac_entry in mac_entries:
                try:
                    my_port = re.search(r'.*([FGT][aie][\d|\/]+)', mac_entry).group(1)
                    if my_port not in trunk_ports:
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
def get_port_label(vendor, device_model):
    """
    :param vendor: eg. Cisco/Dell
    :param device_model: exact device model

    :return: the preceding port label (eg. "Fa0/")depending on switch model
    """

    try:
        port_label = ""

        if vendor == "cisco":
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
def get_port_status(connection, vendor, module, port):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number
    :param port: port number

    :return: port status (up/down)
    """

    try:
        port_status = ""

        if vendor == "cisco":
            device_model = get_device_model(connection, vendor, module)
            port_label = get_port_label(vendor, device_model)

            command = "show int " + port_label + port
            result = device_show_cmd(connection, command, vendor, module)

            if re.findall("line protocol is up", result):
                port_status = "up"
            elif re.findall("line protocol is down", result):
                port_status = "down"


        return port_status

    except Exception as ex:
        print("get_port_status exception: ", ex.message)


#######################################################################################################################
def get_port_power_status(connection, vendor, module, port):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number
    :param port: port number

    :return: port power status
    """

    try:
        port_power = ""

        if vendor == "cisco":
            device_model = get_device_model(connection, vendor, module)
            port_label = get_port_label(vendor, device_model)

            if re.search('WS-C.*[PL]C',device_model):
                command = "show power inline | include " + port_label + port
                result = device_show_cmd(connection, command, vendor, module)

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
def get_port_cabling(connection, vendor, module, port):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number
    :param port: port number

    :return: cabling diagnostics
    """

    try:
        port_cabling = ""

        if vendor == "cisco":
            device_model = get_device_model(connection, vendor, module)
            port_label = get_port_label(vendor, device_model)

            if re.search('WS-C2960', device_model):
                command = "test cable-diagnostics tdr interface " + port_label + port
                result = device_show_cmd(connection, command, vendor, module)
                # If this time is less it disrupts proper access to conn connector for following commands
                time.sleep(3)
                command = "show cable-diagnostics tdr interface " + port_label + port
                result = device_show_cmd(connection, command, vendor, module)
                port_cabling = re.search(r'(Fa|Gi)[\w\d\/\s\+\-]*', result).group()
            else:
                port_cabling = "Not Supported"

        return port_cabling

    except Exception as ex:
        print("get_port_cabling exception: ", ex.message)


########################################################################################################################
def get_port_macs(connection, vendor, module, port):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number
    :param port: port number

    :return: cabling diagnostics
    """

    try:
        mac_list = ""

        if vendor == "cisco":
            device_model = get_device_model(connection, vendor, module)
            port_label = get_port_label(vendor, device_model)
            if re.search('WS-C2950', device_model):
                command = "show mac-address-table interface " + port_label + port
            else:
                command = "show mac address-table interface " + port_label + port

            result = device_show_cmd(connection, command, vendor, module)
            mac_list = re.findall(r'[\w\d]+\.[\w\d]+\.[\w\d]+', result)
            for i, my_mac in enumerate(mac_list):
                mac_list[i] = (my_mac.replace('.','')).upper()

        return mac_list

    except Exception as ex:
        print("get_port_macs exception: ", ex.message)


########################################################################################################################
########################################################################################################################
def device_conft_cmd(connection, command, vendor, module):
    """
    :param connection: switch connector
    :param command: CLI command
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number

    :return: output of the the CLI "conf t" command
    """

    try:
        conft_output = ""

        if vendor == "cisco":
            if module == "0":
                print(command)
                conft_output = connection.send_config_set(command, delay_factor=2)
            else:
                print(command)
                conft_output = connection.send_command("rcommand " + module, auto_find_prompt=False)
                # Verify that member switch is accessed properly
                if conft_output == "":
                    conft_output = connection.send_config_set(command, delay_factor=2)
                    # Use delay factor to ensure netmiko properly exits from member switch
                    connection.send_command("exit", auto_find_prompt=False, delay_factor=2)

        return conft_output

    except Exception as ex:
        print("device_conft_cmd exception: ", ex.message)


########################################################################################################################
def conf_flap_port(connection, vendor, module, port):
    """
    :param connection: switch connector
    :param vendor: eg. Cisco/Dell
    :param module: cluster/stack member number
    :param port: port number

    :return: nothing
    """

    try:
        if vendor == "cisco":
            device_model = get_device_model(connection, vendor, module)
            port_label = get_port_label(vendor, device_model)

            command = ['interface ' + port_label + port, 'shut']
            result = device_conft_cmd(connection, command, vendor, module)
            command = ['interface ' + port_label + port, 'no shut']
            result = device_conft_cmd(connection, command, vendor, module)


    except Exception as ex:
        print("conf_flap_port exception: ", ex.message)


########################################################################################################################
