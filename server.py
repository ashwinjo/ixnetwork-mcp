from mcp.server.fastmcp import FastMCP
import os
from ixnetwork_restpy import SessionAssistant, Files
from ixnetwork_restpy.testplatform.testplatform import TestPlatform
from typing import Dict, List, Optional, Any, Union, Tuple
import json
import logging
import sys
import time
import functools
import traceback

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('ixnetwork-mcp')

# Initialize the MCP server with logging options
logger.info("Initializing IxNetwork MCP server")
mcp = FastMCP("ixnetwork-session-manager")
USER_AGENT = "ixnetwork-session-manager/1.0"

# Create a decorator for logging tool calls
def log_tool(func):
    """Decorator to log the entry, exit, and exceptions of a function call.

    Args:
        func (Callable): The function to be wrapped.

    Returns:
        Callable: The wrapped function with logging.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Tool called: {func.__name__} with args: {kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"Tool completed: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Tool {func.__name__} failed with error: {str(e)}")
            logger.error(traceback.format_exc())
            raise e
    return wrapper

# Load configuration from file
def load_config():
    """Load the IxNetwork configuration from a JSON file.

    Returns:
        dict: Configuration dictionary mapping IPs to credentials.
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ixnetwork_config.json")
    logger.info(f"Loading configuration from {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.info(f"Configuration loaded with {len(config)} IP addresses")
            # Log the available IPs for debugging
            logger.info(f"Available IPs in config: {list(config.keys())}")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a default config with hardcoded credentials as fallback
        default_config = {
            "10.36.236.121": {
                "username": "admin",
                "password": "Kimchi123Kimchi123!"
            }
        }
        logger.info("Using default configuration")
        return default_config

# Global configuration
CONFIG = load_config()
DEFAULT_IP = "10.36.236.121"  # Default IxNetwork server IP

def get_credentials(ip_address=DEFAULT_IP):
    """Get credentials for the specified IP address from the config file.

    Args:
        ip_address (str): The IP address to retrieve credentials for.

    Returns:
        Tuple[str, str]: Username and password for the IP address.
    """
    logger.info(f"Getting credentials for IP: {ip_address}")
    if ip_address in CONFIG:
        username = CONFIG[ip_address]["username"]
        password = CONFIG[ip_address]["password"]
        # Log partial password for debugging (showing only first two chars)
        masked_password = password[:2] + '*' * (len(password) - 2) if len(password) > 2 else '***'
        logger.info(f"Retrieved credentials - Username: {username}, Password: {masked_password}")
        return username, password
    
    error_msg = f"IP address {ip_address} not found in configuration"
    logger.error(error_msg)
    logger.error(f"Available IPs in config: {list(CONFIG.keys())}")
    
    # Fallback to default credentials if IP not found
    logger.info("Using default credentials")
    return "admin", "Kimchi123Kimchi123!"


def get_session_assistant(api_server_ip: str, session_id: Optional[str] = None, session_name: Optional[str] = None) -> SessionAssistant:
    """Create a session assistant for the given chassis IP, session ID, or session name.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (Optional[str]): Session ID to connect to.
        session_name (Optional[str]): Name of the session to create/connect.

    Returns:
        SessionAssistant: The session assistant object.

    Raises:
        Exception: If session creation fails.
    """
    logger.info(f"Creating session assistant - Chassis IP: {api_server_ip}, Session ID: {session_id}, Session Name: {session_name}")
    username, password = get_credentials(ip_address=api_server_ip)
    try:
        session_assistant = SessionAssistant(
            IpAddress=api_server_ip,
            RestPort=443,
            UserName=username,
            Password=password,
            SessionName=session_name,
            SessionId=session_id,
            LogLevel=SessionAssistant.LOGLEVEL_INFO,                
            ClearConfig=False,
        )
        logger.info(f"Session assistant created successfully")
        return session_assistant
    except Exception as e:
        logger.error(f"Failed to create session assistant: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@mcp.tool()
def get_sessions(api_server_ip: str) -> str:
    """List all sessions on the IxNetwork chassis.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.

    Returns:
        str: JSON string of session list.
    """
    logger.info(f"Getting sessions for chassis {api_server_ip}")
    
    try:
        test_platform = TestPlatform(api_server_ip, rest_port=443)
        username, password = get_credentials(ip_address=api_server_ip)
        test_platform.Authenticate(username, password)
        
        session_list: List[Dict[str, str]] = []
        for session in test_platform.Sessions.find():
            session_info = {
                "session_id": session.Id, 
                "session_name": session.Name, 
                "session_type": session.UserName
            }
            session_list.append(session_info)
            logger.info(f"Found session: {session_info}")
            
        logger.info(f"Total sessions found: {len(session_list)}")
        return json.dumps(session_list)
    except Exception as e:
        error_msg = f"Failed to get sessions: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def create_session(api_server_ip: str, session_name: Optional[str] = None) -> str:
    """Create a new IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_name (Optional[str]): Name for the new session.

    Returns:
        str: Session information in JSON format.
    """
    logger.info(f"Creating new session on chassis {api_server_ip}")
    
    try:
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_name=session_name)
        session_info = {
            "session_id": session_assistant.Session.Id,
            "session_name": session_assistant.Session.Name
        }
        logger.info(f"New session created: {session_info}")
        return json.dumps(session_info)
    except Exception as e:
        error_msg = f"Failed to create session: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def delete_ixnetwork_session(api_server_ip: str, session_id: str) -> str:
    """Delete an IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (str): ID of the session to delete.

    Returns:
        str: Result of deletion in JSON format.
    """
    logger.info(f"Deleting session {session_id} on chassis {api_server_ip}")
    
    try:
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_id=session_id)
        result = session_assistant.Session.remove()
        logger.info(f"Session deleted successfully")
        return json.dumps({"result": "success", "message": f"Session {session_id} deleted"})
    except Exception as e:
        error_msg = f"Failed to delete session: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def load_ixnetwork_config(api_server_ip: str, session_id: str, ixia_config_file: str) -> str:
    """Load a configuration file into an IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (str): ID of the session.
        ixia_config_file (str): Path to the ixia configuration file.

    Returns:
        str: Result of loading configuration in JSON format.
    """
    logger.info(f"Loading configuration {ixia_config_file} to session {session_id} on chassis {api_server_ip}")
    
    try:
        # Check if file exists
        config_path = "/Users/ashwjosh/ixnetwork-mcp/ixia_configuration_files/" + ixia_config_file
        if not os.path.exists(config_path):
            return json.dumps({"error": f"Configuration file {ixia_config_file} not found"})
            
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_id=session_id)
        session_assistant.Ixnetwork.LoadConfig(Files(config_path))
        logger.info(f"Configuration loaded successfully")
        return json.dumps({"result": "success", "message": f"Configuration {ixia_config_file} loaded"})
    except Exception as e:
        error_msg = f"Failed to load configuration: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def connect_ports(api_server_ip: str, session_id: str, port_list: List[Tuple[str, str, str]]) -> str:
    """Connect ports to an IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (str): ID of the session.
        port_list (List[Tuple[str, str, str]]): List of ports to connect [(chassis_ip, card, port), ...].

    Returns:
        str: Result of connecting ports in JSON format.
    """
    logger.info(f"Connecting ports {port_list} to session {session_id} on chassis {api_server_ip}")
    
    try:
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_id=session_id)
        port_map = session_assistant.PortMapAssistant()
        
        vports = session_assistant.Ixnetwork.Vport.find()
        if not vports:
            return json.dumps({"error": "No vports found in configuration"})
            
        for index, port in enumerate(port_list):
            if index >= len(vports):
                break
                
            port_name = vports[index].Name
            port_map.Map(
                IpAddress=port[0], 
                CardId=port[1], 
                PortId=port[2], 
                Name=port_name
            )
            logger.info(f"Mapped port {port} to vport {port_name}")
            
        port_map.Connect()
        logger.info("Ports connected successfully")
        return json.dumps({"result": "success", "message": "Ports connected successfully"})
    except Exception as e:
        error_msg = f"Failed to connect ports: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def start_protocols(api_server_ip: str, session_id: str) -> str:
    """Start all protocols in an IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (str): ID of the session.

    Returns:
        str: Result of starting protocols in JSON format.
    """
    logger.info(f"Starting protocols in session {session_id} on chassis {api_server_ip}")
    
    try:
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_id=session_id)
        session_assistant.Ixnetwork.StartAllProtocols(Arg1='sync')
        time.sleep(30)  # Wait for protocols to stabilize
        # Verify protocols started successfully
        protocol_summary = session_assistant.StatViewAssistant('Protocols Summary')
        not_started = protocol_summary.Rows[0]['Sessions Not Started']
        down = protocol_summary.Rows[0]['Sessions Down']
        
        if int(not_started) > 0 or int(down) > 0:
            logger.warning(f"Some protocols failed to start: Not Started={not_started}, Down={down}")
            return json.dumps({
                "result": "warning", 
                "message": f"Some protocols may not have started: Not Started={not_started}, Down={down}"
            })
            
        logger.info("Protocols started successfully")
        return json.dumps({"result": "success", "message": "Protocols started successfully"})
    except Exception as e:
        error_msg = f"Failed to start protocols: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def stop_protocols(api_server_ip: str, session_id: str) -> str:
    """Stop all protocols in an IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (str): ID of the session.

    Returns:
        str: Result of stopping protocols in JSON format.
    """
    logger.info(f"Stopping protocols in session {session_id} on chassis {api_server_ip}")
    
    try:
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_id=session_id)
        session_assistant.Ixnetwork.StopAllProtocols(Arg1='sync')
        logger.info("Protocols stopped successfully")
        return json.dumps({"result": "success", "message": "Protocols stopped successfully"})
    except Exception as e:
        error_msg = f"Failed to stop protocols: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def start_traffic(api_server_ip: str, session_id: str, traffic_item_name: Optional[str] = None) -> str:
    """Start traffic in an IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (str): ID of the session.
        traffic_item_name (Optional[str]): Name of specific traffic item to start.

    Returns:
        str: Result of starting traffic in JSON format.
    """
    logger.info(f"Starting traffic in session {session_id} on chassis {api_server_ip}")
    
    try:
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_id=session_id)
        
        if traffic_item_name:
            # Start specific traffic item
            traffic_items = session_assistant.Ixnetwork.Traffic.TrafficItem.find(Name=traffic_item_name)
            if not traffic_items:
                return json.dumps({"error": f"Traffic item '{traffic_item_name}' not found"})
            
            traffic_items.Generate()
            session_assistant.Ixnetwork.Traffic.Apply()
            traffic_items.StartStatelessTraffic()
            logger.info(f"Traffic item '{traffic_item_name}' started successfully")
            return json.dumps({"result": "success", "message": f"Traffic item '{traffic_item_name}' started"})
        else:
            # Start all traffic
            traffic_items = session_assistant.Ixnetwork.Traffic.TrafficItem.find()
            traffic_items.Generate()
            session_assistant.Ixnetwork.Traffic.Apply()
            session_assistant.Ixnetwork.Traffic.StartStatelessTrafficBlocking()
            logger.info("All traffic started successfully")
            return json.dumps({"result": "success", "message": "All traffic started successfully"})
    except Exception as e:
        error_msg = f"Failed to start traffic: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def stop_traffic(api_server_ip: str, session_id: str) -> str:
    """Stop traffic in an IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (str): ID of the session.

    Returns:
        str: Result of stopping traffic in JSON format.
    """
    logger.info(f"Stopping traffic in session {session_id} on chassis {api_server_ip}")
    
    try:
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_id=session_id)
        session_assistant.Ixnetwork.Traffic.StopStatelessTrafficBlocking()
        logger.info("Traffic stopped successfully")
        return json.dumps({"result": "success", "message": "Traffic stopped successfully"})
    except Exception as e:
        error_msg = f"Failed to stop traffic: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def get_traffic_stats(api_server_ip: str, session_id: str, statistics_name: Optional[str] = None) -> str:
    """Get traffic statistics from an IxNetwork session.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.
        session_id (str): ID of the session.
        statistics_name (Optional[str]): Name of the statistics view to retrieve.

    Returns:
        str: Traffic statistics in JSON format.
    """
    logger.info(f"Getting traffic statistics for session {session_id} on chassis {api_server_ip}")
    
    try:
        session_assistant = get_session_assistant(api_server_ip=api_server_ip, session_id=session_id)
        traffic_stats = session_assistant.StatViewAssistant(statistics_name)
        # Convert to dict for JSON serialization
        stats_data: List[Dict[str, Any]] = []
        for row in traffic_stats.Rows:
            row_dict = {}
            for column_name in traffic_stats.ColumnHeaders:
                row_dict[column_name] = row[column_name]
            stats_data.append(row_dict)
            
        logger.info("Traffic statistics retrieved successfully")
        return json.dumps({"result": "success", "statistics": stats_data})
    except Exception as e:
        error_msg = f"Failed to get traffic statistics: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({"error": error_msg})

