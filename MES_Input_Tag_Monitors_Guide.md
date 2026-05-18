# MES Input Tag Monitors in Ignition Gateway

## Implementation Guideline Document

### Executive Summary

This document provides a comprehensive guide for implementing a tag monitoring system in Ignition Gateway that replicates the functionality of the legacy COM+ service. The system will subscribe to OPC tags mapped in the fc_bridge table, detect value changes, validate them against deadband thresholds, and trigger appropriate REST API calls to the MES system.

---

## 1. Architecture Overview

### 1.1 System Components

```
┌─────────────────────────────────────────────────────┐
│         Ignition Gateway Script Environment         │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │    Tag Monitor Manager (Startup Script)       │   │
│  │  - Initialize tag monitors at gateway startup │   │
│  │  - Load tag definitions from fc/tags endpoint │   │
│  │  - Create tag change event listeners          │   │
│  └──────────────────────────────────────────────┘   │
│                        ▼                              │
│  ┌──────────────────────────────────────────────┐   │
│  │    Tag Definition Cache                      │   │
│  │  - fc_namesp_tag records                     │   │
│  │  - fc_namesp_node records                    │   │
│  │  - OPC tag mappings (fc_bridge)              │   │
│  └──────────────────────────────────────────────┘   │
│                        ▼                              │
│  ┌──────────────────────────────────────────────┐   │
│  │    Tag Change Event Listener                 │   │
│  │  - Monitor OPC tag value changes             │   │
│  │  - Apply deadband filtering                  │   │
│  │  - Invoke appropriate handlers               │   │
│  └──────────────────────────────────────────────┘   │
│                        ▼                              │
│  ┌──────────────────────────────────────────────┐   │
│  │    Tag Handler Dispatcher                    │   │
│  │  - Route to tag-specific handler            │   │
│  │  - Build MES REST API request               │   │
│  │  - Execute async REST call                  │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
└─────────────────────────────────────────────────────┘
        ▼                              ▼
   ┌─────────────┐            ┌──────────────┐
   │   OPC UA    │            │  MES REST    │
   │  Tags (PLC) │            │   API        │
   └─────────────┘            └──────────────┘
```

### 1.2 Data Flow

1. **Initialization Phase**: On gateway startup, load all tag definitions from MES
2. **Monitoring Phase**: Subscribe to OPC tag changes
3. **Validation Phase**: Apply deadband and validation rules
4. **Execution Phase**: Call appropriate MES REST API endpoint
5. **Logging Phase**: Log results for troubleshooting

---

## 2. Database Schema Understanding

### 2.1 Key Tables

**fc_namesp_node** - Entities/Nodes

```
- node_id: Unique identifier
- node_desc: Node name (e.g., "PostExecUtil", "BOMItemCurStep")
- node_level: Hierarchy level
- node_level1_desc through node_level4_desc: Path components
- ent_id: Entity ID
- bom_pos: Bill of Materials position
- parent_node_id: Parent node reference
```

**fc_namesp_tag** - Tag Definitions

```
- tag_id: Unique identifier
- tag_desc: Tag name (e.g., "AddProdQtyCntr", "SetRawReasCd")
- node_id: Reference to fc_namesp_node
- data_type: TagDataTypes enum (tagAnalog, tagString, etc.)
- readable: Boolean (output tag)
- writeable: Boolean (input tag)
- deadband: Double (minimum change threshold)
- scaling_factor: Double (value scaling)
- custom: Boolean (custom tag flag)
- reset_trigger_value: Boolean
- only_trigger_on_value: Optional trigger value
- enable_tag_update: Boolean (persist changes)
- last_value: Previous value
- last_result_cd: Last operation result
- last_result_desc: Result description
- log_option: Bitfield for logging settings
```

**fc_bridge** - OPC Tag Mappings

```
- bridge_id: Unique identifier
- tag_id: Reference to fc_namesp_tag
- opc_address: OPC UA item path
- (Other connection parameters)
```

### 2.2 Data Type Enumeration

```csharp
// In your Ignition implementation
TAG_DATA_TYPES = {
    0: "tagAnalog",        # Numeric double values
    1: "tagString",        # String values
    2: "tagStringArray",   # Array of strings
    3: "tagFloatingPointArray"  # Array of doubles
}

RESULT_STATES = {
    0: "NoActivity",
    1: "Success",
    2: "InProgress",
    3: "Failure"
}
```

---

## 3. Implementation Strategy

### 3.1 Phase 1: Tag Definition Cache

**Objective**: Load and cache tag definitions in memory for fast lookup

**Implementation Location**: `shared.mes.cache` module

