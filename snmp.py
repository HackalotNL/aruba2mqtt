from pysnmp.hlapi import nextCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, OctetString


def retrieve(hostname, port, community, *names):
    iterator = nextCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        UdpTransportTarget((hostname, port)),
        ContextData(),
        ObjectType(
            ObjectIdentity(
                *names,
            )
            .addAsn1MibSource(
                'file://.',
                'file:///usr/share/snmp',
            )
        ),
        lexicographicMode=False,
    )

    for response in iterator:
        errorIndication, errorStatus, errorIndex, varBinds = response

        if errorIndication:
            print(errorIndication)

        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))

        else:
            for varBind in varBinds:
                yield varBind[0].getMibSymbol(), varBind[1]


def gather(host, port, community):
    apStats = {}
    macApAlias = {}
    macSsidAlias = {}
    assocSsidStats = {}
    assocApStats = {}

    auth = (host, port, community)

    for oid, value in retrieve(*auth, 'AI-AP-MIB', 'aiAccessPointTable'):
        _, label, index = oid
        mac = index[0].prettyPrint()

        if mac not in apStats:
            apStats[mac] = {
                'ssid': [],
                'mac': [],
            }
            assocApStats[mac] = 0
        apStats[mac][label] = value

    for oid, value in retrieve(*auth, 'AI-AP-MIB', 'aiWlanEntry'):
        _, label, index = oid
        mac = index[0].prettyPrint()
        idx = index[1]

        if mac not in apStats.keys():
            # AP appeared during stat retrieval
            continue

        if label == 'aiWlanESSID':
            apStats[mac]['ssid'].insert(idx, value)
        elif label == 'aiWlanMACAddress':
            apStats[mac]['mac'].insert(idx, value)
            macApAlias[value] = mac

    for mac in apStats:
        for idx, ssid in enumerate(apStats[mac]['ssid']):
            macSsidAlias[apStats[mac]['mac'][idx]] = ssid

            if ssid not in assocSsidStats:
                assocSsidStats[ssid] = 0

        del apStats[mac]['mac']
        del apStats[mac]['ssid']

    for oid, value in retrieve(*auth, 'AI-AP-MIB', 'aiClientWlanMACAddress'):  # from aiClientTable
        _, label, index = oid
        assocSsidStats[macSsidAlias[value]] += 1
        assocApStats[macApAlias[value]] += 1

    return apStats, assocApStats, assocSsidStats
