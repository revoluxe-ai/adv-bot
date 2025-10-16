# Keyword Parser Workers

<cite>
**Referenced Files in This Document**   
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py)
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py)
- [settings_master.py](file://app/settings/settings_master.py)
- [parsing_queue_mode.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_queue_mode.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
The Keyword Parser Workers system is designed to extract and analyze search terms from Wildberries by efficiently processing keyword parsing tasks. This system leverages a distributed architecture with Redis-based queues for task coordination, multiprocessing for parallel execution, and intelligent page prioritization for optimized parsing. The core components include the parser worker, task management system, and Redis-backed coordination logic that enables scalable and fault-tolerant keyword analysis. This document details the system's architecture, implementation, and operational characteristics.

## Project Structure
The keyword parsing system is organized within the `app/modules/wb_keywords_parser/` directory with a clear separation of concerns. The system consists of worker processes, task management components, Redis coordination modules, and parsing logic. The structure enables modular development and maintenance while supporting distributed deployment across multiple instances.

```mermaid
graph TD
subgraph "Keyword Parser System"
PW[parser_worker.py]
PT[parsing_task.py]
GPQM[global_parsing_queue_manager.py]
PPM[parsing_page_queue_manager.py]
PFRM[parsing_found_redis_manager.py]
P[parser.py]
PQM[parsing_queue_manager.py]
S[settings_master.py]
PQM2[parsing_queue_mode.py]
end
PW --> GPQM
GPQM --> PT
PPM --> PFRM
P --> PPM
P --> PT
S --> PW
S --> PPM
PQM2 --> PPM
```

**Diagram sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py)

**Section sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py)
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py)

## Core Components
The keyword parsing system consists of several core components that work together to extract and analyze search terms from Wildberries. The ParserWorker manages multiprocessing execution, GlobalParsingQueueManager handles task distribution through Redis, ParsingTask defines the unit of work, and ParsingPageQueueManager coordinates intelligent page parsing based on historical data. These components are designed to work together in a distributed environment, enabling horizontal scaling and efficient resource utilization.

**Section sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py#L1-L25)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)

## Architecture Overview
The keyword parsing system follows a distributed worker pattern with Redis serving as the central coordination point. Multiple parser workers connect to a shared Redis instance to retrieve parsing tasks from a priority queue. Each task contains a keyword and a set of nmids (product identifiers) to locate. The system uses an intelligent parsing strategy that prioritizes pages based on historical success rates, minimizing redundant requests and optimizing parsing efficiency.

```mermaid
graph TD
subgraph "Parser Workers"
W1[Parser Worker 1]
W2[Parser Worker 2]
W3[Parser Worker N]
end
subgraph "Redis Coordination"
Q[Task Queue]
TD[Task Data]
TI[Text Index]
FP[Found Pages]
NFP[Not Found Pages]
end
subgraph "External Systems"
WB[Wildberries API]
CH[ClickHouse]
R[Redis Storage]
end
W1 --> Q
W2 --> Q
W3 --> Q
Q --> TD
Q --> TI
W1 --> FP
W1 --> NFP
W2 --> FP
W2 --> NFP
W3 --> FP
W3 --> NFP
W1 --> WB
W2 --> WB
W3 --> WB
W1 --> CH
W2 --> CH
W3 --> CH
W1 --> R
W2 --> R
W3 --> R
style W1 fill:#f9f,stroke:#333
style W2 fill:#f9f,stroke:#333
style W3 fill:#f9f,stroke:#333
style Q fill:#bbf,stroke:#333
style TD fill:#bbf,stroke:#333
style TI fill:#bbf,stroke:#333
style FP fill:#bbf,stroke:#333
style NFP fill:#bbf,stroke:#333
```

**Diagram sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py)

## Detailed Component Analysis

### Parser Worker Analysis
The ParserWorker class implements a multiprocessing design that allows for concurrent processing of keyword parsing tasks. Each worker maintains a pool of parallel tasks (default: 3) that independently retrieve tasks from the shared Redis queue. The worker uses an asyncio.Event-based stop mechanism for graceful shutdown and employs a distributed lock to prevent race conditions when retrieving tasks from the queue.