```python
# Pseudocode structure
class TagDefinitionCache:
    def __init__(self):
        self.tags_by_id = {}  # tag_id -> tag definition
        self.tags_by_node = {}  # node_id -> list of tags
        self.tag_handlers = {}  # tag_desc -> handler function
        self.opc_tag_map = {}  # opc_address -> tag_id
        self.last_refresh = None
    
    def load_from_api(self):
        """Fetch tag definitions from /fc/tags endpoint"""
        # GET http://mes-host/api/fc/tags
        # GET http://mes-host/api/fc/nodes
        # GET http://mes-host/api/fc/bridge
    
    def get_tag_by_id(self, tag_id):
        """Return tag definition by ID"""
        
    def get_tags_by_node(self, node_id):
        """Return all tags for a node"""
        
    def get_handler(self, tag_desc):
        """Return handler for tag type"""
        
    def should_refresh(self, max_age_minutes=60):
        """Check if cache needs refresh"""
```

**Key Considerations**:
- Cache definitions in memory for performance
- Refresh cache periodically (hourly default)
- Handle API failures gracefully (use stale cache)
- Thread-safe access to shared cache

### 3.2 Phase 2: Tag Handler Definitions

**Objective**: Define handlers for each tag type (maps to Tag.cs switch statement)

**Implementation Location**: `shared.mes.handlers` module

#### 2.2.1 Handler Architecture

Each handler should follow this pattern:

```python
def handle_tag_change(tag_def, opc_tag_address, new_value, old_value):
    """
    Args:
        tag_def: Tag definition from cache
        opc_tag_address: Full OPC tag path
        new_value: New value from OPC tag
        old_value: Previous value
        
    Returns:
        result: {
            'success': bool,
            'result_code': int,
            'result_desc': str,
            'api_endpoint': str,
            'payload': dict
        }
    """
    # 1. Validate value type
    # 2. Apply scaling if needed
    # 3. Build API request
    # 4. Execute API call
    # 5. Return result
```

#### 2.2.2 Tag Handler Categories

Based on Tag.cs `HandleInputTagChange()` method:

**Category 1: Job Execution Tags**
- SetLotNo, SetItemId, SetProdCd, SetConsCd, SetToEntId, SetFromEntId, SetActSpecValue
- Handler: `handle_job_execution_tag()`
- API Endpoint: `job_exec/SetCurLotData` or `job_exec/ChangeSpecValue`

**Category 2: Quantity Tags**
- AddProdQtyAbs, AddConsQtyAbs, AddProdQtyAbsTrg, AddConsQtyAbsTrg, AddProdQtyCntr, AddConsQtyCntr
- Handler: `handle_quantity_tag()`
- API Endpoint: `job_exec/AddProd` or `job_exec/AddCons`
- Special: Counter tags require buffering and periodic flush

**Category 3: Job Control Tags**
- StartNextJob, EndCurJob, StartSpecifiedJob
- Handler: `handle_job_control_tag()`
- API Endpoint: `job_exec/StartNextJobViaFC` or `job_exec/EndJob`

**Category 4: Data Log Tags**
- SetDataLogValue, SampleTrigger
- Handler: `handle_datalog_tag()`
- API Endpoint: `data_log_value/UpdateSpecific` or `data_log_grp/SaveSample`

**Category 5: Reason Code Tags**
- SetRawReasCd
- Handler: `handle_reason_code_tag()`
- API Endpoint: `util_exec/SetRawReason` or `labor_exec/SetRawReason`

**Category 6: Step Tags**
- SetStepData, SetStepDone
- Handler: `handle_step_tag()`
- API Endpoint: `job_exec/UpdateStepData` or `job_exec/StopStep`

**Category 7: Trigger Tags**
- SetTrg (on PostExecDataLog, PostExecUtil, PostExecProdEvent, CurrentDateTime)
- Handler: `handle_trigger_tag()`
- API Endpoint: Various depending on node type

**Category 8: Entity Tags**
- SetShiftId
- Handler: `handle_entity_tag()`
- API Endpoint: `ent/StartShift`

### 3.3 Phase 3: Deadband and Value Change Detection

**Objective**: Implement deadband logic to filter insignificant changes

**Implementation Location**: `shared.mes.validation` module

```python
def would_exceed_deadband(tag_def, new_value, cur_value):
    """
    Determines if value change exceeds deadband threshold.
    
    Args:
        tag_def: Tag definition with deadband property
        new_value: New value
        cur_value: Current/previous value
        
    Returns:
        bool: True if change exceeds deadband, False otherwise
    """
    
    # Handle NULL values
    if cur_value is None:
        return True
    
    if new_value is None:
        return False
    
    # Check reset trigger flag
    if tag_def.get('reset_trigger_value', False):
        return True
    
    # Check only_trigger_on_value constraint
    if tag_def.get('only_trigger_on_value') is not None:
        if new_value != tag_def['only_trigger_on_value']:
            return False
    
    # Analog tag deadband
    if tag_def['data_type'] == 'tagAnalog':
        try:
            current_double = float(cur_value)
            new_double = float(new_value)
            delta = abs(new_double - current_double)
            deadband = float(tag_def.get('deadband', 1.0))
            return delta >= deadband
        except ValueError:
            return False
    
    # String tag - any change
    elif tag_def['data_type'] == 'tagString':
        return str(new_value) != str(cur_value)
    
    return False

def apply_scaling_factor(tag_def, value):
    """Apply scaling factor to numeric values"""
    if tag_def['data_type'] != 'tagAnalog':
        return value
    
    try:
        scaling_factor = float(tag_def.get('scaling_factor', 1.0))
        if scaling_factor == 0.0:
            scaling_factor = 1.0
        return float(value) * scaling_factor
    except (ValueError, TypeError):
        return value

def is_numeric(value):
    """Check if value is numeric"""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False
```

