
import pymysql as mariadb       # PyMySQL


########################################################################################################################
def db_connect(DB_CREDS):
    """
    :param DB_CREDS: database credentials
    :return: database connector
    """

    try:
        conn = mariadb.connect(DB_CREDS['db_host'], DB_CREDS['db_username'], DB_CREDS['db_password'], DB_CREDS['db_name'])
        return conn

    except Exception as ex:
        print("db_connect exception: ", ex)
        return None


########################################################################################################################
def execute_db_query(cursor, query):
    """
    :param cursor: database cursor
    :param query: database query
    :return: result
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        return rows

    except Exception as ex:
        print("execute_db_query exception: ", ex)
        return None


########################################################################################################################
def auth_fetch_from_db_per_dn(cursor, dn):
    """
    :param cursor: database cursor (connector)
    :param dn: extension
    :return: [name, unit_id, switchport, isPoE]
    """

    try:
        # Get person_id, unit_id, access_outlet_id
        query = "select name, macaddress, assigned_to_person, assigned_to_unit, access_outlet_id from tel_extensions where number = '{}'".format(dn)

        cursor.execute(query)
        row = cursor.fetchone()
        # print("fetch_from_db_per_dn: row = ", row)
        if row is None:
            person_id = "unknown"
            unit_id = "unknown"
            access_outlet_id = "unknown"
        else:
            if row[2] is None:
                person_id = "unknown"
            else:
                person_id = str(row[2])
            if row[3] is None:
                unit_id = "unknown"
            else:
                unit_id = str(row[3])
            if row[4] is None:
                access_outlet_id = "unknown"
            else:
                access_outlet_id = str(row[4])

        # Get username from person_id
        if person_id == "unknown":
            username = "unknown"
        else:
            query = "select username from person where id ='%s'" % person_id
            cursor.execute(query)
            row = cursor.fetchone()
            username = row[0]

        # Get switchport info (node, module, port, poe) from access_ports
        if access_outlet_id == "unknown":
            switchport = "unknown"
            isPoE = "unknown"
        else:
            query = "select access_node_id, module, port, poe from access_ports where access_outlet_id = '%s'" % access_outlet_id
            cursor.execute(query)
            row = cursor.fetchone()
            if row is None:
                switchport = "unknown"
                isPoE = "unknown"
            else:
                # my_switchport = [row[0], row[1], row[2], row[3]]
                switchport = row[0] + '-m' + str(int(row[1])) + '-p' + str(int(row[2]))
                isPoE = row[3]

        # Get access_outlet_id info (status, usedFor) from access_outlet_id
        if access_outlet_id == "unknown":
            outlet_status = "unknown"
            outlet_usedFor = "unknown"
        else:
            query = "select status, usedFor from access_outlets where id = '%s'" % access_outlet_id
            cursor.execute(query)
            row = cursor.fetchone()
            if row is None:
                outlet_status = "unknown"
                outlet_usedFor = "unknown"
            else:
                outlet_status = str(row[0])
                outlet_usedFor = str(row[1])

        return username, unit_id, switchport, isPoE, access_outlet_id, outlet_status, outlet_usedFor

    except Exception as ex:
        print("fetch_from_db_per_dn exception: ", ex)
        return 'unknown', 'unknown', 'unknown', 'unknown'


########################################################################################################################
