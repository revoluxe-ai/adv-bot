# Billing System

<cite>
**Referenced Files in This Document**   
- [pricer.py](file://app/modules/billing/pricer/pricer.py)
- [tariffs.py](file://app/modules/billing/pricer/tariffs.py)
- [billing.py](file://app/modules/billing/billing.py)
- [models.py](file://app/modules/billing/models.py)
- [redis_lock.py](file://app/modules/billing/redis_lock.py)
- [redis_manager.py](file://app/modules/billing/redis_manager.py)
- [di.py](file://app/modules/billing/di.py)
- [billing_lock.py](file://app/core/redis_manager_v2/mixins/billing_lock.py)
- [billing_check.py](file://app/core/redis_manager_v2/mixins/billing_check.py)
- [settings_master.py](file://app/settings/settings_master.py)
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
The Billing System module is responsible for managing daily billing operations for advertising campaigns in the platform. It handles usage tracking, pricing calculations based on tariff models, and payment processing for active campaigns. The system ensures accurate billing through a combination of database transactions and Redis-based locking mechanisms to prevent race conditions. This document provides a comprehensive overview of the architecture, implementation details, and operational characteristics of the billing system.

## Project Structure
The Billing System is organized within the `app/modules/billing` directory with a clear separation of concerns. The module contains subcomponents for pricing calculations, billing processing, data models, and Redis integration.

```mermaid
graph TB
subgraph "Billing Module"
Pricer[pricer/]
Billing[billing.py]
Models[models.py]
RedisLock[redis_lock.py]
RedisManager[redis_manager.py]
DI[di.py]
end
subgraph "Pricer Submodule"
PricerPy[pricer.py]
Tariffs[tariffs.py]
TariffsText[tariffs_text.py]
end
subgraph "Core Redis Mixins"
BillingLock[billing_lock.py]
BillingCheck[billing_check.py]
end
Pricer --> Billing
RedisLock --> Billing
RedisManager --> Billing
Models --> Billing
DI --> Billing
BillingLock --> RedisLock
BillingCheck --> RedisManager
```

**Diagram sources**
- [app/modules/billing](file://app/modules/billing)
- [app/modules/billing/pricer](file://app/modules/billing/pricer)
- [app/core/redis_manager_v2/mixins](file://app/core/redis_manager_v2/mixins)

**Section sources**
- [app/modules/billing](file://app/modules/billing)
- [app/modules/billing/pricer](file://app/modules/billing/pricer)

## Core Components
The Billing System consists of several core components that work together to process daily billing for advertising campaigns. The system calculates pricing based on the number of active campaigns and additional services, processes payments from user balances or bonuses, and maintains billing records. Key components include the Pricer for tariff calculations, the billing processor for payment execution, Redis-based locking mechanisms to prevent concurrent execution, and data models for storing billing records.

**Section sources**
- [pricer.py](file://app/modules/billing/pricer/pricer.py)
- [billing.py](file://app/modules/billing/billing.py)
- [models.py](file://app/modules/billing/models.py)
- [redis_lock.py](file://app/modules/billing/redis_lock.py)
- [redis_manager.py](file://app/modules/billing/redis_manager.py)

## Architecture Overview
The Billing System follows a modular architecture with clear separation between pricing logic, payment processing, and infrastructure components. The system operates on a daily cycle, processing billing for all active advertising campaigns. It uses a global Redis lock to ensure only one instance runs at a time, preventing race conditions in billing operations.

```mermaid
sequenceDiagram
participant Scheduler
participant Billing as Billing System
participant Redis as Redis
participant DB as Database
Scheduler->>Billing : Trigger daily billing
Billing->>Redis : Acquire global lock
Redis-->>Billing : Lock acquired
Billing->>DB : Fetch active cabinets
DB-->>Billing : Cabinet IDs
loop For each cabinet
Billing->>DB : Load cabinet with relations
DB-->>Billing : Cabinet data
Billing->>Redis : Check daily processing flag
Redis-->>Billing : Flag status
alt Already processed
Billing->>Billing : Skip cabinet
else Not processed
Billing->>Pricer : Calculate daily price
Pricer-->>Billing : Price
Billing->>DB : Process payment
DB-->>Billing : Transaction result
Billing->>Redis : Set processing flag
end
end
Billing->>Redis : Release global lock
Billing-->>Scheduler : Processing complete
```

**Diagram sources**
- [billing.py](file://app/modules/billing/billing.py#L290-L329)
- [redis_lock.py](file://app/modules/billing/redis_lock.py)
- [redis_manager.py](file://app/modules/billing/redis_manager.py)

## Detailed Component Analysis

### Pricer Implementation
The Pricer component is responsible for calculating billing costs based on tariff models and the number of active advertising campaigns. It implements tiered pricing where the cost per campaign decreases as the number of campaigns increases.

```mermaid
classDiagram
class Pricer {
+text : str
-_tariffs : dict
+get_advs_count(session, shop_id) int
+get_month_tariff_for_count_advs(session, shop_id) int
+get_tariff_for_day(tariff_for_month) float
+get_price_for_day_for_shop(session, shop_id) float
+get_price_for_count_advs_in_cabinet_for_month(count_advs) float
+get_payment_for_adv(sum_payment, count_advs) float
+get_automactic_tariff(session, shop_id) int
-_get_month_tariff_for_white_list_updater(session, shop_id) int
-_get_month_tariff_for_autoupdate_target_place(session, shop_id) int
}
class Tariffs {
+tariffs : dict
}
Pricer --> Tariffs : "uses"
```

**Diagram sources**
- [pricer.py](file://app/modules/billing/pricer/pricer.py)
- [tariffs.py](file://app/modules/billing/pricer/tariffs.py)

**Section sources**
- [pricer.py](file://app/modules/billing/pricer/pricer.py#L0-L103)
- [tariffs.py](file://app/modules/billing/pricer/tariffs.py#L0-L9)

### Billing Processing Workflow
The billing processing workflow handles the end-to-end execution of daily billing operations, including payment processing, balance management, and record keeping.

```mermaid
flowchart TD
Start([Start Daily Billing]) --> GlobalLock["Acquire Global Redis Lock"]
GlobalLock --> CheckLock{"Lock Acquired?"}
CheckLock --> |No| End1([Billing Already Running])
CheckLock --> |Yes| FetchCabinets["Fetch Active Cabinet IDs"]
FetchCabinets --> CheckCabinets{"Cabinets Found?"}
CheckCabinets --> |No| End2([No Active Campaigns])
CheckCabinets --> |Yes| ProcessLoop["For Each Cabinet"]
ProcessLoop --> LoadCabinet["Load Cabinet Data"]
LoadCabinet --> CheckRedis["Check Redis Flag"]
CheckRedis --> FlagExists{"Processed Today?"}
FlagExists --> |Yes| SkipCabinet["Skip Cabinet"]
FlagExists --> |No| CheckDB["Check DB for Existing Payments"]
CheckDB --> PaymentExists{"Payments Exist?"}
PaymentExists --> |Yes| SetRedis["Set Redis Flag"]
PaymentExists --> |No| CalculatePrice["Calculate Daily Price"]
CalculatePrice --> CheckPrice{"Price > 0?"}
CheckPrice --> |No| SetRedis
CheckPrice --> |Yes| ProcessPayment["Process Payment"]
ProcessPayment --> CheckBalance{"Sufficient Funds?"}
CheckBalance --> |Yes| CreatePayments["Create Payment Records"]
CheckBalance --> |No| DeactivateCampaigns["Deactivate Campaigns"]
CreatePayments --> CommitDB["Commit Database Transaction"]
DeactivateCampaigns --> CommitDB
CommitDB --> SetRedisFlag["Set Redis Processing Flag"]
SetRedisFlag --> NextCabinet["Next Cabinet"]
SkipCabinet --> NextCabinet
NextCabinet --> MoreCabinets{"More Cabinets?"}
MoreCabinets --> |Yes| ProcessLoop
MoreCabinets --> |No| ReleaseLock["Release Global Lock"]
ReleaseLock --> End3([Processing Complete])
```

**Diagram sources**
- [billing.py](file://app/modules/billing/billing.py#L290-L367)
- [redis_manager.py](file://app/modules/billing/redis_manager.py)

**Section sources**
- [billing.py](file://app/modules/billing/billing.py#L0-L367)

### Redis Locking Mechanism
The Redis locking mechanism ensures that only one instance of the billing process runs at a time, preventing race conditions and duplicate billing.

```mermaid
classDiagram
class RedisLock {
+prefix : str
+default_ttl : int
+acquire_lock(ttl) bool
+release_lock() None
+is_locked() bool
+extend_lock(ttl) bool
+billing_lock(ttl) AsyncIterator[bool]
}
class BillingLockMixin {
+acquire_lock(ttl) bool
+release_lock() None
+is_locked() bool
+extend_lock(ttl) bool
+billing_lock(ttl) AsyncIterator[bool]
}
class BaseRedisManager {
+_client : RedisClient
+_get_key() str
}
RedisLock --> BillingLockMixin : "inherits"
RedisLock --> BaseRedisManager : "inherits"
BillingLockMixin --> BaseRedisManagerProtocol : "requires"
```

**Diagram sources**
- [redis_lock.py](file://app/modules/billing/redis_lock.py)
- [billing_lock.py](file://app/core/redis_manager_v2/mixins/billing_lock.py)
- [base_redis_manager.py](file://app/core/redis_manager_v2/base_redis_manager.py)

**Section sources**
- [redis_lock.py](file://app/modules/billing/redis_lock.py#L0-L26)
- [billing_lock.py](file://app/core/redis_manager_v2/mixins/billing_lock.py#L0-L98)

### Data Models
The data models define the structure of billing records stored in the database, including payment information for advertising campaigns.

```mermaid
erDiagram
ADVSETTING ||--o{ ADVPAYMENT : "has"
ADVSETTING {
int id PK
string shop_id
bool bot_active
bool auto_update_white_list
bool auto_update_target_place
}
ADVPAYMENT {
int id PK
date date
int adv_setting_id FK
string type
float amount
}
ADVPAYMENT }o--|| ADVSETTING : "belongs to"
```

**Diagram sources**
- [models.py](file://app/modules/billing/models.py)
- [common_slaves/wildberries/models.py](file://app/modules/common_slaves/wildberries/models.py)

**Section sources**
- [models.py](file://app/modules/billing/models.py#L0-L29)

## Dependency Analysis
The Billing System has dependencies on several external components and services, including database connections, Redis for locking and caching, and configuration settings.

```mermaid
graph LR
BillingSystem --> Pricer
BillingSystem --> RedisLock
BillingSystem --> RedisManager
BillingSystem --> Models
BillingSystem --> DI
Pricer --> Tariffs
Pricer --> Settings
RedisLock --> BillingLockMixin
RedisLock --> BaseRedisManager
RedisManager --> BillingCheckMixin
RedisManager --> BaseRedisManager
DI --> RedisClient
DI --> RedisLock
DI --> RedisManager
BillingSystem --> AsyncSession
BillingSystem --> Logger
```

**Diagram sources**
- [di.py](file://app/modules/billing/di.py)
- [billing.py](file://app/modules/billing/billing.py)
- [redis_lock.py](file://app/modules/billing/redis_lock.py)
- [redis_manager.py](file://app/modules/billing/redis_manager.py)

**Section sources**
- [di.py](file://app/modules/billing/di.py#L0-L42)
- [billing.py](file://app/modules/billing/billing.py)

## Performance Considerations
The Billing System is designed with performance and reliability in mind. It uses asynchronous processing to handle multiple cabinets concurrently, reducing overall processing time. The system implements a two-level idempotency mechanism using both Redis flags and database checks to prevent duplicate processing. The global Redis lock ensures that only one billing process runs at a time, preventing resource contention. Database operations are optimized with read-only sessions for initial queries and short-lived transactions for updates. The system also implements best-effort Redis flag setting, where successful database commits are not dependent on Redis operations, making the system resilient to Redis failures.

**Section sources**
- [billing.py](file://app/modules/billing/billing.py#L260-L291)
- [redis_manager.py](file://app/modules/billing/redis_manager.py#L0-L7)

## Troubleshooting Guide
Common issues in the Billing System typically relate to payment processing, locking mechanisms, and configuration settings. For billing inaccuracies, verify the tariff configuration in the settings and ensure the pricer is correctly calculating costs based on the number of active campaigns. For subscription management issues, check the campaign status in the database and verify that the auto-update features are properly configured. Payment failures can occur due to insufficient funds in the bonus or balance accounts; the system will automatically deactivate campaigns when funds are insufficient. If billing processes are not running, verify that the global Redis lock is not held by another process and check the scheduler configuration. For Redis-related issues, ensure that the Redis connection is stable and that the TTL settings are appropriate for the deployment environment.

**Section sources**
- [billing.py](file://app/modules/billing/billing.py#L96-L124)
- [settings_master.py](file://app/settings/settings_master.py#L342-L350)
- [test_billing.py](file://tests/modules/billing/test_billing.py)
- [test_billing_parallel.py](file://tests/modules/billing/test_billing_parallel.py)

## Conclusion
The Billing System provides a robust and reliable solution for managing daily billing operations for advertising campaigns. Its modular architecture separates concerns between pricing, payment processing, and infrastructure components, making it maintainable and extensible. The system's use of Redis for locking and idempotency ensures data consistency and prevents race conditions. The tiered pricing model implemented in the Pricer component allows for flexible tariff management based on the number of active campaigns. With its comprehensive error handling and idempotent design, the system can recover gracefully from failures and ensure accurate billing. The architecture supports future enhancements such as integration with external payment gateways and more sophisticated pricing models.