```mermaid
classDiagram
class ParserWorker {
-queue_manager : GlobalParsingQueueManager
-_max_parallel_tasks : int
-_stop_event : asyncio.Event
-_tasks : set[Task[None]]
+__init__(max_parallel_tasks : int)
+run() : Coroutine
+stop() : Coroutine
+_run() : Coroutine
+_process_task(task : ParsingTask) : Coroutine
}
class GlobalParsingQueueManager {
+queue_key : str
+task_data_prefix : str
+text_index_prefix : str
+add_or_update_task(text : str, nmids : set[int]) : Coroutine[str]
+get_next_task() : Coroutine[ParsingTask | None]
-_get_task_id(text : str) : str
}
ParserWorker --> GlobalParsingQueueManager : "uses"
```

**Diagram sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)

### Parsing Task Analysis
The ParsingTask dataclass represents the unit of work in the keyword parsing system. Each task contains a keyword to search for and a set of nmids (product identifiers) that need to be located within the search results. The task includes a computed property for generating a unique ID based on the keyword, enabling efficient deduplication and tracking. Tasks may also include an optional adv_id_order field for campaign tracking purposes.

```mermaid
classDiagram
class ParsingTask {
+keyword : str
+nmids : set[int]
+adv_id_order : str | None
+id : str
}
note right of ParsingTask
The id property generates a SHA1 hash
of the keyword, truncated to 12 characters
for efficient indexing and deduplication
end note
```

**Diagram sources**
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py#L1-L25)

### Task Queue Manager Analysis
The GlobalParsingQueueManager class manages the Redis-based task queue system that coordinates work distribution among parser workers. It uses a sorted set (ZSET) in Redis to maintain task priority based on insertion time, ensuring first-in-first-out processing. The manager implements atomic operations using Redis pipelines to safely add or update tasks while preventing race conditions in distributed environments.

```mermaid
sequenceDiagram
participant Client
participant GPQM as GlobalParsingQueueManager
participant Redis
Client->>GPQM : add_or_update_task(text, nmids)
GPQM->>Redis : MULTI/PIPELINE
Redis-->>GPQM : Pipeline context
GPQM->>Redis : SET task : data : {id} {json}
GPQM->>Redis : ZADD task : queue {id} {timestamp}
GPQM->>Redis : SADD index : text : {hash} {id}
Redis-->>GPQM : EXEC
GPQM-->>Client : task_id
Client->>GPQM : get_next_task()
GPQM->>Redis : EVAL Lua script
Redis-->>GPQM : task_data or nil
alt task exists
GPQM->>GPQM : Parse JSON
GPQM->>GPQM : Create ParsingTask
GPQM-->>Client : ParsingTask
else queue empty
GPQM-->>Client : None
end
```

**Diagram sources**
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)

### Parsing Page Queue Manager Analysis
The ParsingPageQueueManager implements intelligent page prioritization logic that optimizes the parsing process by leveraging historical data. Instead of processing pages sequentially, it analyzes previous parsing results to create an optimized page processing order: pages where products were previously found are processed first, followed by pages with unknown status, and finally pages where products were not previously found.