### 3.4 Phase 4: OPC Tag Subscriptions

**Objective**: Subscribe to OPC tag changes and trigger handlers

**Implementation Location**: `shared.mes.subscriptions` module

```python
def subscribe_to_tag(tag_def, opc_tag_address):
    """
    Subscribe to OPC tag changes.
    
    Creates a tag value listener that will call handler on changes.
    """
    # 1. Get OPC tag quality and initial value
    # 2. Register change listener
    # 3. Store subscription reference
    # 4. Initialize last values for deadband calculation

def on_opc_tag_change(tag_event):
    """
    Callback handler for OPC tag changes.
    
    Called when subscribed OPC tag changes value.
    """
    # 1. Extract tag_id from event metadata
    # 2. Get tag definition from cache
    # 3. Check if value exceeds deadband
    # 4. Log tag change event
    # 5. Dispatch to appropriate handler
    # 6. Update last known value
    # 7. Log result

def initialize_all_subscriptions():
    """
    Initialize all tag subscriptions at gateway startup.
    
    Runs in startup script to set up monitoring for all tags.
    """
    # 1. Load tag cache
    # 2. Iterate through all input tags (writeable=true)
    # 3. Get OPC address from fc_bridge
    # 4. Create subscription
    # 5. Log initialization status
```

### 3.5 Phase 5: API Request Builder

**Objective**: Build and execute MES REST API requests

**Implementation Location**: `shared.mes.api_builder` module

```python
class APIRequestBuilder:
    """Builds MES REST API requests"""
    
    def __init__(self, session_id, user_id):
        self.session_id = session_id
        self.user_id = user_id
        self.api_base_url = "http://mes-host/api"
    
    def build_add_prod_request(self, ent_id, qty_prod, **kwargs):
        """
        Build AddProd XML request
        
        Equivalent to: job_exec/AddProd
        """
        params = {
            'ent_id': ent_id,
            'user_id': self.user_id,
            'qty_prod': qty_prod,
            'apply_scaling_factor': '1'
        }
        params.update(kwargs)  # reason_code, lot_no, item_id, etc.
        return self.build_request('job_exec', 'AddProd', params)
    
    def build_add_cons_request(self, ent_id, qty_cons, **kwargs):
        """Build AddCons XML request"""
        params = {
            'ent_id': ent_id,
            'user_id': self.user_id,
            'qty_cons': qty_cons,
            'apply_scaling_factor': '1'
        }
        params.update(kwargs)
        return self.build_request('job_exec', 'AddCons', params)
    
    def build_set_cur_lot_data_request(self, ent_id, **kwargs):
        """Build SetCurLotData request"""
        params = {
            'ent_id': ent_id,
            'user_id': self.user_id
        }
        params.update(kwargs)
        return self.build_request('job_exec', 'SetCurLotData', params)
    
    def build_request(self, object_name, command_name, params):
        """
        Generic request builder
        
        Returns REST endpoint and payload
        """
        endpoint = f"{self.api_base_url}/{object_name}/{command_name}"
        payload = {
            'session_id': self.session_id,
            'parameters': params
        }
        return {
            'endpoint': endpoint,
            'method': 'POST',
            'payload': payload
        }

def execute_api_request(request_spec, timeout=30):
    """
    Execute MES REST API request
    
    Args:
        request_spec: Dict with endpoint, method, payload
        timeout: Request timeout in seconds
        
    Returns:
        result: {
            'success': bool,
            'status_code': int,
            'response': str,
            'error': str (if failed)
        }
    """
    # 1. Validate request spec
    # 2. Serialize payload (JSON or XML)
    # 3. Execute HTTP request
    # 4. Handle response
    # 5. Log API call and result
```

### 3.6 Phase 6: Event Logging and Result Tracking

**Objective**: Log all tag changes and API results for debugging

**Implementation Location**: `shared.mes.logging` module

```python
def log_tag_change_event(tag_id, tag_desc, event_type, description, 
                         exception_text="", current_value=""):
    """
    Log tag change event
    
    Event types:
    - InputTagChange: Input tag value changed
    - InputTagChangeError: Error handling input tag
    - OutputTagChange: Output tag updated
    - TagChangeWarning: Warning about tag change
    """
    # Log to:
    # 1. Gateway console (system.util.getLogger())
    # 2. MES database (if configured)
    # 3. Tag's last_result_cd and last_result_desc

def update_tag_result(tag_id, result_code, result_desc):
    """
    Update tag's result status in MES database
    
    Calls: fc_namesp_tag/UpdateSpecific
    """
    # Update last_result_cd and last_result_desc
    # Used for downstream monitoring and diagnostics

def log_api_call(function_called, endpoint, payload, 
                 response_code, response_text, success):
    """
    Log MES API call for audit trail
    """
    # Log all API interactions
    # Timestamp, function, endpoint, request, response, result
```

