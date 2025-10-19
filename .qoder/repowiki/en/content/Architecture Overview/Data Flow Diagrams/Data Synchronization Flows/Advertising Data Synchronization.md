# Advertising Data Synchronization

<cite>
**Referenced Files in This Document**   
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)
- [adv.py](file://app/modules/common_slaves/wildberries/data_classes/adv.py)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py)
- [client.py](file://app/utils/click_house/client.py)
- [super_cabinet_manager.py](file://app/modules/common_slaves/wildberries/super_cabinet_manager.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
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
The advertising data synchronization system in the adv-bot application enables bidirectional data flow between the internal system and Wildberries advertising API. This document details the workflow for retrieving advertising campaign data (CPM, bids, status) from Wildberries, transforming it for internal use, and updating local databases (PostgreSQL, Redis, ClickHouse). The system orchestrates ad data updates through the wb_manager component, implements robust error handling for failed API calls, and ensures reliable communication with Wildberries advertising endpoints through the AdvertApi implementation. The workflow incorporates rate limiting, caching strategies, and data consistency patterns to maintain system reliability and performance.

## Project Structure
The advertising data synchronization functionality is organized across multiple modules within the adv-bot application. The core components are distributed across the following directory structure:

```mermaid
graph TD
A[app/modules] --> B[wb_adv_updater]
A --> C[common_slaves/wildberries]
A --> D[wb_update_state_manager]
B --> E[wb_manager.py]
B --> F[data_manager.py]
B --> G[data_setter.py]
C --> H[api/api.py]
C --> I[super_cabinet_manager.py]
C --> J[models/models.py]
C --> K[data_classes/adv.py]
app --> L[utils]
L --> M[click_house/client.py]
L --> N[redis_manager.py]
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

## Core Components
The advertising data synchronization workflow consists of several core components that work together to retrieve, transform, and store advertising data. The wb_manager orchestrates the entire process, coordinating between the Wildberries API client, data transformation logic, and database operations. The AdvertApi implementation provides a reliable interface for communicating with Wildberries advertising endpoints, handling authentication, rate limiting, and error recovery. Data is stored in multiple databases: PostgreSQL for relational data, Redis for caching and temporary storage, and ClickHouse for analytical data.

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

## Architecture Overview
The advertising data synchronization architecture follows a layered approach with clear separation of concerns. The system retrieves data from Wildberries API, processes it through transformation layers, and stores it in multiple databases for different use cases.

```mermaid
graph TD
A[Wildberries API] --> |HTTP Requests| B[AdvertApi]
B --> C[Data Transformation]
C --> D[PostgreSQL]
C --> E[Redis]
C --> F[ClickHouse]
G[wb_manager] --> |Orchestrates| B
G --> |Updates| D
G --> |Caches| E
G --> |Analyzes| F
H[Client Requests] --> G
D --> |Serves| I[Application Logic]
E --> |Accelerates| I
F --> |Analyzes| J[Reporting & Analytics]
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

## Detailed Component Analysis

### wb_manager Analysis
The wb_manager component serves as the central orchestrator for advertising data synchronization. It coordinates the retrieval of advertising data from Wildberries, processes the data, and updates internal databases.

```mermaid
sequenceDiagram
participant Client
participant wb_manager
participant AdvertApi
participant Wildberries
participant PostgreSQL
participant Redis
participant ClickHouse
Client->>wb_manager : Request data update
wb_manager->>AdvertApi : Initialize with access
AdvertApi->>Wildberries : Authenticate
Wildberries-->>AdvertApi : Access granted
AdvertApi->>Wildberries : GET /adv/v0/stats/keywords
Wildberries-->>AdvertApi : Keyword statistics
AdvertApi->>wb_manager : Return keyword data
wb_manager->>wb_manager : Transform data
wb_manager->>ClickHouse : INSERT keyword statistics
ClickHouse-->>wb_manager : Confirmation
wb_manager->>PostgreSQL : UPDATE AdvSetting
PostgreSQL-->>wb_manager : Confirmation
wb_manager->>Redis : CACHE processed data
Redis-->>wb_manager : Confirmation
wb_manager-->>Client : Update complete
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)

### AdvertApi Implementation
The AdvertApi implementation provides a reliable interface for communicating with Wildberries advertising endpoints. It handles authentication, rate limiting, and error recovery to ensure stable communication.

```mermaid
classDiagram
class AdvertApi {
+get_keywords_stat(adv_id)
+get_adv_full_state(adv_ids, dates)
+set_search_cpm(search_adv_id, cpm)
+set_minus_phrases(adv_setting, phrases)
+pause_company(adv_id)
+get_clusters_for_adv(adv)
}
class WBApi {
+advert : AdvertApi
+content : ContentApi
}
class BaseAPI {
+session : ClientSession
+headers : dict
}
class ABC_WB_API {
+_rights : set[str]
+_only_read : bool
}
AdvertApi --|> ABC_WB_API
ABC_WB_API --|> BaseAPI
WBApi --> AdvertApi
WBApi --> ContentApi
```

**Diagram sources**
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

**Section sources**
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

### Data Flow Analysis
The data flow for advertising synchronization follows a specific pattern from Wildberries API to internal storage and back.

```mermaid
flowchart TD
A[Wildberries API] --> B{Rate Limiting}
B --> |Within limits| C[Data Retrieval]
B --> |Exceeded| D[Retry with backoff]
D --> C
C --> E[Data Transformation]
E --> F{Validation}
F --> |Valid| G[ClickHouse Storage]
F --> |Invalid| H[Error Handling]
H --> I[Log Error]
G --> J[PostgreSQL Update]
J --> K[Redis Caching]
K --> L[Application Use]
M[User Request] --> N[w_manager]
N --> O[Check Cache]
O --> |Cache Hit| P[Return Cached Data]
O --> |Cache Miss| Q[Retrieve from DB]
Q --> R[Update Cache]
R --> P
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)

## Dependency Analysis
The advertising data synchronization components have specific dependencies that enable their functionality. These dependencies include database connections, API clients, and utility modules.

```mermaid
graph TD
A[wb_manager] --> B[AdvertApi]
A --> C[PostgreSQL]
A --> D[Redis]
A --> E[ClickHouse]
A --> F[super_cabinet_manager]
B --> G[Wildberries API]
B --> H[BaseAPI]
C --> I[SQLAlchemy]
D --> J[redis.asyncio]
E --> K[clickhouse_connect]
F --> L[WBToken]
F --> M[WBCabinet]
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)

## Performance Considerations
The advertising data synchronization system incorporates several performance optimizations to handle large volumes of data efficiently. The ClickHouse client implements connection pooling and multiprocessing synchronization to manage database connections effectively. The system uses Redis for caching frequently accessed data, reducing database load and improving response times. Data retrieval from Wildberries API is batched to minimize the number of HTTP requests, and the system implements rate limiting to prevent API throttling.

**Section sources**
- [client.py](file://app/utils/click_house/client.py)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)

## Troubleshooting Guide
When troubleshooting issues with the advertising data synchronization workflow, consider the following common scenarios:

1. **Authentication failures**: Verify that WBToken records are valid and not expired. Check the token's permissions and shop_id association.
2. **Data retrieval timeouts**: Ensure the system is respecting Wildberries API rate limits. Check network connectivity and API endpoint availability.
3. **Database connection issues**: Verify that PostgreSQL, Redis, and ClickHouse services are running and accessible. Check connection pool settings.
4. **Data consistency problems**: Confirm that data transformation logic is correctly handling edge cases and data type conversions.
5. **Caching issues**: Clear Redis cache if stale data is suspected. Verify cache key generation and expiration settings.

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [api.py](file://app/modules/common_slaves/wildberries/api/api.py)
- [super_cabinet_manager.py](file://app/modules/common_slaves/wildberries/super_cabinet_manager.py)

## Conclusion
The advertising data synchronization workflow in the adv-bot system provides a robust mechanism for integrating with Wildberries advertising API. The architecture, centered around the wb_manager orchestrator and AdvertApi interface, ensures reliable data flow between external and internal systems. By leveraging multiple database technologies (PostgreSQL, Redis, ClickHouse) and implementing proper error handling and rate limiting, the system maintains data consistency and performance under various conditions. The modular design allows for future enhancements and adaptations to changing requirements.