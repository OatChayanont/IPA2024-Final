from ncclient import manager
import xmltodict
import os
from dotenv import load_dotenv

load_dotenv()

m = manager.connect(
    host=os.getenv("ROUTER_IP"),
    port=830,
    username=os.getenv("ROUTER_USERNAME"),
    password=os.getenv("ROUTER_PASSWORD"),
    hostkey_verify=False
    )

LOOPBACK_NAME = "Loopback64070017"
LOOPBACK_IP = "172.0.17.1"

def create():

    def interface_exists(name):
        filt = f"""
<filter>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{name}</name>
    </interface>
  </interfaces>
</filter>"""
        try:
            reply = m.get_config(source="running", filter=filt)
            data = xmltodict.parse(reply.xml)
            print(data)
            interfaces = data.get('rpc-reply', {}).get('data', {}).get('interfaces')
            if interfaces and interfaces.get('interface'):
                intf = interfaces['interface']
                print("##########################")
                print(intf)
                print("##########################")
                # Could be list or dict
                if isinstance(intf, list):
                    return any(i.get('name') == name for i in intf)
                print(intf.get('name').get('#text') == name)
                return intf.get('name').get('#text') == name
            return False
        except Exception as e:
            print(f"Check exists error: {e}")
            return False

    if interface_exists(LOOPBACK_NAME):
        msg = f"Interface {LOOPBACK_NAME} already exists"
        print(msg)
        return msg

    netconf_config = f"""\
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{LOOPBACK_NAME}</name>
      <description>{LOOPBACK_NAME} created via NETCONF</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:softwareLoopback</type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address>
          <ip>{LOOPBACK_IP}</ip>
          <netmask>255.255.255.0</netmask>
        </address>
      </ipv4>
    </interface>
  </interfaces>
</config>"""

    try:
        netconf_reply = netconf_edit_config(netconf_config)
        xml_data = netconf_reply.xml
        print(xml_data)
        if '<ok/>' in xml_data:
            success_msg = f"Interface {LOOPBACK_NAME} created successfully"
            return success_msg
        fail_msg = f"Failed to create interface {LOOPBACK_NAME}"
        print(fail_msg)
        return fail_msg
    except Exception as e:
        err = f"Cannot create: {LOOPBACK_NAME} ({e})"
        print(err)
        return err


def interface_exists(name):
    filt = f"""
<filter>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{name}</name>
    </interface>
  </interfaces>
</filter>"""
    try:
        reply = m.get_config(source="running", filter=filt)
        data = xmltodict.parse(reply.xml)
        interfaces = data.get('rpc-reply', {}).get('data', {}).get('interfaces')
        if interfaces and interfaces.get('interface'):
            intf = interfaces['interface']
            if isinstance(intf, list):
                return any(i.get('name') == name for i in intf)
            # IOS XE often wraps name as dict {'#text': value}
            nm = intf.get('name')
            if isinstance(nm, dict):
                return nm.get('#text') == name
            return nm == name
        return False
    except Exception:
        return False

def delete():
    if not interface_exists(LOOPBACK_NAME):
        return f"Interface {LOOPBACK_NAME} does not exist"

    netconf_config = f"""\
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="delete">
      <name>{LOOPBACK_NAME}</name>
    </interface>
  </interfaces>
</config>"""

    try:
        netconf_reply = netconf_edit_config(netconf_config)
        xml_data = netconf_reply.xml
        print(xml_data)
        if '<ok/>' in xml_data:
            return f"Interface {LOOPBACK_NAME} deleted successfully"
        return f"Failed to delete interface {LOOPBACK_NAME}"
    except Exception as e:
        print(f"Error: {e}")
        return f"Error deleting interface {LOOPBACK_NAME}: {e}"