```mermaid
flowchart TD
Start([Get Parsing Queue]) --> CheckMode["Check PARSING_QUEUE_MODE"]
CheckMode --> |SIMPLE_QUEUE| ReturnSimple["Return 1 to max_pages"]
CheckMode --> |SMART_QUEUE| Initialize["Initialize page sets"]
Initialize --> FoundPages["found_pages_all = []"]
Initialize --> NotFoundPages["not_found_pages_all = []"]
Initialize --> RemainingPages["remaining_pages_all = set(1..max_pages)"]
FoundPages --> ProcessLoop["For each nmid in need_nmids"]
NotFoundPages --> ProcessLoop
RemainingPages --> ProcessLoop
ProcessLoop --> GetFound["Get found pages for text+nmid"]
ProcessLoop --> GetNotFound["Get not found pages for text+nmid"]
GetFound --> UpdateFound["Extend found_pages_all"]
GetNotFound --> UpdateNotFound["Extend not_found_pages_all"]
UpdateFound --> UpdateRemaining["Remove from remaining_pages_all"]
UpdateNotFound --> UpdateRemaining
UpdateRemaining --> NextNmid{"More nmids?"}
NextNmid --> |Yes| ProcessLoop
NextNmid --> |No| ShuffleRemaining["Shuffle remaining_pages_all"]
ShuffleRemaining --> CreateFinal["Create final queue:<br/>found + remaining + not_found"]
CreateFinal --> CheckLength["Check queue length"]
CheckLength --> |Incomplete| AddMissing["Add missing pages"]
CheckLength --> |Complete| ReturnQueue["Return final queue"]
AddMissing --> ReturnQueue
ReturnSimple --> End([Return])
ReturnQueue --> End
```

**Diagram sources**
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L86)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L30)

## Dependency Analysis
The keyword parsing system has a well-defined dependency structure that enables modularity and testability. The core dependencies are organized in a layered architecture with clear separation between worker processes, task management, and data storage components.

```mermaid
graph TD
PW[ParserWorker] --> GPQM[GlobalParsingQueueManager]
PW --> PT[ParsingTask]
PW --> P[ParserService]
GPQM --> PT
GPQM --> BRM[BaseRedis]
PPM[ParsingPageQueueManager] --> PFRM[ParsingFoundRedisManager]
PPM --> PQM[ParsingQueueMode]
PPM --> S[Settings]
P --> PPM
P --> PT
P --> RM[RedisManager]
P --> DM[DataManager]
PFRM --> BRM
S --> PW
S --> PPM
style PW fill:#f9f,stroke:#333
style GPQM fill:#bbf,stroke:#333
style PT fill:#bbf,stroke:#333
style PPM fill:#bbf,stroke:#333
style PFRM fill:#bbf,stroke:#333
style P fill:#f96,stroke:#333
style S fill:#9f9,stroke:#333
style BRM fill:#69f,stroke:#333
style RM fill:#69f,stroke:#333
style DM fill:#69f,stroke:#333
```

**Diagram sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py)

**Section sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py)

## Performance Considerations
The keyword parsing system incorporates several performance optimizations to maximize throughput and minimize resource consumption. The multiprocessing design allows for concurrent task processing, with configurable parallelism through the max_parallel_tasks parameter. The intelligent page queueing system reduces redundant API calls by prioritizing pages based on historical success rates. Task deduplication prevents redundant processing of identical keywords, while atomic Redis operations ensure data consistency in distributed environments. The system also implements exponential backoff for error recovery, preventing cascading failures during temporary service disruptions.

**Section sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L86)
- [settings_master.py](file://app/settings/settings_master.py)

## Troubleshooting Guide
Common issues in the keyword parsing system typically relate to Redis connectivity, task processing bottlenecks, or API rate limiting. Monitoring Redis queue length can help identify processing backlogs, while tracking worker logs can reveal individual task failures. The system's logging includes detailed information about task processing, including queue operations, page parsing attempts, and error conditions. For performance tuning, adjusting the PARSING_KEYWORDS_DELAY_BETWEEN_TASKS setting can help manage API request rates, while modifying the MAX_PAGE_LIMIT_PARSER_WORKER parameter can control parsing depth. The SMART_QUEUE mode should be used in production to optimize parsing efficiency, while SIMPLE_QUEUE mode can be useful for debugging and testing.

**Section sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L86)
- [settings_master.py](file://app/settings/settings_master.py)

## Conclusion
The Keyword Parser Workers system provides a robust and scalable solution for extracting and analyzing search terms from Wildberries. Its distributed architecture, intelligent parsing strategies, and Redis-based coordination enable efficient processing of large volumes of keyword data. The system's modular design allows for easy configuration and scaling, while its fault-tolerant mechanisms ensure reliable operation in production environments. By leveraging multiprocessing, task deduplication, and intelligent page prioritization, the system maximizes parsing throughput while minimizing redundant API calls and resource consumption.