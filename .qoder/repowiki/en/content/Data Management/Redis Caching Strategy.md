# Redis Caching Strategy

<cite>
**Referenced Files in This Document**   
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [redis.py](file://app/core/di/databases/redis.py)
- [redis_client.py](file://app/core/redis_manager/redis_client.py)
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)
- [adv_setting_redis_cache.py](file://app/core/redis_cache/mixins/main_objects_mixins/adv_setting_redis_cache.py)
- [billing_lock.py](file://app/modules/billing/redis_lock.py)
- [billing_check.py](file://app/core/redis_manager_v2/mixins/billing_check.py)
- [redis_manager.py](file://app/modules/billing/redis_manager.py)
- [redis_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py)
- [predic_ctr.py](file://app/core/redis_manager_v2/mixins/predic_ctr.py)
- [arq_redis_settings.py](file://app/arq_workers/arq_redis_settings.py)
- [workers.py](file://app/arq_workers/workers.py)
- [secure_redis_storage.py](file://app/core/mp/wb/token_management/secure_redis_storage.py)
- [simple_timestamp.py](file://app/core/redis_cache/mixins/data_types/simple_timestamp.py)
- [pass_time_redis_cache_base.py](file://app/core/redis_cache/mixins/data_types/pass_time_redis_cache_base.py)
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
The Redis caching architecture in the adv-bot system serves multiple critical functions including caching frequently accessed data, rate limiting, distributed locking, and task queuing. This document provides a comprehensive analysis of the Redis implementation, covering connection management, data structures, key naming conventions, TTL policies, and specific use cases such as AdvSetting caching, billing locks, and calculated keywords management. The system employs a sophisticated multi-layered approach to Redis usage, with different modules handling specific aspects of the caching strategy.

## Project Structure

```mermaid
graph TD
subgraph "Redis Configuration"
redis_config[redis_config.py]
redis_client[redis_client.py]
end
subgraph "Core Redis Components"
redis_cache_base[redis_cache_base.py]
redis_manager[redis_manager/]
redis_manager_v2[redis_manager_v2/]
end
subgraph "Application Modules"
billing[Billing Module]
keywords[Calculated Keywords Manager]
arq[ARQ Workers]
tokens[Token Management]
end
redis_config --> redis_client
redis_client --> redis_cache_base
redis_cache_base --> redis_manager
redis_cache_base --> redis_manager_v2
redis_manager --> billing
redis_manager_v2 --> billing
redis_manager --> keywords
redis_client --> arq
redis_client --> tokens
```

**Diagram sources**
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [redis_client.py](file://app/core/redis_manager/redis_client.py)
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)

**Section sources**
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [redis_client.py](file://app/core/redis_manager/redis_client.py)
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)

## Core Components

The Redis architecture in adv-bot consists of several core components that work together to provide a robust caching solution. The system is built around a dependency injection pattern that manages Redis connections and provides them to various components. The core components include connection management, caching base classes, specialized managers for different use cases, and integration with task queues.

**Section sources**
- [redis.py](file://app/core/di/databases/redis.py)
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)
- [base_redis_manager.py](file://app/core/redis_manager/base_redis_manager.py)

## Architecture Overview

```mermaid
graph TD
Client[Application Client]
DI[Dependency Injector]
Connection[Redis Connection Pool]
Caching[Caching Layer]
Locking[Locking System]
Queuing[Task Queue]
Monitoring[Monitoring]
Client --> DI
DI --> Connection
Connection --> Caching
Connection --> Locking
Connection --> Queuing
Caching --> Monitoring
Locking --> Monitoring
Queuing --> Monitoring
subgraph "Caching Layer"
AdvSetting[AdvSetting Cache]
Keywords[Calculated Keywords]
PredictCTR[Predict CTR]
Tokens[Token State]
end
subgraph "Locking System"
BillingLock[Billing Global Lock]
ProcessCheck[Process Check Lock]
end
subgraph "Task Queue"
ARQ[ARQ Task Queue]
end
Caching --> AdvSetting
Caching --> Keywords
Caching --> PredictCTR
Caching --> Tokens
Locking --> BillingLock
Locking --> ProcessCheck
```

**Diagram sources**
- [redis.py](file://app/core/di/databases/redis.py)
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)
- [billing_lock.py](file://app/modules/billing/redis_lock.py)
- [arq_redis_settings.py](file://app/arq_workers/arq_redis_settings.py)

## Detailed Component Analysis

### Connection Management and Pooling Strategy

The Redis connection management in adv-bot is implemented through a dependency injection pattern that ensures proper lifecycle management of Redis connections. The system uses redis-py's async client with connection pooling capabilities.

```mermaid
classDiagram
class RedisConfig {
+string host
+int port
+int db
+string password
}
class RedisLifecycle {
+init(client)
+shutdown(client)
}
class create_redis_client {
+create_redis_client(app_config)
}
RedisConfig --> RedisLifecycle : "used by"
RedisConfig --> create_redis_client : "used by"
RedisLifecycle --> create_redis_client : "manages"
```

**Diagram sources**
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [redis.py](file://app/core/di/databases/redis.py)

**Section sources**
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [redis.py](file://app/core/di/databases/redis.py)

### AdvSetting Redis Cache Implementation

The AdvSetting caching system provides a specialized implementation for caching campaign settings with proper key naming and TTL management.

```mermaid
classDiagram
class RedisCacheBase {
+_prefix : str
+_client : Redis
+_key : str
+client : Redis
+key : str
}
class AdvSettingRedisCache {
+__unique_id : str
+_unique_id : str
}
class SimpleTimeStamp {
+set_timestamp()
+get() : datetime
}
class PassTimeRedisCacheBase {
+check_pass_time(pass_time_sec)
+set()
+get() : datetime
}
RedisCacheBase <|-- AdvSettingRedisCache
RedisCacheBase <|-- SimpleTimeStamp
RedisCacheBase <|-- PassTimeRedisCacheBase
```

**Diagram sources**
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)
- [adv_setting_redis_cache.py](file://app/core/redis_cache/mixins/main_objects_mixins/adv_setting_redis_cache.py)
- [simple_timestamp.py](file://app/core/redis_cache/mixins/data_types/simple_timestamp.py)
- [pass_time_redis_cache_base.py](file://app/core/redis_cache/mixins/data_types/pass_time_redis_cache_base.py)

**Section sources**
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)
- [adv_setting_redis_cache.py](file://app/core/redis_cache/mixins/main_objects_mixins/adv_setting_redis_cache.py)

### Billing Lock and Process Management

The billing system implements distributed locking and process tracking using Redis to prevent concurrent execution and track processing status.

```mermaid
sequenceDiagram
participant App as Application
participant BillingLock as BillingLock
participant Redis as Redis Server
App->>BillingLock : acquire_lock(ttl=900)
BillingLock->>Redis : SET billing_lock : global "1" EX 900 NX
Redis-->>BillingLock : Success/Failure
BillingLock-->>App : True/False
App->>BillingLock : is_locked()
BillingLock->>Redis : EXISTS billing_lock : global
Redis-->>BillingLock : 1/0
BillingLock-->>App : True/False
App->>BillingLock : release_lock()
BillingLock->>Redis : DEL billing_lock : global
Redis-->>BillingLock : OK
BillingLock-->>App : Done
```

**Diagram sources**
- [billing_lock.py](file://app/modules/billing/redis_lock.py)
- [billing_check.py](file://app/core/redis_manager_v2/mixins/billing_check.py)

**Section sources**
- [billing_lock.py](file://app/modules/billing/redis_lock.py)
- [billing_check.py](file://app/core/redis_manager_v2/mixins/billing_check.py)

### Calculated Keywords Cache Manager

The calculated keywords system uses Redis hashes to store keyword data with efficient retrieval and batch operations.

```mermaid
flowchart TD
Start([Set Keywords]) --> Pipeline["Create Redis Pipeline"]
Pipeline --> Loop["For each keyword"]
Loop --> HSet["hset(name=key, key=keyword.text, value=keyword.to_json())"]
HSet --> Check["More keywords?"]
Check --> |Yes| Loop
Check --> |No| Execute["Execute Pipeline"]
Execute --> End([Done])
GetStart([Get Keywords]) --> GetPipeline["Create Redis Pipeline"]
GetPipeline --> GetLoop["For each keyword"]
GetLoop --> GetHGet["hget(name=key, key=keyword.text)"]
GetHGet --> GetCheck["More keywords?"]
GetCheck --> |Yes| GetLoop
GetCheck --> |No| GetExecute["Execute Pipeline"]
GetExecute --> Process["Process Results"]
Process --> GetEnd([Return Keywords])
```

**Diagram sources**
- [redis_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py)

**Section sources**
- [redis_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py)

### Predict CTR Redis Mixin

The PredictCTR system implements both legacy and new key formats for storing CTR predictions with proper text cleaning and key normalization.

```mermaid
classDiagram
class PredictCTRRedisMixin {
+prefix : str
+key : str
+get_key(*args, **kwargs)
+_get_legacy_key(adv_id, keyword)
+_get_new_key(nmids, keyword)
+set_predict_ctr_with_pipeline_legacy()
+set_predict_ctr_with_pipeline_by_nmids()
+get_predict_ctr_by_nmids()
+_get_predict_ctr_by_key(key)
}
class BaseRedisManagerProtocol {
+_client : Redis
+prefix : str
}
BaseRedisManagerProtocol <|-- PredictCTRRedisMixin
```

**Diagram sources**
- [predic_ctr.py](file://app/core/redis_manager_v2/mixins/predic_ctr.py)

**Section sources**
- [predic_ctr.py](file://app/core/redis_manager_v2/mixins/predic_ctr.py)

### Task Queuing with ARQ

The system uses ARQ for task queuing with Redis as the backend, providing reliable task processing with proper error handling and retry mechanisms.

```mermaid
sequenceDiagram
participant Worker as ARQ Worker
participant Redis as Redis Queue
participant Task as create_complex_advs
Redis->>Worker : Poll for tasks
Worker->>Redis : Claim task
Redis-->>Worker : Task data
Worker->>Task : Execute
alt Success
Task-->>Worker : Result
Worker->>Redis : Store result
else Failure
Task-->>Worker : Exception
Worker->>Redis : Retry or fail
end
Worker->>Redis : Acknowledge completion
```

**Diagram sources**
- [arq_redis_settings.py](file://app/arq_workers/arq_redis_settings.py)
- [workers.py](file://app/arq_workers/workers.py)

**Section sources**
- [arq_redis_settings.py](file://app/arq_workers/arq_redis_settings.py)
- [workers.py](file://app/arq_workers/workers.py)

## Dependency Analysis

```mermaid
graph TD
redis_config[RedisConfig] --> redis_client[create_redis_client]
redis_client --> redis_lifecycle[RedisLifecycle]
redis_client --> redis_cache_base[RedisCacheBase]
redis_cache_base --> adv_setting_cache[AdvSettingRedisCache]
redis_cache_base --> simple_timestamp[SimpleTimeStamp]
redis_cache_base --> pass_time_cache[PassTimeRedisCacheBase]
redis_client --> billing_lock[BillingLock]
redis_client --> billing_check[BillingCheckMixin]
redis_client --> keywords_manager[RedisCalculatedKeywordsCacheManager]
redis_client --> predict_ctr[PredictCTRRedisMixin]
redis_client --> arq_worker[ARQ Worker]
redis_client --> token_storage[SecureRedisTokenStorage]
```

**Diagram sources**
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [redis.py](file://app/core/di/databases/redis.py)
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)
- [billing_lock.py](file://app/modules/billing/redis_lock.py)
- [billing_check.py](file://app/core/redis_manager_v2/mixins/billing_check.py)
- [redis_manager.py](file://app/modules/calculated_keywords_redis_cache_manager/redis_manager.py)
- [predic_ctr.py](file://app/core/redis_manager_v2/mixins/predic_ctr.py)
- [arq_redis_settings.py](file://app/arq_workers/arq_redis_settings.py)
- [secure_redis_storage.py](file://app/core/mp/wb/token_management/secure_redis_storage.py)

**Section sources**
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [redis.py](file://app/core/di/databases/redis.py)
- [redis_cache_base.py](file://app/core/redis_cache/redis_cache_base.py)

## Performance Considerations

The Redis implementation in adv-bot incorporates several performance optimization techniques:

1. **Connection Pooling**: The system uses redis-py's built-in connection pooling to minimize connection overhead.
2. **Pipelining**: Batch operations are implemented using Redis pipelines to reduce network round trips.
3. **Efficient Data Structures**: Hashes are used for related data to minimize key space and improve retrieval efficiency.
4. **Proper TTL Management**: Appropriate TTL values are set for different types of data to prevent memory bloat.
5. **Asynchronous Operations**: All Redis operations are performed asynchronously to avoid blocking the event loop.

The system also implements monitoring through aiocache plugins that track hit/miss ratios and timing information, allowing for performance analysis and optimization.

## Troubleshooting Guide

Common issues and their solutions:

1. **Connection Leaks**: Ensure proper lifecycle management through the RedisLifecycle class which handles connection shutdown.
2. **Cache Invalidation**: Implement proper TTL policies and use the release_lock methods to clean up after operations.
3. **Memory Optimization**: Monitor memory usage and adjust TTL values accordingly. Use Redis's memory analysis commands to identify large keys.
4. **High Availability**: Configure Redis with replication and consider using Redis Sentinel or Redis Cluster for production environments.
5. **Persistence**: Configure appropriate persistence options (RDB/AOF) based on data durability requirements.

**Section sources**
- [redis.py](file://app/core/di/databases/redis.py)
- [redis_client.py](file://app/core/redis_manager/redis_client.py)
- [redis_func_cache.py](file://app/utils/redis_func_cache.py)

## Conclusion

The Redis caching architecture in the adv-bot system is a comprehensive solution that addresses multiple requirements including data caching, distributed locking, and task queuing. The system is well-structured with clear separation of concerns and follows best practices for Redis usage. Key strengths include the dependency injection-based connection management, proper use of Redis data structures, and comprehensive error handling. The architecture supports high availability and performance requirements while providing extensibility for future enhancements.