@mcp.tool()
def test_connection(api_server_ip: str) -> str:
    """Test connection to IxNetwork chassis.

    Args:
        api_server_ip (str): IP address of the IxNetwork chassis.

    Returns:
        str: Connection test result in JSON format.
    """
    logger.info(f"Testing connection to chassis {api_server_ip}")
    
    try:
        test_platform = TestPlatform(api_server_ip, rest_port=443, verify=False)
        platform_type = test_platform.Platform
        
        test_platform.Authenticate(DEFAULT_USERNAME, DEFAULT_PASSWORD)
        api_version = test_platform.ApiServerVersion
        
        connection_status: Dict[str, str] = {
            "result": "success",
            "platform": platform_type,
            "ip": api_server_ip,
            "api_version": api_version,
            "message": "Successfully connected to IxNetwork chassis"
        }
        logger.info(f"Connection test successful: {connection_status}")
        return json.dumps(connection_status)
    except Exception as e:
        error_msg = f"Failed to connect to chassis {api_server_ip}: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return json.dumps({
            "result": "error",
            "ip": api_server_ip,
            "error": str(e),
            "message": error_msg
        })

@mcp.tool()
def update_credentials(ip_address, username, password):
    """Update credentials for an IP address in the config.

    Args:
        ip_address (str): The IP address to update.
        username (str): The username to set.
        password (str): The password to set.

    Returns:
        str: Status message indicating success or failure.
    """
    logger.info(f"Updating credentials for IP: {ip_address}")
    
    # Update in-memory config
    CONFIG[ip_address] = {
        "username": username,
        "password": password
    }
    
    # Update the config file
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ixnetwork_config.json")
        with open(config_path, 'w') as f:
            json.dump(CONFIG, f, indent=2)
        
        masked_password = password[:2] + '*' * (len(password) - 2) if len(password) > 2 else '***'
        logger.info(f"Credentials updated - IP: {ip_address}, Username: {username}, Password: {masked_password}")
        return f"Credentials for {ip_address} updated successfully"
    except Exception as e:
        error_msg = f"Failed to update credentials: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return f"Error updating credentials: {error_msg}"

@mcp.tool()
def get_current_configuration():
    """Get the current configuration with masked passwords.

    Returns:
        str: JSON string of the current configuration with masked passwords.
    """
    logger.info("Getting current configuration")
    
    # Create a copy with masked passwords
    masked_config = {}
    for ip, creds in CONFIG.items():
        username = creds.get("username", "")
        password = creds.get("password", "")
        masked_password = password[:2] + '*' * (len(password) - 2) if len(password) > 2 else '***'
        
        masked_config[ip] = {
            "username": username,
            "password": masked_password
        }
    
    config_info = {
        "default_ip": DEFAULT_IP,
        "config": masked_config
    }
    
    return json.dumps(config_info, indent=2)


if __name__ == "__main__":
    logger.info("Starting IxNetwork MCP server")
    try: 
        # Run the MCP server
        
        logger.info("Starting MCP server...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        logger.error(traceback.format_exc())
    logger.info("IxNetwork MCP server stopped")