---

## 4. Implementation Roadmap

### 4.1 Step 1: Create Cache Module
- Load tag definitions from MES API
- Implement in-memory cache with TTL
- Create lookup functions
- **Estimated Time**: 2-3 hours

### 4.2 Step 2: Create Validation Module
- Implement deadband checking
- Implement scaling factor application
- Implement data type validation
- **Estimated Time**: 1-2 hours

### 4.3 Step 3: Create API Builder Module
- Define request structures for each API endpoint
- Implement parameter builders
- Implement serialization (JSON/XML)
- **Estimated Time**: 2-3 hours

### 4.4 Step 4: Create Handler Module
- Implement handler for each tag category
- Map tag_desc to handler function
- Implement error handling and logging
- **Estimated Time**: 4-6 hours

### 4.5 Step 5: Create Subscription Module
- Implement OPC tag subscription
- Implement change event callback
- Implement tag value tracking
- **Estimated Time**: 2-3 hours

### 4.6 Step 6: Create Logging Module
- Implement event logging
- Implement result tracking
- Implement audit trail
- **Estimated Time**: 1-2 hours

### 4.7 Step 7: Create Gateway Startup Script
- Initialize cache
- Initialize subscriptions
- Handle startup errors
- **Estimated Time**: 1-2 hours

### 4.8 Step 8: Testing and Validation
- Unit tests for each module
- Integration tests
- End-to-end testing with actual MES
- **Estimated Time**: 4-6 hours

---

## 5. Detailed Implementation Examples

### 5.1 Example: Counter Tag Handler (AddProdQtyCntr)

Counter tags require special handling - they buffer incremental values and flush periodically:

```python
# In shared.mes.handlers

counter_buffers = {}  # tag_id -> buffer state

class CounterTagBuffer:
    def __init__(self, tag_id, deadband, max_value=None):
        self.tag_id = tag_id
        self.deadband = deadband
        self.max_value = max_value
        self.last_value_used = 0.0
        self.first_value_received = False
        self.last_flush = system.date.now()
        self.buffered_counts = 0.0

def handle_counter_tag_change(tag_def, opc_tag_address, new_value):
    """
    Handle counter tag change (AddProdQtyCntr, AddConsQtyCntr)
    
    Counters work differently than other tags:
    1. First value initializes baseline
    2. Subsequent values increment the counter
    3. Counter wraps at max_value
    4. Counts are buffered and flushed periodically
    """
    tag_id = tag_def['tag_id']
    
    # Initialize buffer if needed
    if tag_id not in counter_buffers:
        counter_buffers[tag_id] = CounterTagBuffer(
            tag_id, 
            tag_def.get('deadband', 1.0),
            tag_def.get('max_value')
        )
    
    buffer = counter_buffers[tag_id]
    
    try:
        new_counter_value = float(new_value)
        
        # First value initialization
        if not buffer.first_value_received:
            if 0.0 <= new_counter_value <= 1.0:
                buffer.last_value_used = 0.0
            elif (new_counter_value - buffer.last_value_used) < -1.0:
                # Wrapped counter detected - report missing production
                report_missing_production(tag_def, new_counter_value, buffer.last_value_used)
                buffer.last_value_used = new_counter_value
            
            buffer.first_value_received = True
            return {'success': True, 'buffered': True}
        
        # Check if enough time has elapsed for flush
        time_since_flush = system.date.secondsBetween(
            buffer.last_flush, 
            system.date.now()
        )
        
        if time_since_flush >= tag_def.get('poll_interval', 60):
            # Flush buffered counts
            counts = calculate_counts_and_reset(
                new_counter_value,
                buffer.last_value_used,
                buffer.max_value,
                tag_def.get('deadband', 1.0),
                tag_def.get('scaling_factor', 1.0)
            )
            
            if counts > 0:
                # Execute API call
                if tag_def['tag_desc'] == 'AddProdQtyCntr':
                    return handle_add_prod_qty(tag_def, counts)
                else:
                    return handle_add_cons_qty(tag_def, counts)
            
            buffer.last_flush = system.date.now()
        
        return {'success': True, 'buffered': True}
        
    except Exception as e:
        logger.error(f"Error handling counter tag {tag_id}: {str(e)}")
        return {'success': False, 'error': str(e)}

def calculate_counts_and_reset(current_value, last_used, max_value, deadband, scaling_factor):
    """Calculate counter delta with wraparound support"""
    counts = 0.0
    
    if current_value >= last_used:
        counts = current_value - last_used
    elif max_value > 0.0:
        # Counter wrapped
        counts = ((max_value - last_used) + current_value) + 1.0
    else:
        counts = current_value
        if counts == 0.0:
            return 0.0
    
    if counts >= deadband:
        if scaling_factor != 0.0:
            counts *= scaling_factor
        return counts
    
    return 0.0
```

