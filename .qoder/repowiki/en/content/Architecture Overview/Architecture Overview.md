# Architecture Overview

<cite>
**Referenced Files in This Document**   
- [app_container.py](file://app/core/di/app_container.py)
- [app_config.py](file://app/configs/app_config.py)
- [bot.py](file://app/client_bot/bot.py)
- [base.py](file://app/core/wb_api/base.py)
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [neo4j_config.py](file://app/configs/infrastructure_config/neo4j_config.py)
- [adv_fabric.py](file://app/core/wb_api/data_classes/advs/adv_fabric.py)
- [bidder_func.py](file://app/modules/shop_runner/bidder/bidder_func.py)
- [session_maker.py](file://app/utils/db/session_maker.py)
- [workers.py](file://app/arq_workers/workers.py)
- [logger.py](file://python_modules/logger.py)
- [client_bot_run.py](file://client_bot_run.py)
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
The adv-bot system is a modular monolith application designed for managing advertising campaigns on the Wildberries marketplace through a Telegram interface. The architecture follows a variation of Hexagonal Architecture with clear separation between core business logic and external concerns. The system integrates with multiple data stores including PostgreSQL, Redis, and Neo4j, and communicates with the Wildberries API for campaign management. This document provides a comprehensive overview of the architectural design, key patterns, and component interactions.

## Project Structure

```mermaid
graph TD
A[adv-bot] --> B[app]
A --> C[alembic]
A --> D[dockers]
A --> E[modules]
A --> F[configs]
A --> G[utils]
A --> H[arq_workers]
B --> I[client_bot]
B --> J[core]
B --> K[configs]
B --> L[modules]
I --> M[bot.py]
I --> N[user_interface]
I --> O[global_router.py]
J --> P[di]
J --> Q[wb_api]
J --> R[redis_manager_v2]
E --> S[adv_creator]
E --> T[shop_runner]
E --> U[wb_adv_updater]
E --> V[token_monitoring]
F --> W[infrastructure_config]
H --> X[workers.py]
```

**Diagram sources**
- [app](file://app)
- [modules](file://app/modules)
- [configs](file://app/configs)
- [arq_workers](file://app/arq_workers)

**Section sources**
- [app](file://app)
- [modules](file://app/modules)

## Core Components

The adv-bot system consists of several core components that work together to provide advertising campaign management functionality. The application is structured as a modular monolith with feature-based modules, allowing for clear separation of concerns while maintaining the benefits of a single deployable unit. Key components include the Telegram client interface, business logic modules, data access layers, and external integrations with Wildberries API.

**Section sources**
- [app](file://app)
- [modules](file://app/modules)

## Architecture Overview

```mermaid
graph TD
subgraph "Client Interface"
A[Telegram Bot]
B[aiogram]
end
subgraph "Application Core"
C[Business Logic Modules]
D[Dependency Injection]
E[Domain Models]
end
subgraph "Data Access Layer"
F[SQLAlchemy]
G[Redis]
H[Neo4j]
end
subgraph "External Integrations"
I[Wildberries API]
J[ARQ Workers]
end
A --> C
C --> F
C --> G
C --> H
C --> I
J --> C
B --> A
F --> K[PostgreSQL]
G --> L[Redis Store]
H --> M[Neo4j Graph DB]
style A fill:#f9f,stroke:#333
style C fill:#bbf,stroke:#333
style F fill:#f96,stroke:#333
style G fill:#f96,stroke:#333
style H fill:#f96,stroke:#333
style I fill:#6f9,stroke:#333
```

**Diagram sources**
- [bot.py](file://app/client_bot/bot.py)
- [app_container.py](file://app/core/di/app_container.py)
- [session_maker.py](file://app/utils/db/session_maker.py)
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [neo4j_config.py](file://app/configs/infrastructure_config/neo4j_config.py)
- [base.py](file://app/core/wb_api/base.py)
- [workers.py](file://app/arq_workers/workers.py)

## Detailed Component Analysis

### Client Interface Layer
The client interface is implemented using the aiogram framework for Telegram bot development. The bot provides a conversational interface for users to manage their advertising campaigns on Wildberries. The architecture separates the bot logic from the business logic, allowing for easy maintenance and potential extension to other messaging platforms.

```mermaid
sequenceDiagram
participant User as Telegram User
participant Bot as Telegram Bot
participant Handler as Global Router
participant Service as Business Logic
User->>Bot : Send command/message
Bot->>Handler : Route update
Handler->>Service : Invoke business logic
Service-->>Handler : Return result
Handler-->>Bot : Format response
Bot-->>User : Send response
Note over Bot,Service : All communication through dependency-injected services
```

**Diagram sources**
- [bot.py](file://app/client_bot/bot.py)
- [global_router.py](file://app/client_bot/global_router.py)
- [client_bot_run.py](file://client_bot_run.py)

**Section sources**
- [bot.py](file://app/client_bot/bot.py)
- [client_bot_run.py](file://client_bot_run.py)

### Business Logic Layer
The business logic layer is organized into feature-based modules such as adv_creator, shop_runner, wb_adv_updater, and token_monitoring. Each module encapsulates specific functionality related to advertising campaign management. The architecture follows a service-oriented approach within the monolith, with clear boundaries between different business capabilities.

#### Dependency Injection System
The application uses the Dependency Injector library to manage dependencies and promote loose coupling between components. The AppContainer serves as the central dependency injection container, providing configuration, database connections, and service instances throughout the application.

```mermaid
classDiagram
class AppContainer {
+settings : Singleton
+redis_client : Singleton
+redis_client_wrapper : Singleton
+module_resources : Container
+_redis_lifecycle : Resource
}
class AppConfig {
+infrastructure : InfrastructureConfig
+create() AppConfig
}
class RedisClient {
+redis_client : Redis
+get(key) Any
+set(key, value) bool
}
AppContainer --> AppConfig : depends on
AppContainer --> RedisClient : creates
RedisClient --> Redis : uses
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py)
- [app_config.py](file://app/configs/app_config.py)
- [redis_client.py](file://app/core/redis_manager_v2/redis_client.py)

**Section sources**
- [app_container.py](file://app/core/di/app_container.py)
- [app_config.py](file://app/configs/app_config.py)

### Data Access Layer
The data access layer implements the Repository Pattern through SQLAlchemy for PostgreSQL, with additional data stores for Redis and Neo4j. The architecture provides a consistent interface for data operations while abstracting the underlying storage mechanisms.

#### Repository Pattern Implementation
The session_maker module provides a robust implementation of database session management with support for read/write separation, connection pooling, and performance monitoring.

```mermaid
classDiagram
class AnalyticAsyncSession {
+execute(statement) Result
-log_slow_query(duration, statement)
}
class AsyncSessionMaker {
+get_async_session_maker(read_only) AsyncGenerator
}
class Engine {
+create_async_engine(connector)
}
AsyncSessionMaker --> AnalyticAsyncSession : creates
Engine --> AsyncSessionMaker : binds
AnalyticAsyncSession --> Engine : executes
Note over AnalyticAsyncSession : Adds query timing and slow query logging
```

**Diagram sources**
- [session_maker.py](file://app/utils/db/session_maker.py)

**Section sources**
- [session_maker.py](file://app/utils/db/session_maker.py)

### External Integrations
The system integrates with external services through well-defined interfaces and adapters. The Wildberries API integration is a key component, enabling campaign management and data retrieval from the marketplace.

#### Factory Pattern for Ad Creation
The ad creation process uses a Factory Pattern to instantiate appropriate ad types based on API responses. Currently, the system supports auction campaigns (type 9) through the AuctionAdv class.

```mermaid
classDiagram
class AdvFabric {
+get_adv_data_class(data_from_wb) AuctionAdv
}
class AuctionAdv {
+data : dict
+__init__(data)
}
class BaseAdv {
+validate_data(data) bool
}
AdvFabric --> AuctionAdv : creates
AuctionAdv --> BaseAdv : extends
Note over AdvFabric : Returns appropriate ad type based on API data
```

**Diagram sources**
- [adv_fabric.py](file://app/core/wb_api/data_classes/advs/adv_fabric.py)
- [auction_adv.py](file://app/core/wb_api/data_classes/advs/auction_adv.py)

**Section sources**
- [adv_fabric.py](file://app/core/wb_api/data_classes/advs/adv_fabric.py)

#### Strategy Pattern for Bidding
The bidding strategy is implemented using the Strategy Pattern, with different approaches for automatic and manual bidding modes. The bidder_func module contains the core logic for adjusting campaign bids based on keyword performance and position data.

```mermaid
flowchart TD
Start([Start Bid Process]) --> ValidateInput["Validate Campaign Settings"]
ValidateInput --> InputValid{"Settings Valid?"}
InputValid --> |No| ReturnError["Return Error"]
InputValid --> |Yes| GetKeywords["Get White List Keywords"]
GetKeywords --> BestKeyword{"Find Best Keyword"}
BestKeyword --> GetPosition["Get Current Position"]
GetPosition --> PositionValid{"Position Available?"}
PositionValid --> |No| ReturnError
PositionValid --> |Yes| CalculateBid["Calculate New Bid"]
CalculateBid --> CheckPosition{"Position <= Target?"}
CheckPosition --> |Yes| DecreaseBid["Decrease Bid by Step"]
CheckPosition --> |No| IncreaseBid["Increase Bid by Step"]
DecreaseBid --> ApplyLimits["Apply Min/Max Bid Limits"]
IncreaseBid --> ApplyLimits
ApplyLimits --> UpdateCampaign["Update Campaign Bid"]
UpdateCampaign --> End([Bid Process Complete])
```

**Diagram sources**
- [bidder_func.py](file://app/modules/shop_runner/bidder/bidder_func.py)

**Section sources**
- [bidder_func.py](file://app/modules/shop_runner/bidder/bidder_func.py)

## Dependency Analysis

```mermaid
graph TD
A[client_bot_run.py] --> B[AppContainer]
A --> C[DIManager]
A --> D[Dispatcher]
B --> E[AppConfig]
B --> F[RedisClient]
B --> G[ModuleResources]
E --> H[InfrastructureConfig]
H --> I[PostgreSQL]
H --> J[Redis]
H --> K[Neo4j]
F --> L[Redis]
C --> M[Dependency Injector]
D --> N[aiogram]
N --> O[Telegram API]
P[ARQ Workers] --> Q[create_complex_advs]
Q --> R[adv_creator]
R --> S[Wildberries API]
T[shop_runner] --> U[bidder_func]
U --> V[wb_keywords_parser]
V --> W[Web Scraper]
style A fill:#f9f,stroke:#333
style B fill:#bbf,stroke:#333
style F fill:#f96,stroke:#333
style H fill:#f96,stroke:#333
style Q fill:#6f9,stroke:#333
style U fill:#6f9,stroke:#333
```

**Diagram sources**
- [client_bot_run.py](file://client_bot_run.py)
- [app_container.py](file://app/core/di/app_container.py)
- [app_config.py](file://app/configs/app_config.py)
- [workers.py](file://app/arq_workers/workers.py)
- [bidder_func.py](file://app/modules/shop_runner/bidder/bidder_func.py)

**Section sources**
- [client_bot_run.py](file://client_bot_run.py)
- [app_container.py](file://app/core/di/app_container.py)
- [workers.py](file://app/arq_workers/workers.py)

## Performance Considerations
The system incorporates several performance optimization strategies. The database layer uses connection pooling with configurable pool size and overflow settings. Read/write separation is implemented to distribute database load, with read operations directed to replica instances when possible. The application includes built-in monitoring for slow queries and long-held database sessions, with warnings logged for operations exceeding one second. Redis is used extensively for caching frequently accessed data such as keyword positions and campaign settings, reducing the load on the primary database and external APIs.

**Section sources**
- [session_maker.py](file://app/utils/db/session_maker.py)
- [redis_client.py](file://app/core/redis_manager_v2/redis_client.py)

## Troubleshooting Guide
The system includes comprehensive logging through a centralized logger configuration. The logging system captures detailed information about application execution, including timestamps, log levels, source files, and line numbers. Error handling is implemented at multiple levels, with specific exception types for different failure modes such as API access errors. The application provides health check endpoints (/health, /readiness) for monitoring system status. When issues occur, the logs should be examined first, focusing on ERROR and WARNING level messages. Common issues include database connection problems, API authentication failures, and Redis connectivity issues, all of which are logged with contextual information to aid diagnosis.

**Section sources**
- [logger.py](file://python_modules/logger.py)
- [client_bot_run.py](file://client_bot_run.py)
- [base.py](file://app/core/wb_api/base.py)

## Conclusion
The adv-bot system demonstrates a well-structured modular monolith architecture with clear separation of concerns. The implementation of Hexagonal Architecture principles allows for flexible adaptation to changing requirements while maintaining testability and maintainability. Key architectural patterns including Dependency Injection, Repository Pattern, Factory Pattern, and Strategy Pattern are effectively utilized to create a robust and extensible system. The technology stack choices balance performance, reliability, and developer productivity, with Python providing a rich ecosystem for asynchronous programming and data processing. The system is well-positioned for future enhancements and scaling as needed.