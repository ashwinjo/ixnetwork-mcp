"""
Author: Ashwin Joshi
Date: April 2025

Description:
This script serves as an MCP (Message Communication Protocol) server for IxNetwork session management.
It provides functionality to create, manage, and interact with IxNetwork test sessions through a REST API interface.
The server handles session creation, configuration management, and test execution while maintaining
session persistence and proper resource cleanup.
"""

from mcp.server.fastmcp import FastMCP
import os
from ixnetwork_restpy.testplatform.testplatform import TestPlatform
from ixnetwork_restpy import SessionAssistant, Files
from typing import List, Tuple  # Update this line
import json
import logging

from dotenv import load_dotenv
load_dotenv()

# --- Basic Logging Setup ---
# Add thread name to logging format
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("IxNetworkMCPServer")


# Initialize the MCP server
mcp = FastMCP("ixnetwork-session-manager")
USER_AGENT = "ixnetwork-session-manager/1.0"


def get_session_assistant(session_id: str=None, session_name: str=None):
    """
    This method creates a session assistant for the given session ID or session_name provided
    We will create a new session if session_id or session_name is not provided

    Inputs:
        session_id: str
        session_name: str

    Returns:
        session_Assistant: SessionAssistant
    """
    
    session_assistant = SessionAssistant(
            IpAddress="10.36.236.121",  # Replace with your IxNetwork server IP
            RestPort=443,         # Replace with the appropriate REST port
            UserName="admin",
            Password="XXXXXXX",
            SessionName=session_name,
            SessionId=session_id,
            LogLevel=SessionAssistant.LOGLEVEL_INFO,
            ClearConfig=False
        )
    return session_assistant


@mcp.tool()
def get_ixnetwork_sessions():
    """
    Shows a list of all IxNetwork Sessions on the IXNetwork API.
    Inputs:
        None
    Returns:
        List of sessions on the IXNetwork API.
        
    """
    test_platform = TestPlatform("10.36.236.121")
    assert test_platform.Platform == "linux"
    test_platform.Trace = "request_response"

    # authenticate with username and password
    test_platform.Authenticate("admin", "Kimchi123Kimchi123!")
    # get a list of sessions
    session_list = []
    for session in test_platform.Sessions.find():
        session_list.append({"session_id": session.Id, "session_name": session.Name, "session_type": session.UserName})
        import json
    return json.dumps(session_list)

@mcp.tool()
def get_ixnetwork_session_details(session_id: str):
    """
    Get the sessionID details from the IxNetwork API.
    Inputs:
        session_id: str
    Returns:
        session_details: str
    """
    session_assistant = get_session_assistant(session_id=session_id)
    return str(session_assistant.Session)

@mcp.tool()
def delete_ixnetwork_session(session_id: str):
    """
    Delete the sessionID from the IXNetwork API.
    Inputs:
        session_id: str
    Returns:
        session_info_that_is_deleted: str
    """
    session_assistant = get_session_assistant(session_id=session_id)
    session_info_that_is_deleted = session_assistant.Session.remove()
    return str(session_info_that_is_deleted)
 

@mcp.tool()
def create_ixnetwork_session():
    """
    Create a new new IxNetwork Session on mentioned API Server
    Inputs:
        None
    Returns:
        session_assistant: SessionAssistant
    """
    session_assistant = get_session_assistant()
    return str(session_assistant.Session)


@mcp.tool()
def load_configuration_file(session_id: str=None, session_name: str=None, ixnetwork_file_path:str=None):
    """
    Load a configuration file into the IxNetwork session.
    Inputs:
        session_id: str
        session_name: str
        ixnetwork_file_path: str
    Returns:
        config_file_success_message: str
    """
    # Get all configuration files from the ixia_configuration_files directory
    config_dir = os.path.abspath("ixia_configuration_files")
    if not os.path.exists(config_dir):
        return "Configuration directory not found"
        
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    # Load the specified configuration file if provided
    if ixnetwork_file_path:
        config_path = os.path.join(config_dir, ixnetwork_file_path)
        if not os.path.exists(config_path):
            return f"Configuration file {ixnetwork_file_path} not found"
        session_assistant.Ixnetwork.LoadConfig(Files(config_path))

    return f"Configuration file {ixnetwork_file_path} loaded successfully"