def enable():
    if not interface_exists(LOOPBACK_NAME):
        return f"Interface {LOOPBACK_NAME} does not exist"

    # Check current enabled state
    filt = f"""
<filter>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{LOOPBACK_NAME}</name>
      <enabled/>
    </interface>
  </interfaces>
</filter>"""
    try:
        reply = m.get_config(source="running", filter=filt)
        data = xmltodict.parse(reply.xml)
        intf = (data.get('rpc-reply', {})
                    .get('data', {})
                    .get('interfaces', {})
                    .get('interface'))
        if intf:
            enabled_val = intf.get('enabled')
            if isinstance(enabled_val, dict):
                enabled_val = enabled_val.get('#text')
            # If enabled element absent (None) default is true per YANG model
            if enabled_val in (True, 'true', 'True', None):
                return f"Interface {LOOPBACK_NAME} already enabled"

        netconf_config = f"""\
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{LOOPBACK_NAME}</name>
      <enabled>true</enabled>
    </interface>
  </interfaces>
</config>"""
        netconf_reply = netconf_edit_config(netconf_config)
        xml_data = netconf_reply.xml
        print(xml_data)
        if '<ok/>' in xml_data:
            return f"Interface {LOOPBACK_NAME} enabled"
        return f"Failed to enable interface {LOOPBACK_NAME}"
    except Exception as e:
        print(f"Error enabling: {e}")
        return f"Error enabling interface {LOOPBACK_NAME}: {e}"


def disable():
    if not interface_exists(LOOPBACK_NAME):
        return f"Interface {LOOPBACK_NAME} does not exist"

    # Get current enabled state
    filt = f"""
<filter>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{LOOPBACK_NAME}</name>
      <enabled/>
    </interface>
  </interfaces>
</filter>"""
    try:
        reply = m.get_config(source="running", filter=filt)
        data = xmltodict.parse(reply.xml)
        intf = (data.get('rpc-reply', {})
                    .get('data', {})
                    .get('interfaces', {})
                    .get('interface'))
        if intf:
            enabled_val = intf.get('enabled')
            if isinstance(enabled_val, dict):
                enabled_val = enabled_val.get('#text')
            # If explicitly false -> already disabled
            if enabled_val in (False, 'false', 'False'):
                return f"Interface {LOOPBACK_NAME} already disabled"

        netconf_config = f"""\
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{LOOPBACK_NAME}</name>
      <enabled>false</enabled>
    </interface>
  </interfaces>
</config>"""
        netconf_reply = netconf_edit_config(netconf_config)
        xml_data = netconf_reply.xml
        print(xml_data)
        if '<ok/>' in xml_data:
            return f"Interface {LOOPBACK_NAME} disabled"
        return f"Failed to disable interface {LOOPBACK_NAME}"
    except Exception as e:
        print(f"Error disabling: {e}")
        return f"Error disabling interface {LOOPBACK_NAME}: {e}"

def netconf_edit_config(netconf_config):
    return  m.edit_config(target="running", config=netconf_config)


def status():
    # NETCONF <get> (operational) filter for the specific loopback
    netconf_filter = f"""
<filter>
  <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>{LOOPBACK_NAME}</name>
      <admin-status/>
      <oper-status/>
    </interface>
  </interfaces-state>
</filter>""".strip()

    try:
        reply = m.get(filter=netconf_filter)
        data = xmltodict.parse(reply.xml)

        d = data.get('rpc-reply', {}).get('data', {})
        if not d:
            return f"No operational data returned for {LOOPBACK_NAME}"

        istate = d.get('interfaces-state', {}).get('interface')
        if not istate:
            return f"Interface {LOOPBACK_NAME} not found"

        # If multiple interfaces returned
        if isinstance(istate, list):
            def _nm(x):
                n = x.get('name')
                if isinstance(n, dict):
                    return n.get('#text')
                return n
            istate = next((i for i in istate if _nm(i) == LOOPBACK_NAME), None)
            if not istate:
                return f"Interface {LOOPBACK_NAME} not found"

        # Extract name (normalize)
        name_val = istate.get('name')
        if isinstance(name_val, dict):
            name_val = name_val.get('#text')

        admin = istate.get('admin-status')
        oper = istate.get('oper-status')

        if admin is None and oper is None:
            return f"Operational status fields missing for {LOOPBACK_NAME}"

        if admin == 'up' and oper == 'up':
            return f"Interface {name_val} is up (admin up / oper up)"
        if admin == 'down' and oper == 'down':
            return f"Interface {name_val} is down (admin down / oper down)"
        return f"Interface {name_val} admin={admin} oper={oper}"
    except Exception as e:
        return f"Error fetching status for {LOOPBACK_NAME}: {e}"
