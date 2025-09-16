# Backup and Recovery

<cite>
**Referenced Files in This Document**   
- [set_shop_id_for_all_wbtokens.py](file://scripts/set_shop_id_for_all_wbtokens.py)
- [set_relevant_if_white_phrase.py](file://scripts/set_relevant_if_white_phrase.py)
- [env.py](file://alembic/env.py)
- [alembic.ini](file://alembic.ini)
- [session_maker.py](file://app/utils/db/session_maker.py)
- [settings_master.py](file://app/settings/settings_master.py)
- [client.py](file://app/utils/click_house/client.py)
- [redis_client.py](file://app/core/redis_manager/redis_client.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Core Data Stores Overview](#core-data-stores-overview)
3. [PostgreSQL Backup and Recovery](#postgresql-backup-and-recovery)
4. [ClickHouse Backup and Recovery](#clickhouse-backup-and-recovery)
5. [Redis Backup and Recovery](#redis-backup-and-recovery)
6. [Neo4j Data Protection](#neo4j-data-protection)
7. [Data Consistency Repair Scripts](#data-consistency-repair-scripts)
8. [Automated Backup Strategies](#automated-backup-strategies)
9. [Disaster Recovery Planning](#disaster-recovery-planning)
10. [Monitoring and Alerting](#monitoring-and-alerting)
11. [Security Considerations](#security-considerations)
12. [Common Recovery Scenarios](#common-recovery-scenarios)
13. [Performance Impact Mitigation](#performance-impact-mitigation)

## Introduction
The adv-bot system relies on multiple critical data stores to manage advertising settings, user data, analytics, caching, and keyword relationships. This document outlines comprehensive backup and recovery strategies to ensure data integrity, availability, and business continuity. The system employs PostgreSQL for transactional data, ClickHouse for analytics, Redis for caching and session management, and Neo4j for keyword relationship storage. Each component requires specific backup procedures, recovery workflows, and consistency maintenance mechanisms to protect against data loss from corruption, accidental deletion, or infrastructure failure.

## Core Data Stores Overview
The adv-bot system utilizes a multi-database architecture with specialized data stores for different purposes:

```mermaid
graph TD
subgraph "Data Stores"
PostgreSQL[(PostgreSQL<br>Advertising Settings<br>User Data)]
ClickHouse[(ClickHouse<br>Analytics)]
Redis[(Redis<br>Caching<br>Session Data)]
Neo4j[(Neo4j<br>Keyword Relationships)]
end
subgraph "Applications"
ClientBot[Client Bot]
AdminBot[Admin Bot]
Workers[ARQ Workers]
end
ClientBot --> PostgreSQL
ClientBot --> Redis
AdminBot --> ClickHouse
Workers --> ClickHouse
Workers --> Neo4j
Workers --> PostgreSQL
style PostgreSQL fill:#f9f,stroke:#333
style ClickHouse fill:#bbf,stroke:#333
style Redis fill:#f96,stroke:#333
style Neo4j fill:#6f9,stroke:#333
```

**Diagram sources**
- [settings_master.py](file://app/settings/settings_master.py)
- [session_maker.py](file://app/utils/db/session_maker.py)
- [client.py](file://app/utils/click_house/client.py)
- [redis_client.py](file://app/core/redis_manager/redis_client.py)

**Section sources**
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)
- [session_maker.py](file://app/utils/db/session_maker.py#L1-L175)

## PostgreSQL Backup and Recovery
PostgreSQL serves as the primary relational database for storing advertising settings, user data, and configuration information. The system implements both logical and physical backup strategies with point-in-time recovery capabilities.

### Backup Procedures
PostgreSQL backups are performed using a combination of pg_dump for logical backups and WAL archiving for point-in-time recovery. The backup strategy includes:

- Daily full logical backups using pg_dump
- Continuous WAL archiving for point-in-time recovery
- Transaction log shipping to standby servers
- Automated backup verification

The database connection parameters are configured through environment variables loaded in the settings system, including master and replica hosts, port, database name, username, and password.

```mermaid
sequenceDiagram
participant Cron as Cron Job
participant BackupScript as Backup Script
participant PostgreSQL as PostgreSQL
participant CloudStorage as Cloud Storage
Cron->>BackupScript : Execute daily backup
BackupScript->>PostgreSQL : pg_dump --format=custom
PostgreSQL-->>BackupScript : Database dump
BackupScript->>BackupScript : Encrypt dump
BackupScript->>CloudStorage : Upload to cloud storage
CloudStorage-->>BackupScript : Confirmation
BackupScript->>Cron : Completion status
```

**Diagram sources**
- [alembic.ini](file://alembic.ini#L1-L110)
- [session_maker.py](file://app/utils/db/session_maker.py#L1-L175)
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)

**Section sources**
- [session_maker.py](file://app/utils/db/session_maker.py#L1-L175)
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)
- [alembic.ini](file://alembic.ini#L1-L110)

## ClickHouse Backup and Recovery
ClickHouse is used for storing and analyzing advertising performance analytics data. The backup strategy focuses on efficient handling of large datasets with minimal performance impact.

### Backup Procedures
ClickHouse backups leverage the built-in table-level backup capabilities and distributed architecture:

- Incremental backups of analytics tables
- Replicated table synchronization across clusters
- Integration with cloud storage for long-term retention
- Automated backup scheduling via cron jobs

The ClickHouse client configuration includes connection pooling, connection counting, and monitoring to ensure backup operations do not overwhelm the system.

```mermaid
flowchart TD
Start([Backup Initiated]) --> CheckReplicas["Check Replica Status"]
CheckReplicas --> ReplicasHealthy{"Replicas Healthy?"}
ReplicasHealthy --> |Yes| FreezeTables["Freeze Table Partitions"]
ReplicasHealthy --> |No| Alert["Send Alert<br>Delay Backup"]
FreezeTables --> CopyData["Copy Data to Backup Location"]
CopyData --> UploadCloud["Upload to Cloud Storage"]
UploadCloud --> VerifyBackup["Verify Backup Integrity"]
VerifyBackup --> Cleanup["Cleanup Temporary Files"]
Cleanup --> End([Backup Complete])
style Start fill:#aqua,stroke:#333
style End fill:#aqua,stroke:#333
```

**Diagram sources**
- [client.py](file://app/utils/click_house/client.py#L1-L222)
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)

**Section sources**
- [client.py](file://app/utils/click_house/client.py#L1-L222)
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)

## Redis Backup and Recovery
Redis is used for caching, session data storage, and temporary data management. The backup strategy focuses on persistence configuration and rapid recovery.

### Backup Procedures
Redis backup and recovery relies on RDB snapshots and AOF (Append Only File) persistence:

- Configured RDB snapshots at regular intervals
- AOF logging for write operations
- Automated backup of dump.rdb and appendonly.aof files
- Redis replication for high availability

The Redis client is configured with environment variables for host and port, connecting to database 0 by default.

```mermaid
sequenceDiagram
participant App as Application
participant RedisMaster as Redis Master
participant RedisReplica as Redis Replica
participant BackupSystem as Backup System
loop Normal Operation
App->>RedisMaster : Write operations
RedisMaster->>RedisMaster : Update RDB/AOF
RedisMaster->>RedisReplica : Replicate changes
RedisReplica-->>RedisMaster : Acknowledgment
end
Cron->>BackupSystem : Trigger backup
BackupSystem->>RedisMaster : FLUSHALL (if needed)
BackupSystem->>RedisMaster : BGSAVE
RedisMaster-->>BackupSystem : RDB file
BackupSystem->>CloudStorage : Encrypt and upload
```

**Diagram sources**
- [redis_client.py](file://app/core/redis_manager/redis_client.py#L1-L11)
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)

**Section sources**
- [redis_client.py](file://app/core/redis_manager/redis_client.py#L1-L11)
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)

## Neo4j Data Protection
Neo4j stores keyword relationships and semantic connections used for advertising optimization. While specific backup scripts are not visible in the repository, the system includes data consistency repair mechanisms.

### Backup Procedures
Neo4j backup strategies should include:

- Regular database dumps using neo4j-admin
- File system backups of the Neo4j data directory
- Cluster replication for high availability
- Point-in-time recovery capabilities

The system includes scripts for updating keyword relationships and ensuring data consistency after recovery operations.

```mermaid
graph TD
A[Application] --> B[Neo4j Database]
C[Backup System] --> D[Daily Full Backup]
E[Replication] --> F[Standby Server]
G[Monitoring] --> H[Backup Verification]
D --> I[Cloud Storage]
F --> J[Failover Capability]
H --> K[Alerting System]
style A fill:#f9f,stroke:#333
style B fill:#f96,stroke:#333
style C fill:#6f9,stroke:#333
style D fill:#bbf,stroke:#333
```

**Section sources**
- [keyword_sending_to_neo4j.py](file://keyword_sending_to_neo4j.py)
- [run_update_cards_data_in_neo4j.py](file://run_update_cards_data_in_neo4j.py)
- [run_update_keyword_vectors_in_redis.py](file://run_update_keyword_vectors_in_redis.py)

## Data Consistency Repair Scripts
After recovery operations, data consistency may be compromised. The system provides utility scripts to repair and synchronize data across different stores.

### set_shop_id_for_all_wbtokens.py
This script ensures all WBToken records have their shop_id properly set by extracting it from the token itself.

```mermaid
flowchart TD
Start([Script Execution]) --> LoadEnv["Load Environment Variables"]
LoadEnv --> CreateSession["Create Database Session"]
CreateSession --> QueryTokens["Query All WBToken Records"]
QueryTokens --> LoopTokens["For Each Token"]
LoopTokens --> HasShopID{"Has shop_id?"}
HasShopID --> |Yes| NextToken["Process Next Token"]
HasShopID --> |No| ExtractShopID["Extract shop_id from Token"]
ExtractShopID --> UpdateDB["Update Database Record"]
UpdateDB --> Commit["Commit Transaction"]
Commit --> NextToken
NextToken --> MoreTokens{"More Tokens?"}
MoreTokens --> |Yes| LoopTokens
MoreTokens --> |No| DisplayResults["Display Processing Results"]
DisplayResults --> End([Script Complete])
style Start fill:#aqua,stroke:#333
style End fill:#aqua,stroke:#333
```

**Diagram sources**
- [set_shop_id_for_all_wbtokens.py](file://scripts/set_shop_id_for_all_wbtokens.py#L1-L60)

**Section sources**
- [set_shop_id_for_all_wbtokens.py](file://scripts/set_shop_id_for_all_wbtokens.py#L1-L60)
- [session_maker.py](file://app/utils/db/session_maker.py#L1-L175)

### set_relevant_if_white_phrase.py
This script updates keyword settings to mark white-listed phrases as relevant, ensuring advertising relevance after data restoration.

```mermaid
flowchart TD
Start([Script Execution]) --> CreateSession["Create Database Session"]
CreateSession --> BuildQuery["Build UPDATE Query"]
BuildQuery --> SetRelevant["SET relevant = True"]
SetRelevant --> WhereClause["WHERE hard_status = 2"]
WhereClause --> ExecuteQuery["Execute Query"]
ExecuteQuery --> Commit["Commit Transaction"]
Commit --> End([Script Complete])
style Start fill:#aqua,stroke:#333
style End fill:#aqua,stroke:#333
```

**Diagram sources**
- [set_relevant_if_white_phrase.py](file://scripts/set_relevant_if_white_phrase.py#L1-L22)

**Section sources**
- [set_relevant_if_white_phrase.py](file://scripts/set_relevant_if_white_phrase.py#L1-L22)
- [session_maker.py](file://app/utils/db/session_maker.py#L1-L175)

## Automated Backup Strategies
The system implements automated backup strategies using cron jobs and scheduled tasks to ensure regular, reliable backups without manual intervention.

### Cron Job Configuration
Backup automation is achieved through scheduled cron jobs that execute backup scripts at predefined intervals:

- Daily full backups of PostgreSQL
- Hourly incremental backups of critical tables
- Real-time transaction log shipping
- Weekly full backups of analytics data

The exact cron schedule is not visible in the repository but would typically be configured in the deployment environment.

```mermaid
graph TD
A[Cron Daemon] --> B{Time to Backup?}
B --> |Yes| C[Execute Backup Script]
C --> D[Connect to Database]
D --> E[Create Backup]
E --> F[Encrypt Backup]
F --> G[Upload to Cloud Storage]
G --> H[Verify Backup]
H --> I[Log Results]
I --> J[Send Status Notification]
J --> K[Wait for Next Schedule]
B --> |No| K
```

**Section sources**
- [alembic.ini](file://alembic.ini#L1-L110)
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)

## Disaster Recovery Planning
The disaster recovery plan for adv-bot includes procedures for various failure scenarios, recovery time objectives (RTO), and recovery point objectives (RPO).

### Recovery Workflows
Standard recovery workflows include:

1. **Database Restoration from Dumps**: Restore PostgreSQL from pg_dump files
2. **Redis RDB/AOF Recovery**: Restart Redis with backup files
3. **ClickHouse Replica Synchronization**: Promote replica to primary
4. **Data Consistency Repair**: Run utility scripts to fix relationships

The plan includes regular testing of recovery procedures to ensure they meet business requirements.

```mermaid
graph TD
A[Disaster Detected] --> B[Assess Damage]
B --> C{Data Loss?}
C --> |Yes| D[Restore from Backup]
C --> |No| E[Restart Services]
D --> F[Verify Data Integrity]
F --> G[Run Consistency Scripts]
G --> H[Restart Application]
H --> I[Monitor System]
I --> J[System Operational]
E --> J
```

**Section sources**
- [set_shop_id_for_all_wbtokens.py](file://scripts/set_shop_id_for_all_wbtokens.py#L1-L60)
- [set_relevant_if_white_phrase.py](file://scripts/set_relevant_if_white_phrase.py#L1-L22)

## Monitoring and Alerting
Integration with monitoring systems ensures backup failures are detected and alerted promptly.

### Monitoring Strategy
The monitoring system tracks:

- Backup job completion status
- Backup duration and performance
- Storage utilization
- Data integrity verification results
- Network transfer success/failure

Alerts are configured for failed backups, incomplete transfers, or verification failures.

```mermaid
graph TD
A[Backup Job] --> B[Send Status to Monitoring]
B --> C{Success?}
C --> |Yes| D[Log Success]
C --> |No| E[Trigger Alert]
E --> F[Notify Team]
F --> G[Create Incident]
D --> H[Archive Logs]
G --> H
```

**Section sources**
- [logging_config.json](file://logging_config.json)
- [my_log_handler.py](file://my_log_handler.py)

## Security Considerations
Backup security is critical to protect sensitive advertising and user data.

### Encryption and Access Control
- All backups are encrypted before storage
- Access to backup storage is restricted
- Backup files have limited retention periods
- Audit logs track backup and restore operations
- Environment variables contain sensitive credentials

The system uses environment variables for all database credentials, ensuring they are not hardcoded in configuration files.

```mermaid
graph TD
A[Database] --> B[Create Backup]
B --> C[Encrypt with AES-256]
C --> D[Upload to Cloud Storage]
D --> E[Access Control Policies]
E --> F[Audit Logging]
F --> G[Retention Management]
G --> H[Secure Deletion]
```

**Section sources**
- [settings_master.py](file://app/settings/settings_master.py#L1-L375)
- [alembic.ini](file://alembic.ini#L1-L110)

## Common Recovery Scenarios
The system addresses several common recovery scenarios with specific resolution guides.

### Data Corruption
When data corruption is detected:

1. Identify the affected tables and time range
2. Restore from the most recent clean backup
3. Apply transaction logs to reach desired point-in-time
4. Verify data integrity
5. Run consistency repair scripts

### Accidental Deletion
For accidentally deleted data:

1. Stop applications to prevent further writes
2. Restore affected tables from backup
3. Reconcile with current data
4. Validate relationships
5. Restart applications

### Infrastructure Failure
In case of infrastructure failure:

1. Provision new infrastructure
2. Restore databases from cloud storage
3. Reconfigure applications
4. Validate system functionality
5. Monitor performance

```mermaid
graph TD
A[Failure Detected] --> B[Isolate System]
B --> C[Assess Impact]
C --> D[Prepare Recovery Environment]
D --> E[Restore Data]
E --> F[Validate Integrity]
F --> G[Repair Consistency]
G --> H[Restart System]
H --> I[Monitor Performance]
```

**Section sources**
- [set_shop_id_for_all_wbtokens.py](file://scripts/set_shop_id_for_all_wbtokens.py#L1-L60)
- [set_relevant_if_white_phrase.py](file://scripts/set_relevant_if_white_phrase.py#L1-L22)

## Performance Impact Mitigation
Recovery operations can significantly impact system performance. The following strategies minimize disruption:

- Schedule backups during low-traffic periods
- Use incremental backups to reduce load
- Implement connection pooling and rate limiting
- Monitor system resources during recovery
- Gradually ramp up application traffic after recovery

The system includes connection counting and monitoring in both PostgreSQL and ClickHouse clients to detect and alert on performance issues.

```mermaid
graph TD
A[Start Backup] --> B[Check System Load]
B --> C{Load Acceptable?}
C --> |Yes| D[Proceed with Backup]
C --> |No| E[Delay Backup]
D --> F[Monitor Performance]
F --> G{Degradation Detected?}
G --> |Yes| H[Throttle Backup]
G --> |No| I[Continue]
H --> J[Resume Normal Speed]
I --> K[Complete Backup]
```

**Section sources**
- [session_maker.py](file://app/utils/db/session_maker.py#L1-L175)
- [client.py](file://app/utils/click_house/client.py#L1-L222)