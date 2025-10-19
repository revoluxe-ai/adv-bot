# WB Keywords Parser

<cite>
**Referenced Files in This Document**   
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py)
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py)
- [task_queue_manager.py](file://app/modules/wb_keywords_parser/task_queue_manager.py)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py)
- [parsing_queue_mode.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_queue_mode.py)
- [settings_master.py](file://app/settings/settings_master.py)
- [__init__.py](file://app/modules/shop_runner/service_manager/services/parsing_keywords_from_wb/__init__.py)
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
The WB Keywords Parser module is a critical component of the Wildberries advertising automation system, responsible for extracting and analyzing keyword data from the Wildberries marketplace. This module implements a sophisticated parsing system that handles keyword extraction, position tracking, and data storage with high efficiency and reliability. The system is designed to manage large-scale keyword extraction operations while coordinating multiple workers through Redis-based task distribution. It features intelligent parsing queue management, dynamic page crawling, and robust error handling to ensure reliable operation in the face of marketplace changes, rate limiting, and other challenges.

## Project Structure
The WB Keywords Parser module is organized in a modular structure within the application's modules directory. The core functionality is contained in the `wb_keywords_parser` package, which includes several subcomponents for different aspects of the parsing process.

```mermaid
graph TD
subgraph "WB Keywords Parser Module"
PT["parsing_task.py<br/>ParsingTask model"]
GPQM["global_parsing_queue_manager.py<br/>Task coordination"]
PW["parser_worker.py<br/>Worker implementation"]
P["wb_parser/parser.py<br/>Core parsing logic"]
PF["parsing_found_redis_manager.py<br/>Redis storage manager"]
PQM["parsing_page_queue_manager.py<br/>Page queue management"]
TQM["task_queue_manager.py<br/>Task queue operations"]
PQM2["parsing_queue_mode.py<br/>Parsing strategy"]
end
PT --> GPQM
GPQM --> PW
P --> PW
PF --> P
PQM --> P
TQM --> GPQM
PQM2 --> PQM
```

**Diagram sources**
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py#L1-L25)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L352)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L30)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L86)
- [task_queue_manager.py](file://app/modules/wb_keywords_parser/task_queue_manager.py#L1-L177)
- [parsing_queue_mode.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_queue_mode.py#L1-L7)

**Section sources**
- [app/modules/wb_keywords_parser](file://app/modules/wb_keywords_parser)

## Core Components
The WB Keywords Parser module consists of several core components that work together to extract and analyze keyword data from the Wildberries marketplace. The system is built around a worker-based architecture that processes parsing tasks from a Redis-backed queue. Each parsing task contains a keyword and a set of nmids (product identifiers) to track. The parser makes HTTP requests to Wildberries search endpoints to retrieve product listings and extract position data for the specified keywords and products. The extracted data is then stored in both Redis and ClickHouse databases for fast access and long-term analysis. The system implements intelligent queue management that prioritizes pages based on previous parsing results, optimizing the parsing process by focusing on pages where products were previously found or not found.

**Section sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py#L1-L25)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L352)

## Architecture Overview
The WB Keywords Parser follows a distributed worker architecture with Redis serving as the central coordination point. The system consists of multiple parser workers that consume tasks from a shared Redis queue, process them by crawling Wildberries search results, and store the extracted data in persistent storage.

```mermaid
graph TD
subgraph "Task Management"
TQM["Task Queue Manager<br/>Manages task lifecycle"]
GPQM["Global Parsing Queue Manager<br/>Coordinates task distribution"]
end
subgraph "Workers"
PW1["Parser Worker 1"]
PW2["Parser Worker 2"]
PW3["Parser Worker N"]
end
subgraph "Data Storage"
Redis["Redis<br/>Task queue & caching"]
ClickHouse["ClickHouse<br/>Persistent storage"]
end
subgraph "Parsing Logic"
P["Parser Service<br/>Crawling & extraction"]
PQM["Parsing Queue Manager<br/>Page prioritization"]
PFM["Parsing Found Manager<br/>Page tracking"]
end
Client --> |Add tasks| TQM
TQM --> |Enqueue| Redis
Redis --> |Dequeue| GPQM
GPQM --> |Assign| PW1
GPQM --> |Assign| PW2
GPQM --> |Assign| PW3
PW1 --> |Process| P
PW2 --> |Process| P
PW3 --> |Process| P
P --> |Page queue| PQM
PQM --> |Page results| PFM
P --> |Extracted data| ClickHouse
PFM --> |Page status| Redis
P --> |Real-time data| Redis
style TQM fill:#f9f,stroke:#333
style GPQM fill:#f9f,stroke:#333
style PW1 fill:#f9f,stroke:#333
style PW2 fill:#f9f,stroke:#333
style PW3 fill:#f9f,stroke:#333
style Redis fill:#bbf,stroke:#333
style ClickHouse fill:#bbf,stroke:#333
style P fill:#9f9,stroke:#333
style PQM fill:#9f9,stroke:#333
style PFM fill:#9f9,stroke:#333
```

**Diagram sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L352)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L86)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L30)

## Detailed Component Analysis

### Parser Worker Implementation
The ParserWorker class is responsible for processing parsing tasks from the queue and executing the actual crawling operations. It runs multiple concurrent workers to maximize throughput while respecting rate limits.

```mermaid
classDiagram
class ParserWorker {
+queue_manager : GlobalParsingQueueManager
+_max_parallel_tasks : int
+_stop_event : asyncio.Event
+_tasks : set[Task[None]]
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
+__init__()
+add_or_update_task(text : str, nmids : set[int]) : Coroutine[str]
+get_next_task() : Coroutine[ParsingTask | None]
}
class ParsingTask {
+keyword : str
+nmids : set[int]
+adv_id_order : str | None
+id : str
}
ParserWorker --> GlobalParsingQueueManager : "uses"
ParserWorker --> ParsingTask : "processes"
GlobalParsingQueueManager --> ParsingTask : "returns"
```

**Diagram sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py#L1-L25)

### Keyword Parsing Workflow
The keyword parsing process follows a structured workflow that begins with task retrieval and ends with data persistence. The system implements a sophisticated page crawling strategy that adapts based on previous parsing results.

```mermaid
sequenceDiagram
participant Worker as ParserWorker
participant Queue as GlobalParsingQueueManager
participant Parser as ParserService
participant PageQueue as ParsingQueueManager
participant Redis as ParsingFoundRedisManager
participant Storage as Data Storage
Worker->>Queue : get_next_task()
Queue-->>Worker : ParsingTask
Worker->>Worker : _process_task()
Worker->>Parser : add_wb_positions()
Parser->>PageQueue : get_parsing_queue()
PageQueue->>Redis : get_found_pages()
PageQueue->>Redis : get_not_found_pages()
Redis-->>PageQueue : Page lists
PageQueue-->>Parser : Ordered page queue
loop For each page
Parser->>Parser : _add_positions_from_page()
Parser->>Wildberries : HTTP GET request
Wildberries-->>Parser : Search results
Parser->>Parser : parse_keywords_from_wb()
Parser->>Redis : add_last_found_page()
Parser->>Redis : add_last_not_found_page()
Parser->>Storage : add_wb_positions_to_all_bases()
end
Parser-->>Worker : Completion
Worker->>Queue : Next task
```

**Diagram sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L352)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L86)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L30)

