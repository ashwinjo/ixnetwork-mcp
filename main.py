from mcp.server.fastmcp import FastMCP
import os
from ixnetwork_restpy import SessionAssistant, Files
from typing import List, Tuple
import json
import logging
import sys
import functools


from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ixnetwork_mcp.log')
    ]
)
logger = logging.getLogger('ixnetwork-mcp')

# Initialize the MCP server with logging options
logger.info("Initializing IxNetwork MCP server")
mcp = FastMCP("ixnetwork-session-manager")
USER_AGENT = "ixnetwork-session-manager/1.0"

# Create a decorator for logging tool calls
def log_tool(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Tool called: {func.__name__} with args: {kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"Tool completed: {func.__name__}")
        return result
    return wrapper

# Load configuration from file
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ixnetwork_config.json")
    logger.info(f"Loading configuration from {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)
        logger.info(f"Configuration loaded with {len(config)} IP addresses")
        return config

# Global configuration
CONFIG = load_config()
DEFAULT_IP = "10.36.236.121"  # Default IxNetwork server IP

def get_credentials(ip_address=DEFAULT_IP):
    """Get credentials for the specified IP address from the config file"""
    logger.debug(f"Getting credentials for IP: {ip_address}")
    if ip_address in CONFIG:
        return CONFIG[ip_address]["username"], CONFIG[ip_address]["password"]
    error_msg = f"IP address {ip_address} not found in configuration"
    logger.error(error_msg)
    raise ValueError(error_msg)

def get_session_assistant(ip_address=DEFAULT_IP, session_id=None, session_name=None):
    """
    This method creates a session assistant for the given IP address, session ID or session_name
    We will create a new session if session_id or session_name is not provided

    Inputs:
        ip_address: str
        session_id: str
        session_name: str

    Returns:
        session_Assistant: SessionAssistant
    """
    logger.info(f"Creating session assistant - IP: {ip_address}, Session ID: {session_id}, Session Name: {session_name}")
    username, password = get_credentials(ip_address)
    
    session_assistant = SessionAssistant(
            IpAddress=ip_address,
            RestPort=443,
            UserName=username,
            Password=password,
            SessionName=session_name,
            SessionId=session_id,
            LogLevel=SessionAssistant.LOGLEVEL_INFO,
            ClearConfig=False
        )
    logger.info(f"Session assistant created successfully")
    return session_assistant


@mcp.tool()
@log_tool
def get_ixnetwork_sessions():
    """
    This method lists all the sessions on the IXNetwork API.
    Inputs:
        None
    Returns:
        List of sessions on the IXNetwork API.
        
    """
    logger.info("Getting IxNetwork sessions")
    from ixnetwork_restpy.testplatform.testplatform import TestPlatform
    ip_address = DEFAULT_IP
    username, password = get_credentials(ip_address)
    
    test_platform = TestPlatform(ip_address)
    assert test_platform.Platform == "linux"
    test_platform.Trace = "request_response"

    # authenticate with username and password
    test_platform.Authenticate(username, password)
    # get a list of sessions
    session_list = []
    for session in test_platform.Sessions.find():
        session_info = {"session_id": session.Id, "session_name": session.Name, "session_type": session.UserName}
        session_list.append(session_info)
        logger.info(f"Found session: {session_info}")
    logger.info(f"Total sessions found: {len(session_list)}")
    return json.dumps(session_list)

@mcp.tool()
@log_tool
def get_ixnetwork_session_details(session_id: str):
    """
    Get the sessionID details from the IxNetwork API.
    Inputs:
        session_id: str
    Returns:
        session_details: str
    """
    logger.info(f"Getting details for session ID: {session_id}")
    session_assistant = get_session_assistant(session_id=session_id)
    session_details = str(session_assistant.Session)
    logger.info(f"Session details retrieved successfully")
    return session_details

@mcp.tool()
@log_tool
def delete_ixnetwork_session(session_id: str):
    """
    Delete the sessionID from the IXNetwork API.
    Inputs:
        session_id: str
    Returns:
        session_info_that_is_deleted: str
    """
    logger.info(f"Deleting session ID: {session_id}")
    session_assistant = get_session_assistant(session_id=session_id)
    session_info_that_is_deleted = session_assistant.Session.remove()
    logger.info(f"Session deleted successfully")
    return str(session_info_that_is_deleted)
 

@mcp.tool()
@log_tool
def create_ixnetwork_session():
    """
    Create a new new IxNetwork Session on mentioned API Server
    Inputs:
        None
    Returns:
        session_assistant: SessionAssistant
    """
    logger.info(f"Creating new IxNetwork session")
    session_assistant = get_session_assistant()
    session_info = str(session_assistant.Session)
    logger.info(f"New session created: {session_info}")
    return session_info


@mcp.tool()
@log_tool
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
        logger.error("Configuration directory not found")
        return "Configuration directory not found"
        
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    # Load the specified configuration file if provided
    if ixnetwork_file_path:
        config_path = os.path.join(config_dir, ixnetwork_file_path)
        if not os.path.exists(config_path):
            logger.error(f"Configuration file {ixnetwork_file_path} not found")
            return f"Configuration file {ixnetwork_file_path} not found"
        logger.info(f"Loading configuration file: {ixnetwork_file_path}")
        session_assistant.Ixnetwork.LoadConfig(Files(config_path))
        logger.info(f"Configuration file loaded successfully")

    return f"Configuration file {ixnetwork_file_path} loaded successfully"


@mcp.tool()
@log_tool
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
    logger.info(f"Connecting ports: {portList}")
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    portMap = session_assistant.PortMapAssistant()
    vport = dict()
    for index,port in enumerate(portList):
        # For the port name, get the loaded configuration's port name
        portName = session_assistant.Ixnetwork.Vport.find()[index].Name
        logger.info(f"Mapping port: {port} to vport: {portName}")
        portMap.Map(IpAddress=port[0], CardId=port[1], PortId=port[2], Name=portName)
        
    #portMap.Connect(True)
    logger.info("Ports connected successfully")
    return portMap

@mcp.tool()
@log_tool
def start_ixnetwork_protocol(session_id: str=None, session_name: str=None):
    """
    Start the IxNetwork Protocols in the test.
    Inputs:
        session_id: str
        session_name: str
    
    Returns:
        start_ixnetwork_protocol_success_message: str
    """
    logger.info(f"Starting protocols - Session ID: {session_id}, Session Name: {session_name}")
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    session_assistant.Ixnetwork.StartAllProtocols(Arg1='sync')

    session_assistant.Ixnetwork.info('Verify protocol sessions\n')
    protocolSummary = session_assistant.StatViewAssistant('Protocols Summary')
    protocolSummary.CheckCondition('Sessions Not Started', protocolSummary.EQUAL, 0)
    protocolSummary.CheckCondition('Sessions Down', protocolSummary.EQUAL, 0)
    session_assistant.Ixnetwork.info(protocolSummary)
    logger.info("Protocols started successfully")
    return "Protocols started successfully"

@mcp.tool()
@log_tool
def stop_ixnetwork_protocol(session_id: str=None, session_name: str=None):
    """
    Stop the IxNetwork Protocols in the test.
    Inputs:
        session_id: str
        session_name: str
    
    Returns:
        start_ixnetwork_protocol_success_message: str
    """
    logger.info(f"Stopping protocols - Session ID: {session_id}, Session Name: {session_name}")
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    session_assistant.Ixnetwork.StopAllProtocols(Arg1='sync')
    logger.info("Protocols stopped successfully")
    return "Protocols stopped successfully"

@mcp.tool()
@log_tool
def get_traffic_items(session_id: str=None, session_name: str=None):
    """
    Get the traffic items in the test.
    Inputs:
        session_id: str
        session_name: str
    """
    logger.info(f"Getting traffic items - Session ID: {session_id}, Session Name: {session_name}")
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    traffic_items = session_assistant.Ixnetwork.Traffic.TrafficItem.find()
    traffic_items_list = [{"name": item.Name, "enabled": item.Enabled} for item in traffic_items]
    logger.info(f"Found {len(traffic_items_list)} traffic items")
    return json.dumps(traffic_items_list)

@mcp.tool()
@log_tool
def start_traffic_item(session_id: str=None, session_name: str=None, traffic_item_name: str=None):
    """
    Start the traffic item in the test.
    Inputs:
        session_id: str
        session_name: str
        traffic_item_name: str
    """
    logger.info(f"Starting traffic - Session ID: {session_id}, Session Name: {session_name}, Traffic Item: {traffic_item_name}")
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    if traffic_item_name:
        traffic_items = session_assistant.Ixnetwork.Traffic.TrafficItem.find(Name=traffic_item_name)
        if traffic_items:
            traffic_items.StartStatelessTraffic()
            logger.info(f"Traffic item '{traffic_item_name}' started successfully")
            return f"Traffic item '{traffic_item_name}' started successfully"
        logger.warning(f"Traffic item '{traffic_item_name}' not found")
        return f"Traffic item '{traffic_item_name}' not found"
    else:
        session_assistant.Ixnetwork.Traffic.StartStatelessTrafficBlocking()
        logger.info("All traffic items started successfully")
        return "All traffic items started successfully"

@mcp.tool()
@log_tool
def stop_traffic_item(session_id: str=None, session_name: str=None):
    """
    Start the traffic item in the test.
    Inputs:
        session_id: str
        session_name: str
        traffic_item_name: str
    """
    logger.info(f"Stopping traffic - Session ID: {session_id}, Session Name: {session_name}")
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    session_assistant.Ixnetwork.Traffic.StopStatelessTrafficBlocking()
    logger.info("Traffic stopped successfully")
    return "Traffic stopped successfully"

@mcp.tool()
@log_tool
def get_traffic_statistics(session_id: str=None, session_name: str=None):
    """
    Get traffic statistics in a formatted table.
    Inputs:
        session_id: str
        session_name: str
    Returns:
        A formatted table of traffic statistics
    """
    logger.info(f"Getting traffic statistics - Session ID: {session_id}, Session Name: {session_name}")
    session_assistant = get_session_assistant(session_id=session_id, session_name=session_name)
    traffic_stats = session_assistant.StatViewAssistant('Traffic Item Statistics')
    logger.info("Traffic statistics retrieved successfully")
    return traffic_stats.to_string()


if __name__ == "__main__":
    logger.info("Starting IxNetwork MCP server")
    mcp.run()
    logger.info("IxNetwork MCP server stopped")