# Real-time Updates

<cite>
**Referenced Files in This Document**   
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py)
- [redis_manager.py](file://app/client_bot/redis_manager.py)
- [base_redis_manager.py](file://app/core/redis_manager_v2/base_redis_manager.py)
- [base_redis_manager.py](file://app/core/redis_manager/base_redis_manager.py)
- [redis_client.py](file://app/core/redis_manager/redis_client.py)
- [redis_client.py](file://app/core/redis_manager_v2/redis_client.py)
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [adv_setting_redis_cache.py](file://app/core/redis_cache/mixins/main_objects_mixins/adv_setting_redis_cache.py)
- [last_target_place_update_redis_manager.py](file://app/modules/shop_runner/service_manager/old_modules/auto_updater_target_place/last_target_place_update_redis_manager.py)
- [target_place_updater_redis_cache.py](file://app/modules/shop_runner/service_manager/old_modules/setting_auto_updater/modules/target_place_updater/redis_cache.py)
- [auto_white_list_updater_redis_cache.py](file://app/modules/shop_runner/service_manager/old_modules/setting_auto_updater/modules/white_list_updater/auto_white_list_updater/redis_cache/redis_cache.py)
- [billing_redis_manager.py](file://app/modules/billing/redis_manager.py)
- [calculated_keywords_redis_cache_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Redis-Based Event Propagation Architecture](#redis-based-event-propagation-architecture)
3. [Core Components and Mixins](#core-components-and-mixins)
4. [Event Flow and Data Mutation](#event-flow-and-data-mutation)
5. [Channel Naming Conventions and Event Payloads](#channel-naming-conventions-and-event-payloads)
6. [Error Handling and Message Transmission](#error-handling-and-message-transmission)
7. [Performance Considerations and Message Durability](#performance-considerations-and-message-durability)
8. [Debugging Message Flow](#debugging-message-flow)
9. [Integration with Client Bot for Telegram Notifications](#integration-with-client-bot-for-telegram-notifications)
10. [Conclusion](#conclusion)

## Introduction
The adv-bot system implements a robust real-time update mechanism using Redis-based event propagation to ensure immediate synchronization across system components upon data changes. This document details how Redis pub/sub and key-space notifications are leveraged to trigger updates for position changes, keyword updates, and shop configuration modifications. The architecture utilizes specialized Redis mixins such as wb_positions.py and redis_manager.py to manage event publishing and subscription. The system ensures that data mutations result in appropriate cache invalidation or UI updates through real-time channels, maintaining consistency across distributed components.

**Section sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)

## Redis-Based Event Propagation Architecture

```mermaid
graph TB
subgraph "Data Mutation Sources"
A[Position Changes] --> B[Keyword Updates]
B --> C[Shop Configuration]
C --> D[Auto-Updaters]
end
subgraph "Redis Event System"
D --> E[Redis Pub/Sub]
E --> F[Key-Space Notifications]
F --> G[Event Propagation]
end
subgraph "System Components"
G --> H[Cache Invalidation]
G --> I[UI Updates]
G --> J[Telegram Notifications]
G --> K[Internal Services]
end
subgraph "Client Integration"
J --> L[Telegram Users]
end
```

**Diagram sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)
- [base_redis_manager.py](file://app/core/redis_manager_v2/base_redis_manager.py#L1-L35)

**Section sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)
- [base_redis_manager.py](file://app/core/redis_manager_v2/base_redis_manager.py#L1-L35)

## Core Components and Mixins

### WBPositionsMixin Analysis
The WBPositionsMixin class provides specialized functionality for managing position data in Redis, serving as a critical component in the real-time update mechanism.

```mermaid
classDiagram
class WBPositionsMixin {
+add_positions_to_redis(positions)
+get_keyword_position(keyword, nmid)
+get_keywords_positions(adv_setting, texts)
+set_position_to_out_index(position)
}
class WBClustersMixin {
+get_cluster_and_preset(keyword)
}
class BaseRedisManagerProtocol {
_key : str
prefix : str
client : Redis
}
WBPositionsMixin --> WBClustersMixin : "extends"
WBPositionsMixin --> BaseRedisManagerProtocol : "implements"
```

**Diagram sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)
- [wb_clusters.py](file://app/core/redis_manager_v2/mixins/wb_clusters.py#L1-L10)

**Section sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)

### Redis Manager Hierarchy
The Redis manager classes form a hierarchical structure that enables consistent Redis operations across the application.

```mermaid
classDiagram
class BaseRedisManager {
+prefix : str
+default_ttl : int
+__init__(redis_client, ttl)
+_get_key(*args, **kwargs)
+_client : RedisClient
+_resolve_ttl(ttl)
}
class BaseRedis {
+_client : Redis
+client : Redis
}
class RedisManager {
+_instance : RedisManager
+_redis_conn : Redis
+get_connection()
}
BaseRedisManager <|-- BillingRedisManager
BaseRedisManager <|-- CalculatedKeywordsRedisManager
BaseRedis <-- RedisManager
```

**Diagram sources**
- [base_redis_manager.py](file://app/core/redis_manager_v2/base_redis_manager.py#L1-L35)
- [base_redis_manager.py](file://app/core/redis_manager/base_redis_manager.py#L1-L21)
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)

**Section sources**
- [base_redis_manager.py](file://app/core/redis_manager_v2/base_redis_manager.py#L1-L35)
- [base_redis_manager.py](file://app/core/redis_manager/base_redis_manager.py#L1-L21)

## Event Flow and Data Mutation

### Position Update Flow
The system implements a comprehensive flow for position updates, from data mutation to client notification.

```mermaid
sequenceDiagram
participant DataLayer as Data Layer
participant RedisManager as Redis Manager
participant Cache as Redis Cache
participant ClientBot as Client Bot
participant Telegram as Telegram User
DataLayer->>RedisManager : add_positions_to_redis()
RedisManager->>Cache : SET adv_positions : {keyword} : {nmid}
Cache-->>RedisManager : OK
RedisManager->>RedisManager : Publish event
RedisManager->>ClientBot : Notify via pub/sub
ClientBot->>Telegram : Send position update
Note over DataLayer,Telegram : Real-time position update flow
```

**Diagram sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)

**Section sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)

### Auto-Updater Integration
The auto-updater components integrate with Redis to track and propagate configuration changes.

```mermaid
classDiagram
class LastTargetPlaceUpdateRedisManager {
prefix : "last_target_place_update"
}
class LastSetUpTargetPlace {
prefix : "last_set_up_target_place"
}
class LastSetDownTargetPlace {
prefix : "last_set_down_target_place"
}
class AdvSettingRedisCache {
last_auto_adding_phrase_to_white_list
last_auto_delete_white_list
}
LastTargetPlaceUpdateRedisManager --> AdvSettingRedisCache : "inherits"
LastSetUpTargetPlace --> AdvSettingRedisCache : "inherits"
LastSetDownTargetPlace --> AdvSettingRedisCache : "inherits"
```

**Diagram sources**
- [last_target_place_update_redis_manager.py](file://app/modules/shop_runner/service_manager/old_modules/auto_updater_target_place/last_target_place_update_redis_manager.py#L1-L17)
- [target_place_updater_redis_cache.py](file://app/modules/shop_runner/service_manager/old_modules/setting_auto_updater/modules/target_place_updater/redis_cache.py#L1-L26)
- [auto_white_list_updater_redis_cache.py](file://app/modules/shop_runner/service_manager/old_modules/setting_auto_updater/modules/white_list_updater/auto_white_list_updater/redis_cache/redis_cache.py#L1-L14)

**Section sources**
- [last_target_place_update_redis_manager.py](file://app/modules/shop_runner/service_manager/old_modules/auto_updater_target_place/last_target_place_update_redis_manager.py#L1-L17)

## Channel Naming Conventions and Event Payloads

### Redis Key Structure
The system follows a consistent naming convention for Redis keys to ensure predictable access patterns.

```mermaid
flowchart TD
A[Base Key Patterns] --> B["adv_positions:{keyword}:{nmid}"]
A --> C["calculated_keywords:{adv_id}"]
A --> D["last_target_place_update:{adv_id}"]
A --> E["last_set_up_target_place:{adv_id}"]
A --> F["last_set_down_target_place:{adv_id}"]
G[Data Types] --> H[Position Data]
G --> I[Keyword Data]
G --> J[Configuration Data]
B --> H
C --> I
D --> J
E --> J
F --> J
style A fill:#f9f,stroke:#333
style G fill:#f9f,stroke:#333
```

**Diagram sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)
- [calculated_keywords_redis_cache_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py#L1-L63)
- [last_target_place_update_redis_manager.py](file://app/modules/shop_runner/service_manager/old_modules/auto_updater_target_place/last_target_place_update_redis_manager.py#L1-L17)

**Section sources**
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)
- [calculated_keywords_redis_cache_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py#L1-L63)

## Error Handling and Message Transmission

### Redis Connection Management
The system implements robust error handling for Redis operations to ensure message reliability.

```mermaid
flowchart TD
A[Redis Operation] --> B{Operation Successful?}
B --> |Yes| C[Complete Successfully]
B --> |No| D{Error Type}
D --> E[Connection Error]
D --> F[Data Error]
D --> G[Timeout Error]
E --> H[Retry with Backoff]
F --> I[Log and Skip]
G --> J[Increase Timeout]
H --> K[Reattempt Operation]
K --> B
I --> L[Continue Processing]
J --> K
style A fill:#f9f,stroke:#333
style D fill:#f9f,stroke:#333
```

**Diagram sources**
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)
- [base_redis_manager.py](file://app/core/redis_manager_v2/base_redis_manager.py#L1-L35)

**Section sources**
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)

## Performance Considerations and Message Durability

### Redis Configuration and Optimization
The system is configured to balance performance and durability requirements.

```mermaid
graph LR
A[Performance Factors] --> B[Connection Pooling]
A --> C[Pipeline Operations]
A --> D[Batch Processing]
A --> E[Caching Strategy]
F[Durability Factors] --> G[Persistence Configuration]
F --> H[Replication Setup]
F --> I[Failover Mechanisms]
F --> J[Monitoring and Alerts]
B --> K[Reduced Latency]
C --> K
D --> K
E --> K
G --> L[Data Safety]
H --> L
I --> L
J --> L
style A fill:#f9f,stroke:#333
style F fill:#f9f,stroke:#333
```

**Diagram sources**
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py#L1-L20)
- [base_redis_manager.py](file://app/core/redis_manager_v2/base_redis_manager.py#L1-L35)
- [redis_client.py](file://app/core/redis_manager/redis_client.py#L1-L15)

**Section sources**
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py#L1-L20)

## Debugging Message Flow

### Monitoring and Logging Strategy
The system implements comprehensive logging to facilitate debugging of message flows.

```mermaid
flowchart TD
A[Message Generated] --> B[Log Entry Created]
B --> C[Include Timestamp]
C --> D[Include Message Type]
D --> E[Include Payload Size]
E --> F[Include Source Component]
F --> G[Include Destination]
H[Message Processed] --> I[Log Processing Result]
I --> J{Success?}
J --> |Yes| K[Log Success]
J --> |No| L[Log Error Details]
L --> M[Include Exception]
M --> N[Include Stack Trace]
O[Periodic Audit] --> P[Check Log Consistency]
P --> Q[Verify Message Delivery]
Q --> R[Report Anomalies]
style A fill:#f9f,stroke:#333
style H fill:#f9f,stroke:#333
style O fill:#f9f,stroke:#333
```

**Diagram sources**
- [calculated_keywords_redis_cache_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py#L1-L63)
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)
- [wb_positions.py](file://app/core/redis_manager_v2/mixins/wb_positions.py#L1-L94)

**Section sources**
- [calculated_keywords_redis_cache_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py#L1-L63)

## Integration with Client Bot for Telegram Notifications

### Notification Propagation Path
The system integrates Redis events with the client bot to deliver real-time notifications to Telegram users.

```mermaid
sequenceDiagram
participant DataChange as Data Change
participant Redis as Redis Pub/Sub
participant ClientBot as Client Bot
participant MessageManager as Message Manager
participant Telegram as Telegram User
DataChange->>Redis : Publish event
Redis->>ClientBot : Subscribe to channel
ClientBot->>MessageManager : Process event
MessageManager->>MessageManager : Format message
MessageManager->>Telegram : Send notification
Telegram-->>MessageManager : Delivery receipt
MessageManager-->>ClientBot : Confirmation
ClientBot-->>Redis : Acknowledge receipt
Note over DataChange,Telegram : End-to-end notification flow
```

**Diagram sources**
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)
- [message_manager.py](file://app/client_bot/message_manager.py#L1-L15)
- [single_messages.py](file://app/client_bot/single_messages.py#L1-L10)

**Section sources**
- [redis_manager.py](file://app/client_bot/redis_manager.py#L1-L23)

## Conclusion
The adv-bot system implements a sophisticated real-time update mechanism using Redis-based event propagation. The architecture leverages Redis pub/sub and key-space notifications to ensure immediate synchronization across system components upon data changes. Key components like the WBPositionsMixin and various Redis manager classes provide specialized functionality for handling position changes, keyword updates, and shop configuration modifications. The system follows consistent channel naming conventions and implements robust error handling to ensure message reliability. Performance considerations are addressed through connection pooling, pipeline operations, and batch processing, while comprehensive logging enables effective debugging of message flows. The integration with the client bot allows for real-time notifications to be pushed to Telegram users, completing the end-to-end real-time update mechanism.