### Parsing Queue Management
The parsing system implements intelligent queue management that optimizes the crawling process by prioritizing pages based on historical data. This reduces unnecessary requests and improves parsing efficiency.

```mermaid
flowchart TD
Start([Start Parsing]) --> GetQueue["Get parsing queue<br/>get_parsing_queue()"]
GetQueue --> CheckMode{"Parsing mode?"}
CheckMode --> |SIMPLE_QUEUE| Simple["Return all pages<br/>1 to max_pages"]
CheckMode --> |SMART_QUEUE| Smart["Process historical data"]
Smart --> Init["Initialize tracking sets"]
Init --> LoopNmid["For each nmid in need_nmids"]
LoopNmid --> GetFound["Get found pages from Redis"]
GetFound --> GetNotFound["Get not found pages from Redis"]
GetNotFound --> UpdateSets["Update found_pages_all,<br/>not_found_pages_all,<br/>remaining_pages_all"]
LoopNmid --> CheckAllNmids{"All nmids processed?"}
CheckAllNmids --> |No| LoopNmid
CheckAllNmids --> |Yes| Combine["Combine page lists:<br/>found + remaining + not_found"]
Combine --> Deduplicate["Remove duplicates<br/>OrderedDict.fromkeys()"]
Deduplicate --> CheckCount{"Queue length = max_pages?"}
CheckCount --> |No| AddMissing["Add missing pages"]
CheckCount --> |Yes| ReturnQueue
AddMissing --> ReturnQueue
ReturnQueue([Return final queue]) --> End([End])
style Simple fill:#f96,stroke:#333
style Smart fill:#6f9,stroke:#333
style ReturnQueue fill:#6f9,stroke:#333
```

