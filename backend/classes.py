
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
        self.status = ""
        self.timestamp = ""
        self.switchport = ""
        self.responsible_person = ""

    def print_device_axl(self):
        print("{}, {}, {}, {}, {}".format(self.name, self.description, self.device_type, self.extension, \
                                                   self.alerting_name))

    def print_device_ris(self):
        print("{}, {}, {}, {}, {}, {}, {}".format(self.name, self.description, self.device_type, \
                                                           self.extension, self.alerting_name, self.status, \
                                                           self.timestamp))
    def print_device_full(self):
        print("{}, {}, {}, {}, {}, {}, {}, {}, {}".format(self.name, self.description, self.device_type, \
                                                          self.extension, self.alerting_name, self.status, \
                                                          self.timestamp, self.switchport, self.responsible_person))
