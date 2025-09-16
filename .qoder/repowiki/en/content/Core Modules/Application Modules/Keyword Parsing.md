# Keyword Parsing

<cite>
**Referenced Files in This Document**   
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py)
- [task_queue_manager.py](file://app/modules/wb_keywords_parser/task_queue_manager.py)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py)
- [parsing_queue_settings.py](file://app/settings/parsing_queue_settings.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Core Components](#core-components)
3. [Architecture Overview](#architecture-overview)
4. [Detailed Component Analysis](#detailed-component-analysis)
5. [Task Lifecycle and Queue Management](#task-lifecycle-and-queue-management)
6. [Parsing Workflow and Data Enrichment](#parsing-workflow-and-data-enrichment)
7. [Redis Integration and Fault Tolerance](#redis-integration-and-fault-tolerance)
8. [Error Handling Strategies](#error-handling-strategies)
9. [Performance Considerations](#performance-considerations)
10. [Configuration and Scaling](#configuration-and-scaling)
11. [Integration with Campaign Optimization](#integration-with-campaign-optimization)

## Introduction
The Keyword Parsing module is a critical component of the advertising automation system, responsible for extracting and analyzing keyword positioning data from Wildberries search results. This document provides a comprehensive analysis of the wb_keywords_parser implementation, detailing the scraping architecture, distributed task execution, and integration with downstream campaign optimization systems. The system is designed for high reliability, fault tolerance, and scalability, leveraging Redis for task persistence and distributed coordination.

## Core Components

The Keyword Parsing module consists of several interconnected components that work together to process keyword parsing tasks efficiently. The core components include the parsing task model, distributed worker architecture, queue management systems, and page-level parsing logic. These components are designed to handle large volumes of keyword parsing requests while maintaining data integrity and system reliability.

**Section sources**
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py#L1-L23)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)

## Architecture Overview

The keyword parsing architecture follows a distributed worker pattern with centralized queue management. Tasks are submitted to a Redis-backed priority queue, where they are processed by multiple parser workers running in parallel. The architecture is designed for horizontal scalability, allowing additional workers to be added as parsing demand increases.

```mermaid
graph TD
subgraph "Task Submission"
Client["External Systems<br/>(Campaign Manager, UI)"]
end
subgraph "Queue Management"
GPQM["GlobalParsingQueueManager<br/>Handles task deduplication<br/>and prioritization"]
TQM["TaskQueueManager<br/>Manages task lifecycle"]
end
subgraph "Processing Layer"
PW["ParserWorker<br/>Distributed task execution"]
P["ParserService<br/>Page scraping logic"]
end
subgraph "Data Storage"
Redis["Redis<br/>Task persistence<br/>and coordination"]
ClickHouse["ClickHouse<br/>Position data storage"]
FoundRM["ParsingFoundRedisManager<br/>Page state tracking"]
end
Client --> |Submit task| GPQM
GPQM --> |Add/Update| TQM
TQM --> |Priority queue| PW
PW --> |Process| P
P --> |Extract data| FoundRM
P --> |Store results| ClickHouse
P --> |Cache results| Redis
FoundRM --> |Track state| Redis
style GPQM fill:#f9f,stroke:#333
style TQM fill:#f9f,stroke:#333
style PW fill:#bbf,stroke:#333
style P fill:#bbf,stroke:#333
```

**Diagram sources**
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)
- [task_queue_manager.py](file://app/modules/wb_keywords_parser/task_queue_manager.py#L1-L176)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)

## Detailed Component Analysis

### Parsing Task Model
The ParsingTask dataclass represents the fundamental unit of work in the keyword parsing system. Each task contains a keyword to search for, a set of nmids (product identifiers) to track, and an optional advertising order ID for campaign association.

```mermaid
classDiagram
class ParsingTask {
+keyword : str
+nmids : Set[int]
+adv_id_order : Optional[str]
+id : str
}
note right of ParsingTask
Represents a single keyword parsing request
keyword : search term to parse
nmids : product IDs to track in results
adv_id_order : optional campaign association
id : SHA1 hash of keyword (first 12 chars)
end
```

**Diagram sources**
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py#L1-L23)

### Parser Worker Implementation
The ParserWorker class manages the distributed execution of parsing tasks. It maintains a pool of concurrent workers that pull tasks from the global queue and process them using the ParserService.

```mermaid
classDiagram
class ParserWorker {
-queue_manager : GlobalParsingQueueManager
-max_parallel_tasks : int
-stop_event : asyncio.Event
-tasks : set[Task]
+run() : Coroutine
+stop() : Coroutine
-_run() : Coroutine
-_process_task(task : ParsingTask) : Coroutine
}
class GlobalParsingQueueManager {
+queue_key : str
+task_data_prefix : str
+text_index_prefix : str
+add_or_update_task(text : str, nmids : Set[int]) : str
+get_next_task() : Optional[ParsingTask]
-_get_task_id(text : str) : str
}
ParserWorker --> GlobalParsingQueueManager : "uses"
ParserWorker --> ParsingTask : "processes"
ParserWorker --> ParserService : "delegates"
```

**Diagram sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)

### Page-Level Parsing Logic
The ParserService handles the actual HTTP requests to Wildberries search endpoints and extracts position data from the responses. It manages pagination and processes the JSON response to create structured position records.

```mermaid
sequenceDiagram
participant Worker as ParserWorker
participant Service as ParserService
participant HTTP as Wildberries API
participant Redis as ParsingFoundRedisManager
Worker->>Service : parse_keywords_from_wb(text, page, total_pages)
Service->>HTTP : GET /search?query={text}&page={page}
HTTP-->>Service : JSON response
Service->>Service : Extract products, cluster, preset, total_items
Service->>Service : Calculate real_position for each product
Service->>Service : Determine adv_type from log data
Service->>Redis : set_cluster_and_preset(text, cluster, preset)
Service->>Service : Create WBItemPosition objects
Service-->>Worker : List[WBItemPosition]
```

**Diagram sources**
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L31)

## Task Lifecycle and Queue Management

The task lifecycle in the keyword parsing system follows a well-defined flow from submission to completion. Tasks are managed through a combination of the TaskQueueManager and GlobalParsingQueueManager, which provide different levels of queue functionality.

```mermaid
flowchart TD
A["Submit Task\nadd_or_update_task()"] --> B{"Task Exists?"}
B --> |No| C["Create New Task\nSet task data in Redis\nAdd to ZSET queue"]
B --> |Yes| D["Update Existing Task\nMerge nmids sets\nPreserve queue position"]
C --> E["Task in Queue\nWaiting for worker"]
D --> E
E --> F["Worker Claims Task\nLua script removes from queue\nRetrieves task data"]
F --> G{"Task Processing\nSuccessful?"}
G --> |Yes| H["Complete\nNo cleanup needed"]
G --> |No| I["Error Handling\nTask lost but data preserved\nCan be resubmitted"]
H --> J["Results Stored\nIn Redis and ClickHouse"]
I --> J
J --> K["Update Page State\nIn ParsingFoundRedisManager"]
style A fill:#cfc,stroke:#333
style C fill:#cfc,stroke:#333
style D fill:#cfc,stroke:#333
style H fill:#cfc,stroke:#333
style I fill:#fcc,stroke:#333
```

**Diagram sources**
- [task_queue_manager.py](file://app/modules/wb_keywords_parser/task_queue_manager.py#L1-L176)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L31)

**Section sources**
- [task_queue_manager.py](file://app/modules/wb_keywords_parser/task_queue_manager.py#L1-L176)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)

## Parsing Workflow and Data Enrichment

The parsing workflow is designed to efficiently extract keyword positioning data while minimizing redundant requests. The system uses intelligent page queue management to prioritize pages based on previous parsing results.

```mermaid
flowchart TD
A["Start Parsing\nadd_wb_positions()"] --> B["Initialize State\nTotalPages, stop_event,\n catch_any_position, checked_pages"]
B --> C["Get Parsing Queue\nget_parsing_queue()"]
C --> D{"More Pages\n& nmids to check?"}
D --> |Yes| E["Process Next Page\nadd_positions_from_page()"]
E --> F["Parse Page Data\n__parse_keywords_from_wb()"]
F --> G{"Valid Data\nReceived?"}
G --> |Yes| H["Extract Positions\nCreate WBItemPosition objects"]
G --> |No| I["Handle Error\nLog issue, continue"]
H --> J["Update Page State\nadd_found_not_found_page()"]
J --> K["Store Results\nadd_wb_positions_to_all_bases()"]
K --> L["Check Completion\nAny nmids left?"]
L --> |Yes| M["Update total_pages\nfrom response"]
M --> N["Apply Rate Limit\ndelay between requests"]
N --> O["Mark Page Checked"]
O --> D
L --> |No| P["Set stop_event"]
P --> D
D --> |No| Q["Handle Remaining nmids\nCreate not_found positions"]
Q --> R["Complete Parsing"]
style A fill:#cfc,stroke:#333
style H fill:#cfc,stroke:#333
style K fill:#cfc,stroke:#333
style R fill:#cfc,stroke:#333
```

**Diagram sources**
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L68)

**Section sources**
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L68)

## Redis Integration and Fault Tolerance

Redis plays a central role in the keyword parsing system, providing task persistence, distributed coordination, and state management. The system is designed to be resilient to failures, with multiple mechanisms to ensure data integrity.

```mermaid
erDiagram
TASK_QUEUE ||--o{ TASK_DATA : contains
TASK_QUEUE ||--o{ TEXT_INDEX : indexes
PAGE_STATE ||--o{ FOUND_PAGES : tracks
PAGE_STATE ||--o{ NOT_FOUND_PAGES : tracks
TASK_QUEUE {
string queue_key PK
int task_id FK
timestamp score
}
TASK_DATA {
string task_id PK
string text
int[] nmids
}
TEXT_INDEX {
string text_hash PK
string task_id FK
}
FOUND_PAGES {
string key PK
int page
timestamp score
}
NOT_FOUND_PAGES {
string key PK
int page
timestamp score
}
note as RedisNote
Redis keys:
parser:task:queue - ZSET with task IDs and timestamps
parser:task:data:{task_id} - JSON task data
parser:task:index:text:{text} - SET with task IDs
found_pages:{text}:{nmid} - ZSET with page numbers
not_found_pages:{text}:{nmid} - ZSET with page numbers
end
```

**Diagram sources**
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)
- [task_queue_manager.py](file://app/modules/wb_keywords_parser/task_queue_manager.py#L1-L176)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L31)

## Error Handling Strategies

The system implements comprehensive error handling to deal with various failure scenarios, including network issues, API changes, and system errors. The error handling strategy prioritizes data preservation and task resiliency.

```mermaid
stateDiagram-v2
[*] --> Idle
Idle --> ProcessingTask : get_next_task()
ProcessingTask --> ExtractData : parse_keywords_from_wb()
ExtractData --> HandleNetworkError : HTTP request fails
ExtractData --> ProcessResponse : Response received
ProcessResponse --> ValidateData : Check payloadVersion
ValidateData --> HandleParseError : Invalid data format
ValidateData --> ExtractProducts : Data valid
ExtractProducts --> CreatePositions : Process each product
CreatePositions --> UpdateState : add_found_not_found_page()
CreatePositions --> HandleKeyError : Missing required fields
HandleNetworkError --> Retry : wait and retry
HandleParseError --> LogError : Record issue
HandleKeyError --> SkipProduct : Continue with next product
Retry --> ExtractData : retry request
LogError --> UpdateState : Continue processing
SkipProduct --> CreatePositions : Next product
UpdateState --> StoreResults : add_wb_positions_to_all_bases()
StoreResults --> CheckCompletion : Any nmids left?
CheckCompletion --> SetStopEvent : No nmids left
CheckCompletion --> Continue : More nmids to check
SetStopEvent --> Complete : Finish task
Continue --> CheckPageLimit : Page limit reached?
CheckPageLimit --> ProcessNextPage : Get next page
CheckPageLimit --> Complete : Limit reached
ProcessNextPage --> ExtractData : Next page
Complete --> [*]
note right of HandleNetworkError
Retries with exponential backoff
Preserves task in queue
end
note right of HandleParseError
Logs detailed error info
Continues with available data
end
```

**Diagram sources**
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)

**Section sources**
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)

## Performance Considerations

The keyword parsing system is designed with performance and scalability in mind. Several mechanisms are in place to optimize resource usage and handle high volumes of parsing requests.

```mermaid
graph TD
A["Performance Optimization"] --> B["Concurrency Control"]
A --> C["Rate Limiting"]
A --> D["Intelligent Page Ordering"]
A --> E["Task Deduplication"]
A --> F["Efficient Redis Operations"]
B --> B1["max_parallel_tasks"]
B --> B2["asyncio.Lock for queue access"]
B --> B3["Parallel worker processes"]
C --> C1["delay parameter"]
C --> C2["worker_sleep_interval"]
C --> C3["Respect API limits"]
D --> D1["Prioritize found pages"]
D --> D2["Randomize unknown pages"]
D --> D3["Check not-found pages last"]
E --> E1["SHA1 task ID generation"]
E --> E2["Merge nmids on duplicate tasks"]
E --> E3["Atomic Redis operations"]
F --> F1["Pipeline operations"]
F --> F2["Lua scripts for atomicity"]
F --> F3["Efficient data structures"]
style B fill:#cfc,stroke:#333
style C fill:#cfc,stroke:#333
style D fill:#cfc,stroke:#333
style E fill:#cfc,stroke:#333
style F fill:#cfc,stroke:#333
```

**Diagram sources**
- [parsing_queue_settings.py](file://app/settings/parsing_queue_settings.py#L1-L31)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)

**Section sources**
- [parsing_queue_settings.py](file://app/settings/parsing_queue_settings.py#L1-L31)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)

## Configuration and Scaling

The system provides configurable parameters to adjust performance characteristics based on deployment requirements and resource availability. These settings allow the system to be tuned for different environments and scaling needs.

```mermaid
classDiagram
class ParsingQueueSettings {
+redis_queue_key : str
+redis_task_data_prefix : str
+redis_text_index_prefix : str
+worker_sleep_interval : float
+worker_concurrency : int
+worker_max_retries : int
+worker_retry_delay : float
+task_ttl_seconds : int
+arq_queue_name : str
+arq_default_priority : int
}
note right of ParsingQueueSettings
Configuration options :
- Redis key prefixes
- Worker concurrency and timing
- Task TTL and retry policies
- ARQ integration settings
Configurable via environment variables
with PARSING_QUEUE_ prefix
end
```

**Diagram sources**
- [parsing_queue_settings.py](file://app/settings/parsing_queue_settings.py#L1-L31)

**Section sources**
- [parsing_queue_settings.py](file://app/settings/parsing_queue_settings.py#L1-L31)

## Integration with Campaign Optimization

The parsed keyword data feeds directly into campaign optimization systems, providing real-time insights into keyword performance and enabling automated bidding strategies. The integration is designed to be seamless and reliable.

```mermaid
flowchart LR
A["Keyword Parsing System"] --> B["Data Storage"]
B --> C["Position Data"]
C --> D["Campaign Optimization"]
D --> E["Bid Adjustments"]
D --> F["Keyword Relevance"]
D --> G["Performance Analytics"]
subgraph "Keyword Parsing System"
direction TB
PW["ParserWorker"]
P["ParserService"]
R["Redis"]
end
subgraph "Data Storage"
direction TB
CH["ClickHouse"]
Redis2["Redis Cache"]
end
subgraph "Campaign Optimization"
direction TB
CM["Campaign Manager"]
AM["Ad Manager"]
RM["Reporting"]
end
PW --> |Positions| CH
PW --> |Positions| Redis2
CH --> |Query| CM
Redis2 --> |Real-time| CM
CM --> |Optimize| AM
CM --> |Generate| RM
style PW fill:#bbf,stroke:#333
style P fill:#bbf,stroke:#333
style R fill:#bbf,stroke:#333
style CH fill:#cfc,stroke:#333
style Redis2 fill:#cfc,stroke:#333
style CM fill:#ffc,stroke:#333
style AM fill:#ffc,stroke:#333
style RM fill:#ffc,stroke:#333
```

**Diagram sources**
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L31)

**Section sources**
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L343)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L31)