**Diagram sources**
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L86)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L30)
- [parsing_queue_mode.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_queue_mode.py#L1-L7)

## Dependency Analysis
The WB Keywords Parser module has a well-defined dependency structure that separates concerns and enables modular development. The core dependencies are centered around Redis for coordination and data storage, with clear interfaces between components.

```mermaid
graph TD
subgraph "Core Dependencies"
Redis["Redis<br/>BaseRedis"]
Aiohttp["aiohttp<br/>HTTP client"]
Json["json<br/>Data serialization"]
end
subgraph "Module Components"
PT["ParsingTask<br/>Data model"]
GPQM["GlobalParsingQueueManager<br/>Task coordination"]
PW["ParserWorker<br/>Task processing"]
P["ParserService<br/>Crawling logic"]
PQM["ParsingQueueManager<br/>Page prioritization"]
PFM["ParsingFoundRedisManager<br/>Page tracking"]
end
PT --> GPQM
PT --> P
GPQM --> PW
GPQM --> P
PW --> P
P --> PQM
P --> PFM
PQM --> PFM
PFM --> Redis
GPQM --> Redis
PW --> Redis
Redis -.-> PT
Redis -.-> GPQM
Redis -.-> PFM
Aiohttp -.-> P
Json -.-> GPQM
Json -.-> P
style Redis fill:#bbf,stroke:#333
style Aiohttp fill:#bbf,stroke:#333
style Json fill:#bbf,stroke:#333
```

**Diagram sources**
- [parsing_task.py](file://app/modules/wb_keywords_parser/parsing_task.py#L1-L25)
- [global_parsing_queue_manager.py](file://app/modules/wb_keywords_parser/global_parsing_queue_manager.py#L1-L131)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L352)
- [parsing_page_queue_manager.py](file://app/modules/wb_keywords_parser/wb_parser/parsing_page_queue_manager.py#L1-L86)
- [parsing_found_redis_manager.py](file://app/modules/wb_keywords_parser/parsing_found_redis_manager.py#L1-L30)
- [app/core/redis_manager/base_redis_manager.py](file://app/core/redis_manager/base_redis_manager.py)

## Performance Considerations
The WB Keywords Parser is designed with performance optimization in mind, particularly for large-scale keyword extraction operations. The system implements several strategies to maximize efficiency while minimizing resource usage and avoiding rate limiting by the Wildberries platform.

The worker configuration allows for adjustable concurrency levels through the `max_parallel_tasks` parameter, which controls how many parsing tasks can run simultaneously. This can be tuned based on system resources and Wildberries rate limits. The parsing delay between requests is configurable through environment variables, allowing fine-tuning of the request rate to avoid being blocked by the marketplace.

The smart queue mode significantly improves performance by prioritizing pages that are more likely to contain relevant products, based on historical parsing data. This reduces the number of unnecessary HTTP requests and focuses crawling efforts on the most promising pages. The system also implements caching of parsing results in Redis, enabling quick retrieval of recent position data without additional HTTP requests.

For large-scale operations, the distributed worker architecture allows horizontal scaling by adding more parser worker instances. Each worker independently processes tasks from the shared Redis queue, enabling the system to handle high volumes of keyword extraction requests in parallel.

**Section sources**
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [settings_master.py](file://app/settings/settings_master.py#L1-L434)
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L352)

## Troubleshooting Guide
The WB Keywords Parser includes several mechanisms for handling common issues that may arise during operation. Understanding these issues and their solutions is critical for maintaining reliable parsing operations.

### Parsing Failures
When parsing fails for a specific page or keyword, the system logs detailed error information and continues with other tasks. Common causes include network connectivity issues, malformed responses from Wildberries, or temporary service outages. The system automatically retries failed tasks when they are re-added to the queue. To diagnose parsing failures, check the application logs for error messages containing "Ошибка при парсинге" (parsing error) and examine the associated stack traces.

### Rate Limiting by Wildberries
Wildberries may rate limit excessive requests from the parser. Symptoms include HTTP 429 responses or connection timeouts. The system mitigates this through configurable delays between requests, controlled by the `PARSING_KEYWORDS_DELAY_BETWEEN_TASKS` environment variable. If rate limiting occurs, increase this value to reduce request frequency. The system also uses multiple IP addresses through proxy configurations to distribute requests.

### CAPTCHA Handling
The Wildberries platform may present CAPTCHAs when it detects automated access patterns. The current system does not have built-in CAPTCHA solving capabilities. To address this, implement rotating user agents, vary request patterns, and ensure adequate delays between requests. Consider using CAPTCHA solving services if this becomes a persistent issue.

### Configuration Issues
Ensure all required environment variables are properly set, particularly Redis connection parameters and parsing limits. Key configuration options include:
- `MAX_PAGE_LIMIT_PARSER_WORKER`: Maximum number of pages to parse per keyword
- `PARSING_QUEUE_MODE`: Queue strategy (simple_queue or smart_queue)
- `MAX_THREAD_PARSER`: Maximum number of parser threads
- `PARSING_KEYWORDS_DELAY_BETWEEN_TASKS`: Delay between parsing tasks in seconds

**Section sources**
- [parser.py](file://app/modules/wb_keywords_parser/wb_parser/parser.py#L1-L352)
- [parser_worker.py](file://app/modules/wb_keywords_parser/parser_worker.py#L1-L80)
- [settings_master.py](file://app/settings/settings_master.py#L1-L434)
- [__init__.py](file://app/modules/shop_runner/service_manager/services/parsing_keywords_from_wb/__init__.py#L1-L93)

## Conclusion
The WB Keywords Parser module provides a robust and scalable solution for extracting keyword data from the Wildberries marketplace. Its distributed architecture, intelligent queue management, and comprehensive error handling make it well-suited for large-scale keyword extraction operations. The system effectively balances performance and reliability through its worker-based design and Redis coordination. By implementing smart page prioritization and configurable parsing parameters, the module optimizes resource usage while adapting to the dynamic nature of the marketplace. Future enhancements could include CAPTCHA solving capabilities, more sophisticated rate limit detection, and enhanced data analysis features to provide deeper insights from the extracted keyword data.