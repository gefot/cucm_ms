import pymysql as mariadb       # PyMySQL


#####################################################################
def db_connect(DB_CREDS):
    '''
    Connects to database and returns 'conn' connector
    '''
    try:
        conn = mariadb.connect(DB_CREDS['db_host'], DB_CREDS['db_username'], DB_CREDS['db_password'], DB_CREDS['db_name'])
        return conn

    except Exception as ex:
        print("db_connect exception: ", ex)
        return None


########################################################################
# def execute_db_query(cursor, query):
#     try:
#         cursor.execute(query)
#         rows = cur.fetchall()
#
#         return rows
#
#     except Exception as ex:
#         print(ex)
#         return None


########################################################################
def fetch_from_db_per_dn(cursor, dn):
    '''
    Queries database based on extension (dn) and returns list [name, unit_id, switchport, isPoE]
    '''
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
                person_id = row[2]
            if row[3] is None:
                unit_id = "unknown"
            else:
                unit_id = row[3]
            if row[4] is None:
                access_outlet_id = "unknown"
            else:
                access_outlet_id = row[4]

        # Get username from person_id
        if person_id is "unknown":
            username = "unknown"
        else:
            query = "select username from person where id ='%s'" % person_id
            cursor.execute(query)
            row = cursor.fetchone()
            username = row[0]

        # Get switchport info (node, module, port, poe) from access_outlet_id
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
                # switchport = my_switchport

        return username, unit_id, switchport, isPoE

    except Exception as ex:
        print("fetch_from_db_per_dn exception: ", ex)
        return 'unknown', 'unknown', 'unknown', 'unknown'


########################################################################
