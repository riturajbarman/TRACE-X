import json
import numpy as np
from datetime import datetime, timezone
from app.domain.event.models import Event

# Mapping of known event types and sources to arbitrary integer indices for basic encoding
EVENT_TYPE_MAPPING = {
    "generic": 0,
    "process_exec": 1,
    "file_read": 2,
    "file_write": 3,
    "network_connection": 4,
    "registry_write": 5,
    "registry_read": 6,
    "powershell_encoded": 7,
    "antivirus_alert": 8,
}

SOURCE_MAPPING = {
    "test": 0,
    "evtx": 1,
    "sysmon": 2,
    "firewall": 3,
    "edr": 4,
}

# Suspicious keywords for basic keyword-based features
SUSPICIOUS_KEYWORDS = [
    "powershell", "-enc", "bypass", "hidden", "mimikatz", 
    "wget", "curl", "invoke-webrequest", "rundll32", 
    "regsvr32", "shadowcopy", "vssadmin", "temp", "tmp"
]

FEATURE_NAMES = [
    "event_type_encoded",
    "source_encoded",
    "hour_of_day",
    "day_of_week",
    "data_size",
    "has_process_name",
    "has_network_fields",
    "has_registry_key",
    "has_file_path",
    "keyword_score"
]

def extract_features(event: Event) -> np.ndarray:
    """
    Extract a deterministic feature vector from a TRACE-X Event.
    Features:
    0: event_type (encoded)
    1: source (encoded)
    2: hour of day (0-23)
    3: day of week (0-6)
    4: data_size (length of serialized json)
    5: has_process_name (0 or 1)
    6: has_network_fields (0 or 1)
    7: has_registry_key (0 or 1)
    8: has_file_path (0 or 1)
    9: suspicious_keyword_score (count)
    """
    
    # 0. event_type
    event_type_val = EVENT_TYPE_MAPPING.get(event.event_type.lower() if event.event_type else "generic", -1)
    
    # 1. source
    source_val = SOURCE_MAPPING.get(event.source.lower() if event.source else "test", -1)
    
    # 2. hour of day & 3. day of week
    dt = event.timestamp if event.timestamp else datetime.now(timezone.utc)
    hour_val = dt.hour
    day_val = dt.weekday()
    
    # Extract data payload
    data = event.data if isinstance(event.data, dict) else {}
    data_str = json.dumps(data).lower()
    
    # 4. data_size
    data_size_val = len(data_str)
    
    # 5. has_process_name
    has_process_name = 1 if "process_name" in data else 0
    
    # 6. has_network_fields (ip, dst_ip, src_ip, domain)
    has_network = 1 if any(k in data for k in ["ip", "dst_ip", "src_ip", "domain"]) else 0
    
    # 7. has_registry_key
    has_registry = 1 if "registry_key" in data else 0
    
    # 8. has_file_path (path, filename)
    has_path = 1 if any(k in data for k in ["path", "filename"]) else 0
    
    # 9. suspicious_keyword_score
    keyword_score = sum(1 for kw in SUSPICIOUS_KEYWORDS if kw in data_str)
    
    features = [
        float(event_type_val),
        float(source_val),
        float(hour_val),
        float(day_val),
        float(data_size_val),
        float(has_process_name),
        float(has_network),
        float(has_registry),
        float(has_path),
        float(keyword_score)
    ]
    
    return np.array(features)