### 5.2 Example: Job Execution Tag Handler (SetLotNo)

```python
def handle_job_execution_tag(tag_def, opc_tag_address, new_value):
    """
    Handle job execution tags (SetLotNo, SetItemId, SetProdCd, etc.)
    
    These tags update the current lot data for the running job.
    """
    tag_desc = tag_def['tag_desc']
    node_def = get_node_definition(tag_def['node_id'])
    
    # Get the corresponding value to set
    if tag_desc == 'SetLotNo':
        api_endpoint = 'job_exec/SetCurLotData'
        params = {
            'ent_id': str(node_def['ent_id']),
            'user_id': get_session_user_id(),
            'cur_lot_no': str(new_value)
        }
        if node_def['bom_pos'] != -999:
            params['bom_pos'] = str(node_def['bom_pos'])
    
    elif tag_desc == 'SetItemId':
        api_endpoint = 'job_exec/SetCurLotData'
        params = {
            'ent_id': str(node_def['ent_id']),
            'user_id': get_session_user_id(),
            'cur_item_id': str(new_value)
        }
        if node_def['bom_pos'] != -999:
            params['bom_pos'] = str(node_def['bom_pos'])
    
    elif tag_desc in ['SetProdCd', 'SetConsCd']:
        api_endpoint = 'job_exec/SetCurLotData'
        params = {
            'ent_id': str(node_def['ent_id']),
            'user_id': get_session_user_id(),
            'cur_reas_cd': str(new_value)
        }
        if node_def['bom_pos'] != -999:
            params['bom_pos'] = str(node_def['bom_pos'])
    
    # Build and execute request
    request = build_api_request(api_endpoint, params)
    return execute_api_request(request)
```

### 5.3 Example: Trigger Tag Handler (SetTrg on PostExecUtil)

Trigger tags on specific node types call different endpoints:

```python
def handle_trigger_tag(tag_def, opc_tag_address, new_value):
    """
    Handle trigger tags (SetTrg) on various node types
    
    The endpoint depends on the node type:
    - PostExecDataLog: data_log_grp/SampleViaFC
    - PostExecUtil: util_exec/InsRawReasViaFC
    - PostExecProdEvent: job_exec/InsertProdViaFC
    - CurrentDateTime: fc_namesp_tag/CurDateTime
    """
    node_def = get_node_definition(tag_def['node_id'])
    node_desc = node_def['node_desc']
    
    if int(new_value) == 0:
        return {'success': True, 'message': 'Trigger value is 0, skipping'}
    
    if node_desc == 'PostExecDataLog':
        return handle_postexec_datalog_trigger(tag_def, node_def)
    
    elif node_desc == 'PostExecUtil':
        return handle_postexec_util_trigger(tag_def, node_def)
    
    elif node_desc == 'PostExecProdEvent':
        return handle_postexec_prodevt_trigger(tag_def, node_def)
    
    elif node_desc == 'CurrentDateTime':
        return handle_current_datetime_trigger(tag_def, node_def)
    
    return {'success': False, 'error': f'Unknown trigger node type: {node_desc}'}

def handle_postexec_util_trigger(tag_def, node_def):
    """Handle trigger on PostExecUtil node"""
    # Collect required parameters from sibling tags
    ent_id = get_tag_value_as_string(node_def['node_id'], 'SetEntID', '')
    start_year = get_tag_value_as_string(node_def['node_id'], 'SetStartYear', '')
    start_month = get_tag_value_as_string(node_def['node_id'], 'SetStartMonth', '')
    start_day = get_tag_value_as_string(node_def['node_id'], 'SetStartDay', '')
    start_hour = get_tag_value_as_string(node_def['node_id'], 'SetStartHour', '')
    start_minute = get_tag_value_as_string(node_def['node_id'], 'SetStartMinute', '')
    start_second = get_tag_value_as_string(node_def['node_id'], 'SetStartSecond', '')
    raw_reas_code = get_tag_value_as_string(node_def['node_id'], 'SetRawReasCd', '')
    duration = get_tag_value_as_string(node_def['node_id'], 'SetDuration', '')
    
    # Validate all parameters present
    if not all([ent_id, start_year, start_month, start_day, start_hour, 
                start_minute, start_second, raw_reas_code, duration]):
        return {'success': False, 'error': 'Missing required parameter for trigger'}
    
    # Build datetime string
    start_time = f"{start_month}/{start_day}/{start_year} {start_hour.zfill(2)}:{start_minute.zfill(2)}:{start_second.zfill(2)}"
    
    # Execute API call
    params = {
        'ent_id': ent_id,
        'raw_reas_cd': raw_reas_code,
        'event_time': start_time,
        'duration': duration
    }
    
    request = build_api_request('util_exec/InsRawReasViaFC', params)
    return execute_api_request(request)
```

### 5.4 Example: Gateway Startup Script