@mcp.tool()
def connect_ports(session_id: str=None, session_name: str=None, portList:List[Tuple[str, str, str]]=None):
    """
    Connect the ports in the IxNetwork session.
    Method accepts a list of ports in the format of [(ip_address, card_id, port_id)]
    Inputs:
        session_id: str
        session_name: str
        portList: List[Tuple[str, str, str]] # Example: [('10.36.236.121', '1', '1'), ('10.36.236.121', '1', '2')]
    Returns:
        connect_ports_success_message: str
    """
    # Assign ports. Map physical ports to the configured vports.
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    portMap = session_assistant.PortMapAssistant()
    vport = dict()
    for index,port in enumerate(portList):
        # For the port name, get the loaded configuration's port name
        portName = session_assistant.Ixnetwork.Vport.find()[index].Name
        portMap.Map(IpAddress=port[0], CardId=port[1], PortId=port[2], Name=portName)
        
    portMap.Connect(True)
    return portMap

@mcp.tool()
def start_ixnetwork_protocol(session_id: str=None, session_name: str=None):
    """
    Start the IxNetwork Protocols in the test.
    Inputs:
        session_id: str
        session_name: str
    
    Returns:
        start_ixnetwork_protocol_success_message: str
    """
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    session_assistant.Ixnetwork.StartAllProtocols(Arg1='sync')

    session_assistant.Ixnetwork.info('Verify protocol sessions\n')
    protocolSummary = session_assistant.StatViewAssistant('Protocols Summary')
    protocolSummary.CheckCondition('Sessions Not Started', protocolSummary.EQUAL, 0)
    protocolSummary.CheckCondition('Sessions Down', protocolSummary.EQUAL, 0)
    session_assistant.Ixnetwork.info(protocolSummary)
    return "Protocols started successfully"

@mcp.tool()
def stop_ixnetwork_protocol(session_id: str=None, session_name: str=None):
    """
    Stop the IxNetwork Protocols in the test.
    Inputs:
        session_id: str
        session_name: str
    
    Returns:
        start_ixnetwork_protocol_success_message: str
    """
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    session_assistant.Ixnetwork.StopAllProtocols(Arg1='sync')
    return "Protocols stopped successfully"

@mcp.tool()
def get_traffic_items(session_id: str=None, session_name: str=None):
    """
    Get the traffic items in the test.
    Inputs:
        session_id: str
        session_name: str
    """
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    # Get the Traffic Item name for getting Traffic Item statistics.
    trafficItems = session_assistant.Ixnetwork.Traffic.TrafficItem.find()
    return trafficItems

@mcp.tool()
def start_traffic_item(session_id: str=None, session_name: str=None, traffic_item_name: str=None):
    """
    Start the traffic item in the test.
    Inputs:
        session_id: str
        session_name: str
        traffic_item_name: str
    """
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    
    trafficItem = session_assistant.Ixnetwork.Traffic.TrafficItem.find(Name=traffic_item_name)
    trafficItem.Generate()
    session_assistant.Ixnetwork.Traffic.Apply()
    session_assistant.Ixnetwork.Traffic.StartStatelessTrafficBlocking()
    return f"Traffic item {traffic_item_name} started successfully"


@mcp.tool()
def stop_traffic_item(session_id: str=None, session_name: str=None):
    """
    Start the traffic item in the test.
    Inputs:
        session_id: str
        session_name: str
        traffic_item_name: str
    """
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    session_assistant.Ixnetwork.Traffic.StopStatelessTrafficBlocking()
    return f"All Traffic items stopped successfully"


@mcp.tool()
def get_traffic_statistics(session_id: str=None, session_name: str=None):
    """
    Get traffic statistics in a formatted table.
    Inputs:
        session_id: str
        session_name: str
    Returns:
        A formatted table of traffic statistics
    """
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    flowStatistics = session_assistant.StatViewAssistant('Flow Statistics')
    
    # Create table data
    table_data = {
        "headers": ['Tx Port', 'Rx Port', 'Loss %', 'Tx Frames', 'Rx Frames'],
        "rows": []
    }
    
    for flowStat in flowStatistics.Rows:
        table_data["rows"].append({
            "Tx Port": flowStat['Tx Port'],
            "Rx Port": flowStat['Rx Port'],
            "Loss %": flowStat['Loss %'],
            "Tx Frames": flowStat['Tx Frames'],
            "Rx Frames": flowStat['Rx Frames']
        })
    
    return json.dumps(table_data)

if __name__ == "__main__":
    mcp.run(transport="stdio")
