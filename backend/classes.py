class Phone:

    def __init__(self, name, description, device_type, extension, alerting_name):
        self.name = name
        if name.startswith('SEP') or name.startswith('ATA'):
            self.mac = name[3:]
        else:
            self.mac = ''
        self.description = description
        self.device_type = device_type
        self.extension = extension
        self.alerting_name = alerting_name
        self.status = None
        self.timestamp = None
        self.switchport = None
        self.responsible_person = None

    def print_device_axl(self):
        print("{}, {}, {}, {}, {}".format(self.name, self.description, self.device_type, self.extension, \
                                                   self.alerting_name))

    def print_device_ris(self):
        print("{}, {}, {}, {}, {}, {}, {}".format(self.name, self.description, self.device_type, \
                                                           self.extension, self.alerting_name, self.status, \
                                                           self.timestamp))
