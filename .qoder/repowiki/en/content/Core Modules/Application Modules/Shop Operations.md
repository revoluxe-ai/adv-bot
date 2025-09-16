# Shop Operations

<cite>
**Referenced Files in This Document**   
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py)
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py)
- [worker.py](file://app/modules/shop_runner/shop_run_worker/worker/worker.py)
- [data_classes.py](file://app/modules/shop_runner/data_classes.py)
- [run_process_func.py](file://app/modules/shop_runner/run_process_func.py)
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py)
- [wb_shop_data_manager.py](file://app/modules/shop_runner/service_manager/wb_shop_data_manager/wb_shop_data_manager.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Core Components](#core-components)
3. [Architecture Overview](#architecture-overview)
4. [Detailed Component Analysis](#detailed-component-analysis)
5. [Execution Flow and Scheduling](#execution-flow-and-scheduling)
6. [State Synchronization and Error Isolation](#state-synchronization-and-error-isolation)
7. [Resource Allocation and Health Monitoring](#resource-allocation-and-health-monitoring)
8. [Operational Issues and Recovery Procedures](#operational-issues-and-recovery-procedures)
9. [Configuration and Command Propagation](#configuration-and-command-propagation)
10. [Conclusion](#conclusion)

## Introduction
The Shop Operations module provides a comprehensive automation framework for managing multiple Wildberries shops concurrently. This system enables automated advertising management, keyword parsing, bid optimization, and performance monitoring through a distributed worker architecture. The implementation centers on the shop_runner module, which coordinates shop-level operations through a sophisticated combination of asynchronous processing, Redis-based state management, and PostgreSQL-backed data persistence.

**Section sources**
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py#L1-L42)

## Core Components
The Shop Operations module consists of several interconnected components that work together to automate shop management tasks. The core components include the WBShop class for shop entity management, the CoroutinesManager for operational coordination, the ShopWorker for process execution, and supporting data models and utility classes.

**Section sources**
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py#L1-L42)
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)
- [worker.py](file://app/modules/shop_runner/shop_run_worker/worker/worker.py#L1-L79)
- [data_classes.py](file://app/modules/shop_runner/data_classes.py#L1-L13)

## Architecture Overview

```mermaid
graph TD
subgraph "Worker Process"
Worker[ShopWorker]
RedisManager[RedisShopManager]
end
subgraph "Shop Execution"
WBShop[WBShop]
CoroutinesManager[CoroutinesManager]
WBShopDataManager[WBShopDataManager]
end
subgraph "Data Layer"
PostgreSQL[(PostgreSQL)]
ClickHouse[(ClickHouse)]
Redis[(Redis)]
end
Worker --> WBShop
WBShop --> CoroutinesManager
CoroutinesManager --> WBShopDataManager
WBShopDataManager --> PostgreSQL
CoroutinesManager --> ClickHouse
Worker --> RedisManager
RedisManager --> Redis
WBShop --> RedisManager
style Worker fill:#f9f,stroke:#333
style WBShop fill:#bbf,stroke:#333
style CoroutinesManager fill:#f96,stroke:#333
```

**Diagram sources**
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py#L1-L42)
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)
- [worker.py](file://app/modules/shop_runner/shop_run_worker/worker/worker.py#L1-L79)
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py#L1-L81)

## Detailed Component Analysis

### WBShop Implementation
The WBShop class serves as the primary container for shop-level automation, coordinating multiple concurrent operations through asynchronous coroutines. It maintains references to the WBApi instance for Wildberries API interactions and the RedisShopManager for state persistence.

```mermaid
classDiagram
class WBShop {
+WBApi _wb_api
+RedisShopManager _redis_manager
+__init__(wb_api : WBApi, redis_manager : RedisShopManager)
+run() Coroutine
+_alive_worker_run() Coroutine
}
class WBApi {
+str shop_id
+str access
+ClientSession session
}
class RedisShopManager {
+str _active_shops_set_name
+str _shops_heartbeat_prefix
+int DEFAULT_TTL
+update_active_shops(shop_ids : list[str])
+renew_shop_ttl(shop_id : str)
+get_next_free_shop_id() str | None
+remove_shops(shop_ids : list[str])
}
WBShop --> WBApi : "uses"
WBShop --> RedisShopManager : "uses"
```

**Diagram sources**
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py#L1-L42)
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py#L1-L81)

**Section sources**
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py#L1-L42)

### Service Manager and Operational Coordination
The CoroutinesManager class in manager.py orchestrates various operational tasks for shop automation, including bid updates, statistics collection, and keyword parsing. It implements a decorator-based scheduling system that controls the frequency of operations.

```mermaid
classDiagram
class CoroutinesManager {
+WBApi _wb_api
+int shop_id
+WBShopDataManager _wb_shop_data_manager
+dict[int, list[CalculatedKeyword]] __keywords_for_advs
+dict[int, AdvSetting] | None _adv_settings_dict
+ClientSession _session
+update_cpm_bid() Coroutine
+update_common_sale_stat() Coroutine
+update_full_adv_stat() Coroutine
+update_advs_data_from_wb_to_pg() Coroutine
+update_cards_data_from_wb_to_pg() Coroutine
+parsing_keywords_run() Coroutine
+adv_settings_auto_update() Coroutine
+update_top_key_in_advs() Coroutine
}
class WBShopDataManager {
+WBCabinet _wb_cabinet
+str shop_id
+get_calculated_keywords(adv : AdvSetting) list[CalculatedKeyword]
+get_active_advs() list[AdvSetting]
}
class AdvSetting {
+int adv_id
+int search_adv_id
+list[int] nmids
+bool bidder_active
+bool bot_active
+bool auto_update_white_list
+bool auto_update_target_place
}
CoroutinesManager --> WBShopDataManager : "uses"
CoroutinesManager --> AdvSetting : "processes"
WBShopDataManager --> AdvSetting : "retrieves"
```

**Diagram sources**
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)
- [wb_shop_data_manager.py](file://app/modules/shop_runner/service_manager/wb_shop_data_manager/wb_shop_data_manager.py#L1-L49)

**Section sources**
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)

### Worker Process Implementation
The ShopWorker class manages the lifecycle of shop processing tasks, handling task creation, completion callbacks, and error cleanup. It maintains a dictionary of active tasks and coordinates with Redis to distribute work across multiple workers.

```mermaid
sequenceDiagram
participant Worker as ShopWorker
participant Redis as RedisShopManager
participant Task as run_shop_task
participant WBShop as WBShop
loop Continuous Monitoring
Worker->>Redis : get_next_free_shop_id()
alt Shop Available
Redis-->>Worker : shop_id
Worker->>Task : create_task(shop_id)
Task->>WBShop : Initialize with shop_id
Task->>Redis : add_done_callback()
WBShop->>Worker : Execute all operations
else No Shop Available
Redis-->>Worker : None
Worker->>Worker : Wait 15 seconds
end
end
WBShop->>Redis : renew_shop_ttl() every 30s
Task->>Worker : on_task_done()
Worker->>Redis : remove_shops() on completion
```

**Diagram sources**
- [worker.py](file://app/modules/shop_runner/shop_run_worker/worker/worker.py#L1-L79)
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py#L1-L81)

**Section sources**
- [worker.py](file://app/modules/shop_runner/shop_run_worker/worker/worker.py#L1-L79)

### Data Models
The data model for shop operations includes the ComplexAdv dataclass that combines advertising settings with their associated keywords, enabling coordinated processing of ad campaigns and their keyword sets.

```mermaid
classDiagram
class ComplexAdv {
+AdvSetting adv
+list[CalculatedKeyword] keywords
}
class AdvSetting {
+int adv_id
+str name
+bool bot_active
+bool bidder_active
+bool auto_update_white_list
+bool auto_update_target_place
}
class CalculatedKeyword {
+str text
+int nmid
+float cpm
+float ctr
+int position
+bool is_relevant
}
ComplexAdv --> AdvSetting
ComplexAdv --> CalculatedKeyword
```

**Diagram sources**
- [data_classes.py](file://app/modules/shop_runner/data_classes.py#L1-L13)
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)

**Section sources**
- [data_classes.py](file://app/modules/shop_runner/data_classes.py#L1-L13)

## Execution Flow and Scheduling

### Process Execution Flow
The execution flow begins with the main run() function that initializes the worker process and continuously monitors for shops that require processing. When a shop is identified, a dedicated task is created to handle all its operations.

```mermaid
flowchart TD
Start([Start run_process_func.run]) --> CreateSession["Create ClientSession"]
CreateSession --> InitTasks["Initialize active_tasks dict"]
InitTasks --> Loop["While True"]
Loop --> GetShops["Query DB for active shops"]
GetShops --> CheckShop["For each shop_id"]
CheckShop --> Exists{"Task exists?"}
Exists --> |No| CreateTask["Create run_shop_task"]
Exists --> |Yes| CheckDone["Task done?"]
CheckDone --> |Yes| Cleanup["Remove from active_tasks"]
CheckDone --> |No| Continue["Continue"]
CreateTask --> AddTask["Add to active_tasks"]
AddTask --> Sleep["Sleep 0.1s"]
Sleep --> NextShop["Next shop"]
NextShop --> CheckRemove{"Shop still active?"}
CheckRemove --> |No| CancelTask["Cancel task"]
CheckRemove --> |Yes| Continue
CancelTask --> Log["Log shop stopped"]
Log --> NextShop
Continue --> NextShop
NextShop --> EndLoop["End loop"]
EndLoop --> Sleep1["Sleep 1s"]
Sleep1 --> Loop
style Start fill:#9f9,stroke:#333
style EndLoop fill:#f99,stroke:#333
```

**Diagram sources**
- [run_process_func.py](file://app/modules/shop_runner/run_process_func.py#L1-L102)

**Section sources**
- [run_process_func.py](file://app/modules/shop_runner/run_process_func.py#L1-L102)

### Scheduling Mechanism
The system uses a decorator-based scheduling mechanism (@while_coroutine_decorator) to control the frequency of various operations. Different tasks have different update intervals based on their resource requirements and data freshness needs.

```mermaid
graph TD
Scheduling[Scheduling Intervals] --> UpdateCPM["update_cpm_bid: 3 times/min"]
Scheduling --> Keywords["parsing_keywords_run: 1 time/min"]
Scheduling --> CommonStat["update_common_sale_stat: 5 min"]
Scheduling --> FullStat["update_full_adv_stat: 5 min"]
Scheduling --> AdvData["update_advs_data_from_wb_to_pg: 1 min"]
Scheduling --> CardData["update_cards_data_from_wb_to_pg: 15 min"]
Scheduling --> SettingsUpdate["adv_settings_auto_update: 5 min"]
Scheduling --> TopKey["update_top_key_in_advs: 1 time/min"]
style UpdateCPM fill:#ff9,stroke:#333
style Keywords fill:#ff9,stroke:#333
style CommonStat fill:#9ff,stroke:#333
style FullStat fill:#9ff,stroke:#333
style AdvData fill:#9ff,stroke:#333
style CardData fill:#9ff,stroke:#333
style SettingsUpdate fill:#9ff,stroke:#333
style TopKey fill:#ff9,stroke:#333
```

**Diagram sources**
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)

## State Synchronization and Error Isolation

### State Synchronization with Redis
The system uses Redis for state synchronization across multiple worker processes, implementing a heartbeat mechanism to track active shops and prevent duplicate processing.

```mermaid
sequenceDiagram
participant Worker as ShopWorker
participant Redis as RedisShopManager
participant Shop as WBShop
Worker->>Redis : update_active_shops([shop_id])
Redis->>Redis : SADD active_shops shop_id
loop Heartbeat (Every 30s)
Shop->>Redis : renew_shop_ttl(shop_id)
Redis->>Redis : SETEX shops_heartbeat : shop_id TTL "1"
end
Worker->>Redis : get_next_free_shop_id()
Redis->>Redis : SMEMBERS active_shops
Redis->>Redis : SET shops_heartbeat : shop_id EX NX
Redis-->>Worker : shop_id or nil
Worker->>Redis : remove_shops([shop_id]) on completion
Redis->>Redis : SREM active_shops shop_id
Redis->>Redis : DEL shops_heartbeat : shop_id
```

**Diagram sources**
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py#L1-L81)
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py#L1-L42)

**Section sources**
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py#L1-L81)

### Error Isolation and Handling
The system implements comprehensive error isolation to ensure that failures in one shop's processing do not affect others. Each shop runs in its own task with dedicated exception handling.

```mermaid
flowchart TD
Start([Start run_shop_task]) --> Try["Try Block"]
Try --> GetAccess["Get access for shop"]
GetAccess --> CreateWBApi["Create WBApi"]
CreateWBApi --> CreateWBShop["Create WBShop"]
CreateWBShop --> RunWBShop["Run WBShop"]
RunWBShop --> Success["Task completes normally"]
Success --> End["Return None"]
Try --> StopException["StopShopUpdateException?"]
StopException --> |Yes| End
Try --> OtherException["Other Exception?"]
OtherException --> |Yes| LogError["Log error with exc_info"]
LogError --> Sleep["Sleep 1 second"]
Sleep --> Try
style Start fill:#9f9,stroke:#333
style Success fill:#9f9,stroke:#333
style End fill:#f99,stroke:#333
style LogError fill:#f99,stroke:#333
```

**Diagram sources**
- [run_process_func.py](file://app/modules/shop_runner/run_process_func.py#L1-L102)
- [worker.py](file://app/modules/shop_runner/shop_run_worker/worker/worker.py#L1-L79)

## Resource Allocation and Health Monitoring

### Resource Allocation Strategy
The system implements a distributed resource allocation strategy using Redis as a coordination point, ensuring that multiple worker processes can operate concurrently without conflict.

```mermaid
graph TD
subgraph "Worker 1"
W1[ShopWorker]
R1[RedisShopManager]
end
subgraph "Worker 2"
W2[ShopWorker]
R2[RedisShopManager]
end
subgraph "Redis"
ActiveShops[active_shops Set]
Heartbeats[shops_heartbeat:* Keys]
end
W1 --> R1
W2 --> R2
R1 --> ActiveShops
R2 --> ActiveShops
R1 --> Heartbeats
R2 --> Heartbeats
W1->>ActiveShops: get_next_free_shop_id()
W2->>ActiveShops: get_next_free_shop_id()
ActiveShops --> >W1: Returns shop_id if available
ActiveShops --> >W2: Returns nil if locked
style W1 fill:#f9f,stroke:#333
style W2 fill:#f9f,stroke:#333
style ActiveShops fill:#ff9,stroke:#333
style Heartbeats fill:#ff9,stroke:#333
```

**Diagram sources**
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py#L1-L81)
- [worker.py](file://app/modules/shop_runner/shop_run_worker/worker/worker.py#L1-L79)

### Health Monitoring Capabilities
The system includes built-in health monitoring through heartbeat mechanisms and comprehensive logging, allowing operators to track the status of all shop processing activities.

```mermaid
sequenceDiagram
participant Worker as ShopWorker
participant Redis as Redis
participant Monitor as Monitoring System
loop Every 30 seconds
Worker->>Redis : SETEX shops_heartbeat : shop_id TTL "1"
end
loop Every 5 minutes
Monitor->>Redis : KEYS shops_heartbeat : *
Redis-->>Monitor : List of active shops
Monitor->>Monitor : Compare with expected shops
Monitor->>Monitor : Alert on missing heartbeats
end
Worker->>Logger : Log task creation
Worker->>Logger : Log task completion
Worker->>Logger : Log errors with stack trace
Logger->>Monitoring : Forward logs to monitoring system
```

**Diagram sources**
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py#L1-L42)
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py#L1-L81)

## Operational Issues and Recovery Procedures

### Process Crash Recovery
The system is designed to recover gracefully from process crashes through its Redis-based state management and heartbeat system.

```mermaid
flowchart TD
Crash[Worker Process Crash] --> RedisDown["Redis server continues"]
RedisDown --> Heartbeats["Heartbeat keys expire after TTL"]
Heartbeats --> Available["Shop becomes available in active_shops"]
Available --> NewWorker["New worker process"]
NewWorker --> Detect["Detects available shop"]
Detect --> Process["Processes shop normally"]
Process --> Success["Operation continues"]
style Crash fill:#f99,stroke:#333
style Success fill:#9f9,stroke:#333
```

**Section sources**
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py#L1-L81)
- [wb_shop.py](file://app/modules/shop_runner/wb_shop.py#L1-L42)

### Data Inconsistency Handling
The system includes mechanisms to handle data inconsistencies, particularly in the shop configuration and advertising settings.

```mermaid
flowchart TD
Inconsistency[Data Inconsistency Detected] --> CheckActive["Check if shop in active_shops"]
CheckActive --> |Yes| Remove["Remove from active_shops"]
CheckActive --> |No| Continue["Continue processing"]
Remove --> Log["Log inconsistency"]
Log --> Retry["Retry after delay"]
Retry --> Validate["Validate data consistency"]
Validate --> |Valid| Process["Process normally"]
Validate --> |Invalid| Alert["Alert administrators"]
Alert --> Manual["Manual intervention required"]
style Inconsistency fill:#f99,stroke:#333
style Process fill:#9f9,stroke:#333
style Manual fill:#f99,stroke:#333
```

**Section sources**
- [run_process_func.py](file://app/modules/shop_runner/run_process_func.py#L1-L102)
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)

## Configuration and Command Propagation

### Shop Configuration Example
Shop configuration is managed through database records that define the operational parameters for each shop.

```mermaid
erDiagram
WBCABINET ||--o{ ADVSETTING : contains
WBCABINET {
string shop_id PK
string cabinet_name
boolean active
}
ADVSETTING }o--|| WBCABINET : belongs_to
ADVSETTING {
int adv_id PK
string shop_id FK
boolean bot_active
boolean bidder_active
boolean auto_update_white_list
boolean auto_update_target_place
int max_balance_adding_for_day
float auto_add_only_relevant_phrase_in_percent
float auto_update_target_place_in_percent
}
style WBCABINET fill:#9cf,stroke:#333
style ADVSETTING fill:#9cf,stroke:#333
```

**Section sources**
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)

### Command Propagation Flow
Operational commands propagate from user interfaces through the database to execution workers, enabling real-time control of shop operations.

```mermaid
sequenceDiagram
participant UI as User Interface
participant DB as PostgreSQL
participant Worker as ShopWorker
participant Shop as WBShop
UI->>DB : Update AdvSetting (bot_active=True)
DB-->>UI : Confirmation
loop Every 1 minute
Worker->>DB : Query active shops
DB-->>Worker : List of shops with bot_active=True
alt New shop detected
Worker->>Worker : Create run_shop_task
Worker->>Shop : Execute operations
end
end
UI->>DB : Update AdvSetting (bot_active=False)
DB-->>UI : Confirmation
Worker->>DB : Next query cycle
Worker->>Worker : Cancel existing task
Worker->>Worker : Log shop stopped
```

**Diagram sources**
- [run_process_func.py](file://app/modules/shop_runner/run_process_func.py#L1-L102)
- [manager.py](file://app/modules/shop_runner/service_manager/manager.py#L1-L262)

## Conclusion
The Shop Operations module provides a robust and scalable solution for automating Wildberries shop management. Through its distributed architecture, the system can concurrently manage multiple shops while maintaining isolation between them. The combination of Redis for state synchronization and PostgreSQL for persistent storage ensures data consistency and fault tolerance. The modular design allows for easy extension of functionality, while the comprehensive error handling and recovery mechanisms ensure reliable operation even in the face of failures. This architecture effectively balances performance, reliability, and maintainability for large-scale shop automation.