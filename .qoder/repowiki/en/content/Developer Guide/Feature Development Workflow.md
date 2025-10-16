# Feature Development Workflow

<cite>
**Referenced Files in This Document**   
- [app_container.py](file://app/core/di/app_container.py)
- [bot.py](file://app/client_bot/bot.py)
- [states.py](file://app/client_bot/user_interface/states.py)
- [module_resources.py](file://app/core/di/module_resources.py)
- [di.py](file://app/modules/billing/di.py)
- [token_monitoring/__init__.py](file://app/modules/token_monitoring/__init__.py)
- [models.py](file://app/utils/db/models.py)
- [env.py](file://alembic/env.py)
- [workers.py](file://app/arq_workers/workers.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [base_adv.py](file://app/core/wb_api/data_classes/advs/base_adv.py)
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
This document provides comprehensive guidance for developing new features in the adv-bot project. It covers the modular architecture, dependency injection system, Telegram bot handler implementation, database migration procedures, and best practices for implementing new functionality while adhering to architectural patterns like Hexagonal Architecture and Dependency Injection.

## Project Structure

The adv-bot project follows a modular architecture with clear separation of concerns. The main components are organized into distinct directories:

- **app/**: Core application code
  - **client_bot/**: Telegram bot interface and handlers
  - **modules/**: Feature modules (token_monitoring, billing, wb_adv_updater, etc.)
  - **core/di/**: Dependency injection system
  - **arq_workers/**: Background task workers
- **alembic/**: Database migration system
- **configs/**: Application configuration
- **utils/**: Shared utilities and helpers

```mermaid
graph TD
A[adv-bot Project] --> B[app/]
A --> C[alembic/]
A --> D[configs/]
A --> E[utils/]
B --> F[client_bot/]
B --> G[modules/]
B --> H[core/di/]
B --> I[arq_workers/]
F --> J[bot.py]
F --> K[user_interface/]
F --> L[states.py]
G --> M[token_monitoring/]
G --> N[billing/]
G --> O[wb_adv_updater/]
H --> P[app_container.py]
H --> Q[module_resources.py]
C --> R[app_config.py]
E --> S[db/]
E --> T[redis_manager/]
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py)
- [bot.py](file://app/client_bot/bot.py)
- [models.py](file://app/utils/db/models.py)

**Section sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L50)
- [bot.py](file://app/client_bot/bot.py#L1-L16)
- [models.py](file://app/utils/db/models.py#L1-L51)

## Core Components

The adv-bot project is built around several core components that enable its functionality:

1. **Dependency Injection System**: Centralized service management using Dependency Injector
2. **Telegram Bot Interface**: Client interaction through Telegram with state management
3. **Background Workers**: Asynchronous task processing using Arq
4. **Database Migration System**: Schema management using Alembic
5. **Module System**: Feature-based organization with isolated functionality

The system follows Hexagonal Architecture principles, with the core domain logic separated from external concerns like databases, APIs, and user interfaces.

**Section sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L50)
- [workers.py](file://app/arq_workers/workers.py#L1-L51)
- [env.py](file://alembic/env.py#L1-L90)

## Architecture Overview

The adv-bot project implements a modular architecture with dependency injection and separation of concerns. The system is designed around the Hexagonal Architecture pattern, where the core business logic is isolated from external dependencies.

```mermaid
graph TD
subgraph "Core Domain"
A[AppContainer]
B[ModuleResources]
C[Business Logic]
end
subgraph "Infrastructure"
D[Database]
E[Redis]
F[Wildberries API]
G[Telegram API]
end
subgraph "Interfaces"
H[Telegram Bot]
I[Background Workers]
J[API Endpoints]
end
A --> |provides services| C
B --> |aggregates modules| A
C --> |uses| D
C --> |uses| E
C --> |uses| F
H --> |handles| C
I --> |processes| C
J --> |exposes| C
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L50)
- [module_resources.py](file://app/core/di/module_resources.py#L1-L35)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L145)

## Detailed Component Analysis

### Module Architecture and Creation

The adv-bot project uses a modular architecture where each feature is implemented as a self-contained module. The token_monitoring module serves as an excellent example of the module pattern.

```mermaid
classDiagram
class TokenMonitoringModule {
+TokenNotificationTracker
+NotificationType
+TokenInfoService
+TokenMonitoringService
+NotificationManager
+TokenExpirationService
+TokenMonitoringScheduler
+initialize_token_monitoring()
+setup_token_monitoring_for_app()
}
class BillingModule {
+BillingContainer
+RedisManager
+RedisLock
+process_payment_for_advs()
}
class WbAdvUpdaterModule {
+run_update_predict_ctr()
+run_update_all_keywords_on_wb()
+run_update_vectors_in_redis()
+data_manager.py
}
TokenMonitoringModule --> ModuleInterface : implements
BillingModule --> ModuleInterface : implements
WbAdvUpdaterModule --> ModuleInterface : implements
class ModuleInterface {
<<interface>>
+initialize()
+setup()
+services
+models
}
```

**Diagram sources**
- [token_monitoring/__init__.py](file://app/modules/token_monitoring/__init__.py#L1-L63)
- [di.py](file://app/modules/billing/di.py#L1-L43)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L145)

**Section sources**
- [token_monitoring/__init__.py](file://app/modules/token_monitoring/__init__.py#L1-L63)
- [di.py](file://app/modules/billing/di.py#L1-L43)

### Telegram Bot Handler Implementation

The client_bot structure handles Telegram interactions with a clear routing and state management system.

```mermaid
sequenceDiagram
participant User as Telegram User
participant Bot as Telegram Bot
participant Router as GlobalRouter
participant Handler as Handler Function
participant State as FSM State
User->>Bot : Sends message/command
Bot->>Router : Routes message
Router->>State : Checks current state
State-->>Router : Returns state
Router->>Handler : Calls appropriate handler
Handler->>Handler : Processes business logic
Handler->>State : Updates state if needed
Handler->>Bot : Returns response
Bot->>User : Sends response message
Note over Bot,Handler : State management ensures proper user interaction flow
```

**Diagram sources**
- [bot.py](file://app/client_bot/bot.py#L1-L16)
- [states.py](file://app/client_bot/user_interface/states.py#L1-L79)
- [global_router.py](file://app/client_bot/global_router.py)

**Section sources**
- [bot.py](file://app/client_bot/bot.py#L1-L16)
- [states.py](file://app/client_bot/user_interface/states.py#L1-L79)

### Dependency Injection System

The AppContainer class implements a comprehensive dependency injection system using the Dependency Injector library.

```mermaid
classDiagram
class AppContainer {
+settings : Singleton(AppConfig)
+redis_client : Singleton(create_redis_client)
+redis_client_wrapper : Singleton(RedisClient)
+module_resources : Container(ModuleResources)
+_redis_lifecycle : Resource(RedisLifecycle)
}
class ModuleResources {
+redis_client_wrapper : Dependency(RedisClient)
+billing : Container(BillingContainer)
+predict_ctr_manager : Container(PredictCTRManagerContainer)
}
class BillingContainer {
+redis_client_wrapper : Dependency(RedisClient)
+redis_manager : Singleton(RedisManager)
+redis_lock : Singleton(RedisLock)
}
AppContainer --> ModuleResources : contains
ModuleResources --> BillingContainer : contains
AppContainer --> RedisClient : creates
BillingContainer --> RedisManager : creates
BillingContainer --> RedisLock : creates
class RedisClient {
+redis_client : Redis
+get()
+set()
+delete()
}
class RedisManager {
+redis_client : RedisClient
+get_data()
+set_data()
}
class RedisLock {
+redis_client : RedisClient
+acquire()
+release()
}
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L50)
- [module_resources.py](file://app/core/di/module_resources.py#L1-L35)
- [di.py](file://app/modules/billing/di.py#L1-L43)

**Section sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L50)
- [module_resources.py](file://app/core/di/module_resources.py#L1-L35)
- [di.py](file://app/modules/billing/di.py#L1-L43)

### Database Migration Procedures

The Alembic system manages database schema migrations with version control.

```mermaid
flowchart TD
A[Create Model Changes] --> B[Generate Migration]
B --> C[Review Migration Script]
C --> D[Apply Migration]
D --> E[Update Production]
E --> F[Verify Changes]
B --> |alembic revision --autogenerate| G[env.py]
G --> |target_metadata| H[BaseTable.metadata]
H --> |models| I[User, WBToken, AdvSetting, etc.]
D --> |alembic upgrade head| J[Database]
F --> |test functionality| K[Application]
style G fill:#f9f,stroke:#333
style J fill:#f9f,stroke:#333
```

**Diagram sources**
- [env.py](file://alembic/env.py#L1-L90)
- [models.py](file://app/utils/db/models.py#L1-L51)

**Section sources**
- [env.py](file://alembic/env.py#L1-L90)
- [models.py](file://app/utils/db/models.py#L1-L51)

### Background Workers and API Integrations

The arq_workers system handles background processing and API integrations.

```mermaid
classDiagram
class WorkerSettings {
+functions : List[Callable]
+redis_settings : ArqRedisSettings
+on_startup : Callable
+on_shutdown : Callable
+keep_jobs : int
+max_tries : int
+job_timeout : int
}
class ArqWorker {
+startup()
+shutdown()
+process_tasks()
}
class BackgroundTask {
+run_update_predict_ctr()
+run_update_all_keywords_on_wb()
+sender_message_to_not_pay_users()
+process_token_expiration_check()
+process_payment_for_advs()
}
WorkerSettings --> ArqWorker : configures
ArqWorker --> BackgroundTask : executes
BackgroundTask --> Redis : queues tasks
BackgroundTask --> Database : reads/writes
BackgroundTask --> WildberriesAPI : integrates
BackgroundTask --> TelegramAPI : notifies
class Redis {
+task_queue : List
+results : Hash
+status : String
}
class WildberriesAPI {
+get_keywords()
+update_positions()
+get_statistics()
}
class TelegramAPI {
+send_message()
+notify_users()
}
```

**Diagram sources**
- [workers.py](file://app/arq_workers/workers.py#L1-L51)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L145)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L799)

**Section sources**
- [workers.py](file://app/arq_workers/workers.py#L1-L51)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L145)

## Dependency Analysis

The adv-bot project has a well-defined dependency structure that follows the Dependency Inversion Principle.

```mermaid
graph TD
A[AppContainer] --> B[ModuleResources]
A --> C[RedisClient]
A --> D[AppConfig]
B --> E[BillingContainer]
B --> F[PredictCTRManagerContainer]
E --> G[RedisManager]
E --> H[RedisLock]
G --> C
H --> C
I[ClientBot] --> A
I --> J[States]
K[BackgroundWorkers] --> A
K --> L[DIManager]
M[Database] --> N[Alembic]
N --> D
style A fill:#ccf,stroke:#333
style B fill:#ccf,stroke:#333
style E fill:#ccf,stroke:#333
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L50)
- [module_resources.py](file://app/core/di/module_resources.py#L1-L35)
- [di.py](file://app/modules/billing/di.py#L1-L43)

**Section sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L50)
- [module_resources.py](file://app/core/di/module_resources.py#L1-L35)
- [di.py](file://app/modules/billing/di.py#L1-L43)

## Performance Considerations

The system is designed with performance in mind, using caching, background processing, and efficient database queries.

Key performance considerations:
- Redis caching for frequently accessed data
- Background workers for long-running tasks
- Database connection pooling
- Efficient query patterns with proper indexing
- Asynchronous processing throughout the system

The DI system ensures that services are properly instantiated and reused, minimizing resource overhead.

## Troubleshooting Guide

Common issues and their solutions:

1. **Dependency Injection Issues**: Ensure all dependencies are properly registered in the AppContainer and ModuleResources
2. **Database Migration Conflicts**: Use alembic revision --autogenerate carefully and review generated scripts
3. **State Management Problems**: Verify state transitions in the client_bot handlers
4. **Background Worker Failures**: Check Redis connection and task queue status
5. **API Integration Errors**: Validate API credentials and rate limiting

**Section sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L50)
- [env.py](file://alembic/env.py#L1-L90)
- [workers.py](file://app/arq_workers/workers.py#L1-L51)

## Conclusion

The adv-bot project provides a robust foundation for feature development with its modular architecture, dependency injection system, and clear separation of concerns. By following the patterns demonstrated in existing modules like token_monitoring and billing, developers can create new features that integrate seamlessly with the existing system. The combination of Hexagonal Architecture and Dependency Injection ensures that the codebase remains maintainable and testable as it grows.