```python
# Project > Gateway Event Scripts > Startup

def startup_mes_tag_monitors():
    """
    Initialize MES tag monitoring on gateway startup.
    
    This script runs once when the Ignition gateway starts up.
    It loads tag definitions and initializes OPC subscriptions.
    """
    logger = system.util.getLogger('MES.TagMonitor')
    
    try:
        logger.info("=" * 80)
        logger.info("Starting MES Tag Monitor initialization...")
        logger.info("=" * 80)
        
        # Step 1: Initialize cache
        logger.info("Loading tag definitions from MES API...")
        shared.mes.cache.load_tag_definitions()
        tag_count = shared.mes.cache.get_tag_count()
        logger.info(f"Successfully loaded {tag_count} tag definitions")
        
        # Step 2: Initialize handler mappings
        logger.info("Initializing tag handlers...")
        shared.mes.handlers.initialize_handlers()
        
        # Step 3: Initialize subscriptions
        logger.info("Creating OPC tag subscriptions...")
        subscription_count = shared.mes.subscriptions.initialize_all_subscriptions()
        logger.info(f"Successfully created {subscription_count} tag subscriptions")
        
        # Step 4: Log initialization complete
        logger.info("=" * 80)
        logger.info("MES Tag Monitor initialization COMPLETE")
        logger.info("=" * 80)
        
        # Store initialization timestamp
        shared.mes.cache.initialization_time = system.date.now()
        
    except Exception as e:
        logger.error("ERROR during MES Tag Monitor initialization:")
        logger.error(str(e))
        import traceback
        logger.error(traceback.format_exc())

# Execute startup
startup_mes_tag_monitors()
```

---

## 6. Error Handling and Recovery

### 6.1 API Call Failures

```python
def execute_api_request_with_retry(request_spec, max_retries=3, timeout=30):
    """
    Execute API request with automatic retry logic.
    """
    for attempt in range(max_retries):
        try:
            result = http_post(
                request_spec['endpoint'],
                request_spec['payload'],
                timeout=timeout
            )
            
            if result['status_code'] == 200:
                return {'success': True, 'response': result}
            
            elif result['status_code'] in [500, 503]:
                # Temporary server error - retry
                if attempt < max_retries - 1:
                    logger.warning(f"API call failed with {result['status_code']}, retrying...")
                    system.util.sleep(1000)  # Wait 1 second before retry
                    continue
                else:
                    raise Exception(f"API returned {result['status_code']} after {max_retries} attempts")
            
            else:
                # Client error - don't retry
                raise Exception(f"API returned {result['status_code']}: {result.get('text', '')}")
        
        except Exception as e:
            logger.error(f"API call attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                return {
                    'success': False,
                    'error': str(e),
                    'attempts': attempt + 1
                }
```

### 6.2 Cache Refresh on Stale Data

```python
def get_tag_definition_with_refresh(tag_id):
    """
    Get tag definition with automatic cache refresh on miss.
    """
    try:
        # Try to get from cache
        tag_def = shared.mes.cache.get_tag_by_id(tag_id)
        if tag_def:
            return tag_def
        
        # Cache miss - refresh cache
        logger.warning(f"Tag {tag_id} not in cache, refreshing...")
        shared.mes.cache.load_tag_definitions()
        
        # Try again
        tag_def = shared.mes.cache.get_tag_by_id(tag_id)
        if tag_def:
            return tag_def
        
        raise Exception(f"Tag {tag_id} not found in MES API")
    
    except Exception as e:
        logger.error(f"Error retrieving tag definition: {str(e)}")
        raise
```

### 6.3 Subscription Recovery

```python
def handle_subscription_error(tag_id, error):
    """
    Handle subscription error and attempt recovery.
    """
    logger = system.util.getLogger('MES.Subscriptions')
    logger.error(f"Subscription error for tag {tag_id}: {str(error)}")
    
    # Attempt to recreate subscription
    try:
        tag_def = shared.mes.cache.get_tag_by_id(tag_id)
        if tag_def:
            opc_tag = get_opc_tag_address(tag_id)
            shared.mes.subscriptions.subscribe_to_tag(tag_def, opc_tag)
            logger.info(f"Successfully recreated subscription for tag {tag_id}")
    except Exception as recovery_error:
        logger.error(f"Failed to recreate subscription: {str(recovery_error)}")
```

---

## 7. Testing Strategy

### 7.1 Unit Testing

```python
# tests/test_deadband.py

def test_deadband_analog_tag():
    """Test deadband calculation for analog tags"""
    tag_def = {'data_type': 'tagAnalog', 'deadband': 1.0}
    
    # Should not exceed deadband
    assert not shared.mes.validation.would_exceed_deadband(tag_def, 10.5, 10.0)
    
    # Should exceed deadband
    assert shared.mes.validation.would_exceed_deadband(tag_def, 11.5, 10.0)

def test_scaling_factor():
    """Test scaling factor application"""
    tag_def = {'data_type': 'tagAnalog', 'scaling_factor': 2.5}
    
    result = shared.mes.validation.apply_scaling_factor(tag_def, 10.0)
    assert result == 25.0

def test_counter_wraparound():
    """Test counter wraparound detection"""
    # Simulate counter wrapping from 999 to 10 with max_value of 1000
    counts = calculate_counts_and_reset(10, 999, 1000, 1.0, 1.0)
    expected = ((1000 - 999) + 10) + 1.0  # Should be 12
    assert counts == expected
```

