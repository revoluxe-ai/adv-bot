# Data Flow Diagrams

<cite>
**Referenced Files in This Document**   
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [workers.py](file://app/arq_workers/workers.py)
- [app_container.py](file://app/core/di/app_container.py)
- [di_manager.py](file://app/core/di/di_manager.py)
- [scheduler.py](file://app/modules/token_monitoring/scheduler.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
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
This document provides comprehensive data flow documentation for the adv-bot system, mapping the complete data lifecycle from user interaction to external API synchronization. It covers both synchronous flows (user command → bot handler → service → response) and asynchronous flows (scheduled token monitoring, keyword parsing jobs, ad performance updates). The documentation illustrates how DIManager orchestrates service initialization and how ARQ workers process background tasks, showing data transformation at each stage with examples from token_monitoring_service and wb_adv_updater. Error recovery paths and retry mechanisms are included, along with timing diagrams for critical operations like shop update cycles and prediction model updates.

## Project Structure

The adv-bot system follows a modular architecture with clear separation of concerns. The core application resides in the `app` directory, which contains several key subdirectories:

- `arq_workers`: Contains ARQ worker configurations for background task processing
- `client_bot`: Implements the Telegram bot interface and user interaction handlers
- `core`: Houses core infrastructure including dependency injection (DI), Redis management, and API clients
- `modules`: Contains business logic modules such as token monitoring, ad updating, and shop management
- `configs`: Configuration management for the application
- `utils`: Utility functions and shared components

The system uses Alembic for database migrations, with migration scripts in the `alembic/versions` directory. External service integrations include Redis for caching and message queuing, Neo4j for graph data storage, and ClickHouse for analytics data.

```mermaid
graph TD
A[User Interaction] --> B[Client Bot]
B --> C[Core Services]
C --> D[External APIs]
D --> E[Data Storage]
E --> F[Analytics & ML]
F --> G[Notification System]
G --> A
subgraph "Application Core"
C --> H[DI Manager]
H --> I[Redis Manager]
I --> J[API Clients]
end
subgraph "Background Processing"
K[ARQ Workers] --> L[Task Queue]
L --> M[Background Jobs]
M --> N[Shop Updates]
M --> O[Token Monitoring]
M --> P[Ad Performance Updates]
end
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py)
- [workers.py](file://app/arq_workers/workers.py)

**Section sources**
- [app_container.py](file://app/core/di/app_container.py)
- [workers.py](file://app/arq_workers/workers.py)

## Core Components

The adv-bot system consists of several core components that work together to manage advertising campaigns on Wildberries. The key components include:

1. **Token Monitoring Service**: Monitors API token status and handles deactivation events
2. **WB Advertiser Updater**: Manages ad campaign updates and performance tracking
3. **ARQ Workers**: Processes background tasks using Redis as a message broker
4. **DI Manager**: Orchestrates dependency injection and service initialization
5. **Scheduler**: Manages periodic tasks and maintenance operations

These components work together to provide a robust system for managing advertising campaigns, with comprehensive error handling and recovery mechanisms.

**Section sources**
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [di_manager.py](file://app/core/di/di_manager.py)

## Architecture Overview

The adv-bot system follows a layered architecture with clear separation between presentation, business logic, and data access layers. The system uses dependency injection to manage service dependencies and configuration.

```mermaid
graph TD
A[Telegram Client] --> B[Client Bot]
B --> C[Service Layer]
C --> D[Data Access Layer]
D --> E[External Services]
subgraph "Service Layer"
C --> F[Token Monitoring]
C --> G[Ad Campaign Management]
C --> H[Shop Management]
C --> I[Billing]
end
subgraph "Data Access Layer"
D --> J[PostgreSQL]
D --> K[Redis]
D --> L[ClickHouse]
D --> M[Neo4j]
end
subgraph "External Services"
E --> N[Wildberries API]
E --> O[GRPC Services]
end
P[ARQ Workers] --> Q[Background Tasks]
Q --> C
R[Scheduler] --> S[Periodic Tasks]
S --> C
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py)
- [di_manager.py](file://app/core/di/di_manager.py)
- [workers.py](file://app/arq_workers/workers.py)

## Detailed Component Analysis

### Token Monitoring Service Analysis

The Token Monitoring Service is responsible for detecting and handling token deactivation events during API calls to Wildberries. It wraps existing API decorators to add token monitoring capabilities without modifying the core API client code.

```mermaid
flowchart TD
Start([API Call]) --> Decorator["Apply try_except_decorator"]
Decorator --> Monitoring["Add Token Monitoring"]
Monitoring --> API["Call Wildberries API"]
API --> Success{"Success?"}
Success --> |Yes| ReturnResult["Return Result"]
Success --> |No| CheckError["Check Error Type"]
CheckError --> IsForbidden{"Forbidden Error?"}
IsForbidden --> |Yes| ExtractShop["Extract Shop ID"]
ExtractShop --> LogWarning["Log Warning"]
LogWarning --> Notify["Send Deactivation Notification"]
Notify --> ReThrow["Re-throw Exception"]
IsForbidden --> |No| ReThrow
ReturnResult --> End([Return to Caller])
ReThrow --> End
```

**Diagram sources**
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py)

**Section sources**
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py)

### DI Manager Analysis

The DI Manager orchestrates service initialization and dependency injection throughout the application. It uses the Dependency Injector library to manage service lifecycles and configuration.

```mermaid
flowchart TD
Start([Application Start]) --> CreateContainer["Create AppContainer"]
CreateContainer --> Bootstrap["Bootstrap Container"]
Bootstrap --> WireModules["Wire Module Containers"]
WireModules --> InitResources["Initialize Resources"]
InitResources --> ReturnContainer["Return Container"]
ReturnContainer --> UseContainer["Use Container in Application"]
UseContainer --> Shutdown["Application Shutdown"]
Shutdown --> ReleaseResources["Release Resources"]
ReleaseResources --> End([Application Exit])
subgraph "Container Wiring"
WireModules --> Module1["Wire token_monitoring"]
WireModules --> Module2["Wire wb_adv_updater"]
WireModules --> Module3["Wire shop_runner"]
end
```

**Diagram sources**
- [di_manager.py](file://app/core/di/di_manager.py)
- [app_container.py](file://app/core/di/app_container.py)

**Section sources**
- [di_manager.py](file://app/core/di/di_manager.py)
- [app_container.py](file://app/core/di/app_container.py)

### ARQ Workers Analysis

The ARQ Workers process background tasks using Redis as a message broker. The system uses a worker pattern to handle long-running operations asynchronously.

```mermaid
flowchart TD
Start([Task Submitted]) --> Queue["Add to Redis Queue"]
Queue --> Worker["ARQ Worker Picks Up Task"]
Worker --> Context["Initialize Context"]
Context --> Execute["Execute Task"]
Execute --> Success{"Success?"}
Success --> |Yes| Complete["Mark as Complete"]
Success --> |No| Retry{"Retries Left?"}
Retry --> |Yes| Delay["Wait Exponential Backoff"]
Delay --> Execute
Retry --> |No| Fail["Mark as Failed"]
Complete --> End([Task Complete])
Fail --> End
subgraph "Worker Startup"
Context --> Bot["Initialize Bot"]
Context --> Session["Create ClientSession"]
end
```

**Diagram sources**
- [workers.py](file://app/arq_workers/workers.py)

**Section sources**
- [workers.py](file://app/arq_workers/workers.py)

### WB Advertiser Updater Analysis

The WB Advertiser Updater manages the lifecycle of advertising campaigns, including keyword updates, performance tracking, and predictive analytics.

```mermaid
flowchart TD
Start([Update Cycle]) --> GetSettings["Get Active Ad Settings"]
GetSettings --> ProcessAd["Process Each Ad"]
ProcessAd --> GetKeywords["Get Calculated Keywords"]
GetKeywords --> UpdatePredict["Update Predict CTR"]
UpdatePredict --> CheckStatus["Check Campaign Status"]
CheckStatus --> IsActive{"Active?"}
IsActive --> |Yes| UpdateAd["Update Ad on Wildberries"]
IsActive --> |No| Skip["Skip Update"]
UpdateAd --> NextAd["Next Ad"]
Skip --> NextAd
NextAd --> MoreAds{"More Ads?"}
MoreAds --> |Yes| ProcessAd
MoreAds --> |No| EndCycle["End Update Cycle"]
EndCycle --> Wait["Wait for Next Cycle"]
Wait --> Start
subgraph "Predict CTR Update"
UpdatePredict --> GetModel["Load Prediction Model"]
GetModel --> Calculate["Calculate Predicted CTR"]
Calculate --> Store["Store in Redis"]
end
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)

### Token Monitoring Scheduler Analysis

The Token Monitoring Scheduler manages periodic tasks related to token expiration and health checks.

```mermaid
flowchart TD
Start([Scheduler Start]) --> SetTime["Set Check Time (9:00)"]
SetTime --> CalculateNext["Calculate Next Run Time"]
CalculateNext --> Sleep["Sleep Until Check Time"]
Sleep --> CheckTokens["Check Token Expiration"]
CheckTokens --> GetStats["Get Expiration Stats"]
GetStats --> SendReport["Send Notification Report"]
SendReport --> Cleanup["Cleanup Old Notifications"]
Cleanup --> Reschedule["Schedule Next Check"]
Reschedule --> Sleep
subgraph "Token Expiration Check"
CheckTokens --> QueryDB["Query Database for Tokens"]
QueryDB --> Analyze["Analyze Expiration Dates"]
Analyze --> Categorize["Categorize by Expiration"]
Categorize --> GenerateStats["Generate Statistics"]
end
```

**Diagram sources**
- [scheduler.py](file://app/modules/token_monitoring/scheduler.py)

**Section sources**
- [scheduler.py](file://app/modules/token_monitoring/scheduler.py)

## Dependency Analysis

The adv-bot system has a well-defined dependency structure with clear boundaries between components. The core dependencies are managed through the DI container, which provides services to various modules.

```mermaid
graph TD
AppContainer --> RedisClient
AppContainer --> AppConfig
AppContainer --> ModuleResources
ModuleResources --> TokenMonitoring
ModuleResources --> WbAdvUpdater
ModuleResources --> ShopRunner
ModuleResources --> Billing
TokenMonitoring --> RedisClient
TokenMonitoring --> WBApi
WbAdvUpdater --> RedisClient
WbAdvUpdater --> ClickHouse
WbAdvUpdater --> Neo4j
WbAdvUpdater --> WBApi
ShopRunner --> RedisClient
ShopRunner --> WBApi
Billing --> RedisClient
Billing --> Database
ARQWorkers --> RedisClient
ARQWorkers --> AppContainer
ClientBot --> AppContainer
ClientBot --> ARQWorkers
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py)
- [di_manager.py](file://app/core/di/di_manager.py)

**Section sources**
- [app_container.py](file://app/core/di/app_container.py)
- [di_manager.py](file://app/core/di/di_manager.py)

## Performance Considerations

The adv-bot system is designed with performance in mind, using several optimization techniques:

1. **Caching**: Extensive use of Redis for caching frequently accessed data
2. **Batch Processing**: Operations are batched to minimize API calls
3. **Asynchronous Processing**: Long-running tasks are handled asynchronously
4. **Connection Pooling**: Database and API connections are pooled
5. **Exponential Backoff**: Retry mechanisms use exponential backoff to avoid overwhelming services

The system also includes monitoring and logging to track performance metrics and identify bottlenecks. Critical operations are timed and logged for performance analysis.

## Troubleshooting Guide

When troubleshooting issues with the adv-bot system, consider the following common scenarios:

1. **Token Deactivation**: If API calls are failing with 403 errors, check the token monitoring logs and verify that tokens are still valid.

2. **Background Task Failures**: Check the ARQ worker logs for failed tasks and examine the retry mechanisms.

3. **Performance Issues**: Monitor Redis memory usage and database query performance. Consider scaling resources if needed.

4. **Dependency Injection Problems**: Verify that all required services are properly wired in the DI container.

5. **Configuration Issues**: Ensure that all environment variables and configuration files are correctly set.

The system includes comprehensive logging that can help diagnose issues. Logs are structured to include timestamps, component names, and relevant context information.

**Section sources**
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py)
- [workers.py](file://app/arq_workers/workers.py)
- [di_manager.py](file://app/core/di/di_manager.py)

## Conclusion

The adv-bot system provides a comprehensive solution for managing advertising campaigns on Wildberries. Its modular architecture with clear separation of concerns makes it maintainable and extensible. The use of dependency injection, asynchronous processing, and comprehensive error handling ensures reliability and performance.

Key strengths of the system include:
- Robust token monitoring and recovery mechanisms
- Efficient background task processing with ARQ workers
- Comprehensive data flow from user interaction to external API synchronization
- Well-structured dependency management through DI
- Detailed logging and monitoring for troubleshooting

The system is well-positioned to handle current requirements and can be extended to support additional features as needed.