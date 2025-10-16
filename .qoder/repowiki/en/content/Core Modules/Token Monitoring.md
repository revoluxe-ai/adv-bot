# Token Monitoring

<cite>
**Referenced Files in This Document**   
- [models.py](file://app/modules/token_monitoring/models.py)
- [scheduler.py](file://app/modules/token_monitoring/scheduler.py)
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py)
- [token_expiration_service.py](file://app/modules/token_monitoring/services/token_expiration_service.py)
- [notification_manager.py](file://app/modules/token_monitoring/services/notification_manager.py)
- [startup.py](file://app/modules/token_monitoring/startup.py)
- [integration.py](file://app/modules/token_monitoring/integration.py)
- [token_info_service.py](file://app/modules/token_monitoring/services/token_info_service.py)
- [f8e1d9c2a3b4_add_token_notification_tracker_table.py](file://alembic/versions/f8e1d9c2a3b4_add_token_notification_tracker_table.py)
- [README.md](file://app/modules/token_monitoring/README.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [Token Status Checking and Permission Validation](#token-status-checking-and-permission-validation)
5. [Expiration Prediction and Scheduling](#expiration-prediction-and-scheduling)
6. [Notification System](#notification-system)
7. [Service Layer Implementation](#service-layer-implementation)
8. [Integration and Startup](#integration-and-startup)
9. [Data Models and Database Schema](#data-models-and-database-schema)
10. [Redis Caching Strategy](#redis-caching-strategy)
11. [Common Issues and Solutions](#common-issues-and-solutions)
12. [Configuration Options](#configuration-options)
13. [Usage Examples](#usage-examples)

## Introduction
The Token Monitoring module is a comprehensive system designed to track Wildberries API token validity, permissions, and expiration status. This system provides proactive monitoring of token health, detects deactivation events, predicts expiration, and sends timely notifications to users. The module integrates with the application's HTTP request layer to monitor API calls and implements a scheduled background service for periodic token status checks. It ensures that users are alerted to potential service disruptions before they occur, maintaining uninterrupted access to Wildberries API services.

## Architecture Overview

```mermaid
graph TD
subgraph "Token Monitoring System"
TIS[TokenInfoService]
TMS[TokenMonitoringService]
NM[NotificationManager]
TES[TokenExpirationService]
S[Scheduler]
I[Integration]
end
Client[Wildberries API Clients] --> TMS
TMS --> NM
TES --> NM
S --> TES
I --> TMS
I --> S
TIS --> NM
TMS --> TIS
TES --> TIS
style TIS fill:#f9f,stroke:#333
style TMS fill:#f9f,stroke:#333
style NM fill:#f9f,stroke:#333
style TES fill:#f9f,stroke:#333
style S fill:#f9f,stroke:#333
style I fill:#f9f,stroke:#333
```

**Diagram sources**
- [README.md](file://app/modules/token_monitoring/README.md#L26-L47)

**Section sources**
- [README.md](file://app/modules/token_monitoring/README.md)

## Core Components

The Token Monitoring module consists of several interconnected services that work together to provide comprehensive token monitoring capabilities. The system is designed with a modular architecture that separates concerns between token information retrieval, expiration monitoring, notification management, and system integration. Each component has a specific responsibility and communicates with others through well-defined interfaces. The architecture follows a service-oriented design pattern, allowing for independent development, testing, and deployment of each component.

**Section sources**
- [models.py](file://app/modules/token_monitoring/models.py)
- [scheduler.py](file://app/modules/token_monitoring/scheduler.py)
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py)

## Token Status Checking and Permission Validation

```mermaid
classDiagram
class TokenInfoService {
+get_shop_token_status(shop_id) TokenStatusReport
+validate_permissions(shop_id, required_rights) PermissionValidation
+get_expiring_tokens(shop_id, days_ahead) list[ExpiringToken]
}
class TokenStatusReport {
-shop_id : str
-shop_name : str
-status : str
-all_tokens : list[TokenInfo]
-valid_tokens : list[TokenInfo]
-expired_tokens : list[TokenInfo]
-available_permissions : set[str]
-missing_permissions : set[str]
-has_all_required_permissions : bool
-expiring_tokens : list[ExpiringToken]
+total_tokens : int
+valid_token_count : int
+has_valid_tokens : bool
+status_description : str
+service_expiration_date : datetime | None
+days_until_service_breaks : int | None
}
class TokenInfo {
-id : int
-api_key : str
-user_id : int
-shop_id : str
-expires : datetime
-categories : set[str]
-is_read_only : bool
-is_valid : bool
-is_expired : bool
}
class ExpiringToken {
-token_info : TokenInfo
-days_until_expiry : int
-shop_name : str
+expiry_date_str : str
}
class PermissionValidation {
-has_access : bool
-missing_permissions : set[str]
-available_permissions : set[str]
-error_message : str | None
}
TokenInfoService --> TokenStatusReport : "creates"
TokenInfoService --> ExpiringToken : "creates"
TokenInfoService --> PermissionValidation : "creates"
TokenStatusReport --> TokenInfo : "contains"
TokenStatusReport --> ExpiringToken : "contains"
TokenStatusReport --> PermissionValidation : "related"
```

**Diagram sources**
- [token_info_service.py](file://app/modules/token_monitoring/services/token_info_service.py#L100-L353)

**Section sources**
- [token_info_service.py](file://app/modules/token_monitoring/services/token_info_service.py#L1-L353)

## Expiration Prediction and Scheduling

```mermaid
sequenceDiagram
participant Scheduler as TokenMonitoringScheduler
participant TES as TokenExpirationService
participant DB as Database
participant NM as NotificationManager
Scheduler->>Scheduler : start_daily_expiration_check()
loop Every 24 hours
Scheduler->>Scheduler : Calculate next check time
Scheduler->>TES : _run_expiration_check()
TES->>DB : _get_active_tokens_with_expiry()
DB-->>TES : List of active tokens
loop For each token
TES->>TES : Calculate days_until_expiry
TES->>DB : _notification_already_sent()
alt Notification needed
TES->>NM : notify_token_issue()
NM->>NM : _get_shop_users()
NM->>NM : _send_notification_to_user()
NM->>DB : Record notification
else Notification already sent
TES->>TES : Skip notification
end
end
TES->>Scheduler : Return check statistics
end
```

**Diagram sources**
- [scheduler.py](file://app/modules/token_monitoring/scheduler.py#L1-L185)
- [token_expiration_service.py](file://app/modules/token_monitoring/services/token_expiration_service.py#L1-L313)

**Section sources**
- [scheduler.py](file://app/modules/token_monitoring/scheduler.py#L1-L185)
- [token_expiration_service.py](file://app/modules/token_monitoring/services/token_expiration_service.py#L1-L313)

## Notification System

```mermaid
flowchart TD
Start([Notification Request]) --> ValidateInput["Validate notification parameters"]
ValidateInput --> GetUsers["Get shop users from database"]
GetUsers --> UsersFound{"Users found?"}
UsersFound --> |No| LogWarning["Log warning: No users for shop"]
UsersFound --> |Yes| FormatMessage["Format message using template"]
FormatMessage --> SendMessage["Send Telegram message to each user"]
SendMessage --> HandleResult{"Send successful?"}
HandleResult --> |Yes| RecordNotification["Record notification in database"]
HandleResult --> |No| HandleError["Handle error (blocked bot, etc.)"]
HandleError --> |TelegramForbiddenError| SkipUser["Skip user (bot blocked)"]
HandleError --> |IntegrityError| SkipDuplicate["Skip (duplicate notification)"]
HandleError --> |Other error| LogError["Log error"]
RecordNotification --> CommitTransaction["Commit database transaction"]
CommitTransaction --> End([Notification process completed])
LogWarning --> End
SkipUser --> SendMessage
SkipDuplicate --> End
LogError --> End
style Start fill:#f9f,stroke:#333
style End fill:#f9f,stroke:#333
```

**Diagram sources**
- [notification_manager.py](file://app/modules/token_monitoring/services/notification_manager.py#L1-L335)

**Section sources**
- [notification_manager.py](file://app/modules/token_monitoring/services/notification_manager.py#L1-L335)

## Service Layer Implementation

The service layer implementation of the Token Monitoring module follows a clean, modular design with well-defined responsibilities. The TokenMonitoringService wraps the existing HTTP request decorator to detect token deactivation events during API calls. When a token deactivation is detected (typically through a 403 Forbidden response), the service triggers notifications through the NotificationManager. The TokenExpirationService handles proactive monitoring of token expiration dates, checking for tokens that will expire within predefined warning periods (14, 3, and 1 day). The NotificationManager coordinates the delivery of notifications to users via Telegram, ensuring that each user receives appropriate alerts based on their shop's token status. All services are designed to be stateless and can be easily integrated into the application's dependency injection system.

**Section sources**
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py#L1-L208)
- [token_expiration_service.py](file://app/modules/token_monitoring/services/token_expiration_service.py#L1-L313)
- [notification_manager.py](file://app/modules/token_monitoring/services/notification_manager.py#L1-L335)

## Integration and Startup

```mermaid
sequenceDiagram
participant App as Application
participant Startup as startup.py
participant Integration as integration.py
participant HR as http_request.py
App->>Startup : setup_token_monitoring_for_app()
Startup->>Startup : initialize_token_monitoring()
Startup->>Integration : install_token_monitoring()
Integration->>Integration : install()
Integration->>HR : Store original decorator
Integration->>Integration : Create enhanced decorator
Integration->>HR : Replace try_except_decorator
Startup->>Scheduler : start_token_monitoring_scheduler()
Scheduler->>Scheduler : start_daily_expiration_check()
Scheduler->>Scheduler : _daily_check_loop()
App->>Startup : shutdown_token_monitoring()
Startup->>Scheduler : stop_token_monitoring_scheduler()
Startup->>Integration : uninstall_token_monitoring()
Integration->>HR : Restore original decorator
```

**Diagram sources**
- [startup.py](file://app/modules/token_monitoring/startup.py#L1-L119)
- [integration.py](file://app/modules/token_monitoring/integration.py#L1-L111)

**Section sources**
- [startup.py](file://app/modules/token_monitoring/startup.py#L1-L119)
- [integration.py](file://app/modules/token_monitoring/integration.py#L1-L111)

## Data Models and Database Schema

```mermaid
erDiagram
TOKEN_NOTIFICATION_TRACKER {
integer id PK
string shop_id
bigint user_telegram_id
string notification_type
timestamp token_expiry_date
timestamp sent_at
timestamp resolved_at
}
WB_TOKEN {
integer id PK
string api_key
integer user_id
string shop_id
timestamp expires
boolean active
boolean read_only
}
WB_CABINET {
integer id PK
string shop_id
string name
}
WB_USER_CABINET {
integer id PK
integer wb_cabinet_id FK
integer user_id FK
string name
}
USER {
integer id PK
bigint user_telegram_id
string username
}
TOKEN_NOTIFICATION_TRACKER ||--o{ WB_CABINET : "shop_id"
TOKEN_NOTIFICATION_TRACKER ||--o{ USER : "user_telegram_id"
WB_TOKEN }o--|| WB_CABINET : "shop_id"
WB_USER_CABINET }o--|| WB_CABINET : "wb_cabinet_id"
WB_USER_CABINET }o--|| USER : "user_id"
```

**Diagram sources**
- [models.py](file://app/modules/token_monitoring/models.py#L1-L80)
- [f8e1d9c2a3b4_add_token_notification_tracker_table.py](file://alembic/versions/f8e1d9c2a3b4_add_token_notification_tracker_table.py#L1-L57)

**Section sources**
- [models.py](file://app/modules/token_monitoring/models.py#L1-L80)
- [f8e1d9c2a3b4_add_token_notification_tracker_table.py](file://alembic/versions/f8e1d9c2a3b4_add_token_notification_tracker_table.py#L1-L57)

## Redis Caching Strategy
The Token Monitoring module does not implement Redis caching for token status information. Instead, it relies on direct database queries to ensure the most current token status is always used. This design decision prioritizes accuracy over performance, as token status changes must be detected immediately to prevent service disruptions. The system leverages the application's existing Redis infrastructure for other purposes, such as rate limiting and session management, but maintains a direct connection to the database for token monitoring operations. This approach ensures that token expiration checks and permission validations always reflect the current state in the database without potential staleness from cached data.

**Section sources**
- [client_bot/redis_manager.py](file://app/client_bot/redis_manager.py)
- [arq_workers/arq_redis_settings.py](file://app/arq_workers/arq_redis_settings.py)

## Common Issues and Solutions

### False Expiration Alerts
False expiration alerts are prevented through the use of database constraints and state tracking. The TokenNotificationTracker table includes a unique constraint on (shop_id, user_telegram_id, notification_type) to prevent duplicate notifications. Additionally, each notification record includes a resolved_at timestamp that allows the system to track when a token issue has been resolved, preventing re-notification for the same issue.

### API Rate Limiting During Checks
API rate limiting is avoided by not making external API calls during token expiration checks. The system relies on stored token expiration dates in the database rather than validating tokens through the Wildberries API. This approach minimizes external requests while still providing accurate expiration monitoring based on the token's known lifespan.

### Handling Revoked Tokens
Revoked tokens are detected through the TokenMonitoringService, which wraps HTTP request decorators to catch 403 Forbidden responses. When a token is found to be invalid during an API call, the service triggers immediate notifications to users, alerting them to the revoked token status. The system also marks the token as inactive in the database to prevent future use.

**Section sources**
- [token_monitoring_service.py](file://app/modules/token_monitoring/services/token_monitoring_service.py#L1-L208)
- [token_expiration_service.py](file://app/modules/token_monitoring/services/token_expiration_service.py#L1-L313)
- [notification_manager.py](file://app/modules/token_monitoring/services/notification_manager.py#L1-L335)

## Configuration Options

### Monitoring Frequency
The token expiration monitoring frequency is configurable through the daily_check_time parameter in the TokenMonitoringScheduler. By default, checks run daily at 9:00 AM, but this can be adjusted to any time of day based on operational requirements.

### Notification Thresholds
Notification thresholds are defined by the WARNING_STAGES constant in the TokenExpirationService, which specifies the days before expiration when notifications should be sent (14, 3, and 1 day). These thresholds can be modified to adjust the timing of expiration warnings based on business needs.

### Service Activation
The token monitoring system can be selectively activated through configuration parameters in the initialize_token_monitoring function:
- enable_decorator_monitoring: Enables HTTP decorator monitoring for token deactivation detection
- enable_expiration_scheduler: Starts the expiration scheduler for proactive monitoring
- daily_check_time: Sets the time of day for daily expiration checks

**Section sources**
- [scheduler.py](file://app/modules/token_monitoring/scheduler.py#L1-L185)
- [token_expiration_service.py](file://app/modules/token_monitoring/services/token_expiration_service.py#L1-L313)
- [startup.py](file://app/modules/token_monitoring/startup.py#L1-L119)

## Usage Examples

### Token Validation Workflow
```mermaid
flowchart TD
Start([Get Token Status]) --> TIS["TokenInfoService.get_shop_token_status()"]
TIS --> DB["Query WBToken records"]
DB --> Analyze["Analyze token validity and permissions"]
Analyze --> Aggregate["Aggregate permissions from valid tokens"]
Aggregate --> CheckRequired["Check against REQUIRED_RIGHTS"]
CheckRequired --> DetermineStatus["Determine shop status"]
DetermineStatus --> FindExpiring["Find expiring tokens"]
FindExpiring --> CreateReport["Create TokenStatusReport"]
CreateReport --> Return["Return comprehensive status report"]
Return --> End([Workflow complete])
```

**Diagram sources**
- [token_info_service.py](file://app/modules/token_monitoring/services/token_info_service.py#L1-L353)

### Permission Checking Against Wildberries API
The system validates permissions by checking the categories field of stored WBToken records against the REQUIRED_RIGHTS set, which includes "Контент" (Content), "Статистика" (Statistics), "Аналитика" (Analytics), and "Продвижение" (Promotion). This validation occurs without making additional API calls by relying on permission data stored when tokens are initially created or updated. The TokenInfoService aggregates permissions from all valid tokens for a shop, providing a comprehensive view of available capabilities.

**Section sources**
- [token_info_service.py](file://app/modules/token_monitoring/services/token_info_service.py#L1-L353)
- [token_expiration_service.py](file://app/modules/token_monitoring/services/token_expiration_service.py#L1-L313)