### 7.2 Integration Testing

```python
# tests/test_handlers.py

def test_add_prod_qty_handler():
    """Test AddProdQtyAbs handler"""
    tag_def = {
        'tag_id': 123,
        'tag_desc': 'AddProdQtyAbs',
        'data_type': 'tagAnalog',
        'scaling_factor': 1.0,
        'node_id': 1
    }
    
    # Mock API
    with mock_api_endpoint('job_exec/AddProd'):
        result = shared.mes.handlers.handle_quantity_tag(
            tag_def, '/Path/To/OPC/Tag', 100.0
        )
        assert result['success'] == True
        assert result['api_endpoint'] == 'job_exec/AddProd'
```

### 7.3 End-to-End Testing

```
# Manual Test Checklist:

1. Quantity Tags (AddProdQtyCntr)
   - [ ] Initial counter value initialization
   - [ ] Incremental counter changes
   - [ ] Counter wraparound detection
   - [ ] Buffering and periodic flush
   - [ ] Missing production reporting
   - [ ] Scaling factor application

2. Job Execution Tags (SetLotNo)
   - [ ] Value change validation
   - [ ] Deadband filtering
   - [ ] Buffered counts saved before tag change
   - [ ] Correct API endpoint called
   - [ ] Result status updated

3. Trigger Tags (SetTrg on PostExecUtil)
   - [ ] Parameter collection from sibling tags
   - [ ] Missing parameter detection
   - [ ] Datetime formatting
   - [ ] Correct API endpoint for node type
   - [ ] Result status updated

4. Error Scenarios
   - [ ] API timeout handling
   - [ ] Invalid value type for tag
   - [ ] Missing required parameter
   - [ ] Subscription failure recovery
   - [ ] Cache refresh on miss

5. Monitoring
   - [ ] Event logs created for all tag changes
   - [ ] Result codes persisted to MES
   - [ ] Error logging for failures
   - [ ] Cache refresh happens periodically
```

---

## 8. Configuration and Deployment

### 8.1 Gateway Settings

Create a gateway configuration file for MES integration:

```python
# Configuration in gateway scripting environment

MES_CONFIG = {
    'api_base_url': 'http://mes-server:8080/api',
    'session_id': 'ignition-gateway',
    'user_id': 'factory-connector',
    'api_timeout': 30,
    'api_retries': 3,
    'cache_ttl_minutes': 60,
    'counter_flush_interval': 60,
    'log_level': 'INFO',
    'enable_audit_logging': True
}

# Load from external configuration if needed
def load_config():
    """Load configuration from file or database"""
    pass
```

### 8.2 Deployment Checklist

```
1. Pre-Deployment
   - [ ] All unit tests passing
   - [ ] Integration tests passing
   - [ ] Code review completed
   - [ ] Performance testing completed
   - [ ] Error handling verified

2. Deployment
   - [ ] Gateway backup created
   - [ ] Modules imported to gateway
   - [ ] Configuration updated
   - [ ] Startup script enabled
   - [ ] Gateway restarted safely

3. Post-Deployment
   - [ ] Startup script executed successfully
   - [ ] Tag subscriptions created
   - [ ] Initial API call successful
   - [ ] Event logs showing activity
   - [ ] MES database being updated

4. Monitoring
   - [ ] Set up alerts for subscription failures
   - [ ] Monitor API call success rate
   - [ ] Monitor event log growth
   - [ ] Periodic cache refresh working
```

---

## 9. Performance Considerations

### 9.1 Optimization Techniques

```python
# 1. Batch API requests where possible
def batch_api_calls(request_list):
    """
    Combine multiple API calls into single batch request.
    
    Instead of:
    - AddProd for 50 units
    - AddProd for 25 units
    
    Combine into:
    - AddProd for 75 units
    """
    pass

# 2. Cache frequently accessed data
# Tag definitions cached in memory
# Node definitions cached in memory
# OPC tag mappings cached in memory

# 3. Use async API calls for non-critical operations
def execute_api_request_async(request_spec):
    """
    Execute API request asynchronously using threading.
    
    Don't block tag change handler while waiting for response.
    """
    def async_call():
        try:
            result = execute_api_request(request_spec)
            update_tag_result(result)
        except Exception as e:
            logger.error(f"Async API call failed: {str(e)}")
    
    thread = threading.Thread(target=async_call)
    thread.start()

# 4. Implement circuit breaker for API failures
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout_seconds=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def is_available(self):
        """Check if API is available based on failure history"""
        if self.state == 'CLOSED':
            return True
        elif self.state == 'OPEN':
            if system.date.secondsSince(self.last_failure_time) > self.timeout_seconds:
                self.state = 'HALF_OPEN'
                return True
            return False
        elif self.state == 'HALF_OPEN':
            return True
        
        return False
```

---

## 10. Monitoring and Maintenance

### 10.1 Health Checks

```python
def health_check_mes_integration():
    """
    Perform health check on MES integration.
    
    Should be called periodically (every 5 minutes).
    """
    logger = system.util.getLogger('MES.HealthCheck')
    status = {
        'timestamp': system.date.now(),
        'cache_loaded': False,
        'subscriptions_active': 0,
        'last_cache_refresh': None,
        'api_availability': False,
        'errors': []
    }
    
    try:
        # Check cache
        if shared.mes.cache.is_loaded():
            status['cache_loaded'] = True
            status['last_cache_refresh'] = shared.mes.cache.last_refresh
        else:
            status['errors'].append('Tag cache not loaded')
        
        # Check subscriptions
        status['subscriptions_active'] = shared.mes.subscriptions.get_active_count()
        
        # Check API connectivity
        if test_api_endpoint('job_exec/Ping'):
            status['api_availability'] = True
        else:
            status['errors'].append('MES API unavailable')
        
        # Log status
        logger.info(f"Health check: {status}")
        
        return status
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        status['errors'].append(str(e))
        return status
```

### 10.2 Maintenance Tasks

```python
# Weekly maintenance
def maintenance_weekly():
    """Perform weekly maintenance"""
    logger = system.util.getLogger('MES.Maintenance')
    
    try:
        # Clean up old logs
        logger.info("Cleaning up old event logs...")
        # Delete logs older than 30 days
        
        # Refresh cache
        logger.info("Refreshing tag definitions cache...")
        shared.mes.cache.load_tag_definitions(force=True)
        
        # Verify all subscriptions
        logger.info("Verifying subscriptions...")
        shared.mes.subscriptions.verify_all_subscriptions()
        
        logger.info("Weekly maintenance completed successfully")
    
    except Exception as e:
        logger.error(f"Maintenance failed: {str(e)}")

# Monthly maintenance
def maintenance_monthly():
    """Perform monthly maintenance"""
    # Analyze API performance metrics
    # Check for any tags with high error rates
    # Generate health report
    pass
```

---

## 11. Key Differences from COM+ Service

| Aspect | COM+ Service | Ignition Implementation |
|--------|--------------|------------------------|
| **Startup** | Managed by Windows Service | Gateway startup script |
| **Memory** | Process memory | Java/Ignition heap |
| **Logging** | Windows Event Log + DB | Ignition console + DB |
| **Config** | COM+ configuration | Python dicts + gateway settings |
| **Threading** | Component Services | Python threading |
| **API Calls** | XML over HTTP | JSON/REST over HTTP |
| **Caching** | Static loaded cache | Dynamic with TTL refresh |
| **Error Handling** | Windows events | Python exceptions + logging |
| **Testing** | VB6/C# unit tests | Python unit tests |

---

## 12. Reference: Tag Mapping Examples

### Example 1: Counter Tag (AddProdQtyCntr)

```
OPC Tag: /Station01/Counters/ProductionCounter
MES Tag Definition:
  - tag_id: 145
  - tag_desc: "AddProdQtyCntr"
  - tag_type: "tagAnalog"
  - deadband: 5.0
  - scaling_factor: 0.5
  - poll_interval: 60

Behavior:
1. Subscribe to OPC tag change
2. On change, check if exceeds deadband (5.0)
3. Every 60 seconds, calculate delta from last flush
4. Apply scaling (multiply by 0.5)
5. Call job_exec/AddProd with qty_prod parameter
6. Update fc_namesp_tag with result
```

### Example 2: Trigger Tag (SetTrg on PostExecUtil)

```
OPC Tag: /PostExecUtil01/SetTrg
MES Tag Definition:
  - tag_id: 238
  - tag_desc: "SetTrg"
  - tag_type: "tagAnalog"
  - node: PostExecUtil
  - dependent_tags: [
      "SetEntID",
      "SetStartYear", "SetStartMonth", "SetStartDay",
      "SetStartHour", "SetStartMinute", "SetStartSecond",
      "SetRawReasCd", "SetDuration"
    ]

Behavior:
1. Subscribe to SetTrg OPC tag
2. On change to non-zero value:
   a. Collect all dependent tag values
   b. Validate all parameters present
   c. Build datetime string
   d. Call util_exec/InsRawReasViaFC
3. Set Result tag with success/failure code
```

---

## Conclusion

This guideline provides a comprehensive roadmap for implementing MES Input tag monitoring in Ignition Gateway. The modular architecture ensures:

- **Maintainability**: Each component has single responsibility
- **Testability**: Easy to unit test each module
- **Scalability**: Can handle hundreds of tags
- **Reliability**: Built-in error handling and recovery
- **Debuggability**: Comprehensive logging and tracing

Follow the implementation roadmap in Section 4, and refer to the detailed examples in Section 5 for specific tag handler implementation.
