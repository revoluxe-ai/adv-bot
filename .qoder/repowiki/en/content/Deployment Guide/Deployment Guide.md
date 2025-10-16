# Deployment Guide

<cite>
**Referenced Files in This Document**   
- [Dockerfile](file://dockers/Dockerfile)
- [neo4j/Dockerfile](file://dockers/neo4j/Dockerfile)
- [filebeat.yml](file://filebeat.yml)
- [promtail-config.yml](file://promtail-config.yml)
- [alembic.ini](file://alembic.ini)
- [settings_master.py](file://app/settings/settings_master.py)
- [app_config.py](file://app/configs/app_config.py)
- [infrastructure_config.py](file://app/configs/infrastructure_config/infrastructure_config.py)
- [neo4j_config.py](file://app/configs/infrastructure_config/neo4j_config.py)
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)
- [startup.py](file://app/modules/token_monitoring/startup.py)
</cite>

## Table of Contents
1. [Docker Configuration](#docker-configuration)
2. [Environment Setup](#environment-setup)
3. [Deployment Instructions](#deployment-instructions)
4. [Scaling Considerations](#scaling-considerations)
5. [Monitoring and Logging](#monitoring-and-logging)
6. [Database Migration Procedures](#database-migration-procedures)
7. [Health Check Endpoints](#health-check-endpoints)
8. [Rollback Procedures](#rollback-procedures)
9. [Disaster Recovery Planning](#disaster-recovery-planning)

## Docker Configuration

The adv-bot system utilizes Docker for containerization, with separate containers for the main application and Neo4j database. The main application container is built from a Python 3.11-slim base image and includes Poetry for dependency management. The Dockerfile configures logrotate and cron for log management, installs system dependencies, and copies the application code into the container.

The Neo4j database container is based on the official Neo4j image and includes two essential plugins: APOC (Awesome Procedures on Cypher) and Neo4j Graph Data Science. These plugins are copied into the container's plugins directory during the build process with appropriate ownership settings. The container exposes the standard Neo4j ports (7474, 7473, and 7687) for HTTP, HTTPS, and Bolt protocol access.

**Section sources**
- [Dockerfile](file://dockers/Dockerfile)
- [neo4j/Dockerfile](file://dockers/neo4j/Dockerfile)

## Environment Setup

The system requires several environment variables to be configured for proper operation. Database connections are configured through PostgreSQL settings including POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DBNAME. For Redis connectivity, the REDIS_MASTER_HOST and REDIS_REPLICA_HOST variables must be set.

Neo4j configuration is managed through environment variables with the NEO4J_ prefix, including NEO4J_URI, NEO4J_NAME, NEO4J_PASSWORD, and NEO4J_PORT. ClickHouse database settings are specified with CLICK_HOUSE_HOST, CLICK_HOUSE_USER, CLICK_HOUSE_PASSWORD, and CLICKHOUSE_PORT.

Application behavior is controlled by various flags and settings such as POLLING_MODE (determines whether the bot uses polling or webhook mode), TEST_MODE (enables test functionality), and TELEGRAM_WEB_PORT (specifies the port for webhook operations). Additional settings include BIDDER_STEP_RUB (defines bidding increments) and various thread pool sizes for different operations.

**Section sources**
- [settings_master.py](file://app/settings/settings_master.py)
- [app_config.py](file://app/configs/app_config.py)
- [infrastructure_config.py](file://app/configs/infrastructure_config/infrastructure_config.py)
- [neo4j_config.py](file://app/configs/infrastructure_config/neo4j_config.py)
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)

## Deployment Instructions

For production deployment, build the Docker images using the provided Dockerfiles. First, build the Neo4j container: `docker build -f dockers/neo4j/Dockerfile -t adv-bot-neo4j .`. Then build the main application container: `docker build -f dockers/Dockerfile -t adv-bot-app .`.

Deploy the containers using Docker Compose or your preferred orchestration tool. Ensure that the Neo4j container is started first, followed by the application container. The application container should have network access to Neo4j, PostgreSQL, Redis, and ClickHouse databases.

For webhook mode deployment, configure your reverse proxy to route requests to the application container on the port specified by TELEGRAM_WEB_PORT. Set the WEBHOOK_URL and WEBHOOK_PATH environment variables accordingly. For polling mode, ensure that the application container has internet connectivity to receive updates from Telegram.

Initialize the database schema using Alembic migrations after the containers are running. Monitor the application logs during startup to verify successful connection to all required services.

**Section sources**
- [Dockerfile](file://dockers/Dockerfile)
- [neo4j/Dockerfile](file://dockers/neo4j/Dockerfile)
- [alembic.ini](file://alembic.ini)

## Scaling Considerations

The system is designed to handle multiple shops and high request volumes through several scaling mechanisms. The application uses Redis for caching and Celery for task queuing, allowing horizontal scaling of worker processes. Configure multiple Celery workers to distribute the processing load across available CPU cores.

For handling multiple shops, the system uses shop_id to partition data in the database and cache layers. Ensure that your PostgreSQL and Redis instances have sufficient resources to handle the expected number of shops. Consider sharding the PostgreSQL database by shop_id if the number of shops exceeds several hundred.

The application includes configurable thread pools for various operations such as keyword parsing (MAX_THREAD_PARSER) and ClickHouse operations (CH_MAX_THREAD). Adjust these values based on your hardware capabilities and performance requirements. The system also supports read replicas for PostgreSQL through the POSTGRES_REPLICA_HOST setting, allowing read operations to be distributed across multiple database instances.

**Section sources**
- [settings_master.py](file://app/settings/settings_master.py)
- [redis_config.py](file://app/configs/infrastructure_config/redis_config.py)

## Monitoring and Logging

The system includes comprehensive monitoring and logging configuration using Filebeat and Promtail. Filebeat is configured to collect Docker container logs from /var/lib/docker/containers/*/*.log and forward them to an Elasticsearch instance at the specified host and port. The configuration includes authentication credentials for the Elasticsearch server.

Promtail is configured to collect logs and forward them to Loki for aggregation. It listens on port 9080 and scrapes Docker container logs, extracting structured fields such as log level, logger name, and service name through JSON parsing of log entries. The logs are labeled with job=docker for easy filtering in Loki.

Application logging is configured through the LOG_LEVEL environment variable, which controls the verbosity of log output. The system uses Python's standard logging module with structured logging practices. Log rotation is handled by logrotate, which is configured to run every 5 minutes through a cron job in the Docker container.

**Section sources**
- [filebeat.yml](file://filebeat.yml)
- [promtail-config.yml](file://promtail-config.yml)
- [settings_master.py](file://app/settings/settings_master.py)
- [test_logging.py](file://tools/test_logging.py)

## Database Migration Procedures

Database migrations are managed using Alembic, with migration scripts located in the alembic/versions directory. The alembic.ini file configures the migration environment, including the database connection string and script location.

To apply migrations, run `alembic upgrade head` from the application directory. This will execute all pending migrations in sequence. To create a new migration, use `alembic revision --autogenerate -m "description"` which will generate a migration script based on detected changes to the SQLAlchemy models.

The migration history includes numerous revisions that add fields to various models, create indexes for performance optimization, and modify table structures to support new features. Examples include adding shop_id to wbtoken, adding auto-update functionality to advsetting, and creating indexes on frequently queried fields.

Before applying migrations to production, test them thoroughly in a staging environment. Always backup the database before running migrations, and verify the success of each migration by checking the alembic_version table.

**Section sources**
- [alembic.ini](file://alembic.ini)
- [versions/](file://alembic/versions)

## Health Check Endpoints

The system includes several health check mechanisms to monitor service availability and performance. While specific health check endpoints are not explicitly defined in the provided code, the application structure supports health monitoring through several means.

The token monitoring system includes a scheduler that performs daily health checks on API tokens at the configured time (default 9:00 AM). This system monitors token validity and can detect deactivation through HTTP decorator monitoring.

Database connectivity can be verified through the application logs, which will show connection status during startup. Redis connectivity is also logged during initialization. The system's reliance on multiple external services (PostgreSQL, Redis, Neo4j, ClickHouse, and Wildberries API) means that health monitoring should include checks for all these dependencies.

For webhook mode, the application's ability to receive and process Telegram updates serves as a functional health check. In polling mode, regular polling operations indicate system health. Monitoring should also include checking the status of background workers and task queues.

**Section sources**
- [startup.py](file://app/modules/token_monitoring/startup.py)
- [settings_master.py](file://app/settings/settings_master.py)

## Rollback Procedures

Rollback procedures should be carefully planned before deploying new versions or applying database migrations. For application rollbacks, maintain previous Docker images and redeploy the previous version if issues are encountered. Ensure that your orchestration system supports easy rollback to previous container versions.

For database migrations, each Alembic migration should be reversible. Test the downgrade path of each migration in a staging environment before applying to production. If a migration causes issues, use `alembic downgrade <target_revision>` to revert to a previous state.

Before any deployment, backup all databases (PostgreSQL, Neo4j, and ClickHouse) and Redis data. For Neo4j, use the neo4j-admin dump command to create a backup. For PostgreSQL, use pg_dump. For Redis, ensure persistence is configured and consider using BGSAVE before deployments.

The system's modular design allows for rolling updates of individual components. Update components in the following order: application containers, then worker containers, while monitoring system performance and error rates throughout the process.

**Section sources**
- [alembic.ini](file://alembic.ini)
- [Dockerfile](file://dockers/Dockerfile)

## Disaster Recovery Planning

Disaster recovery planning for the adv-bot system should address both data loss and service interruption scenarios. Implement regular automated backups of all data stores with offsite storage. Schedule PostgreSQL backups at least daily, with transaction log archiving for point-in-time recovery.

For Neo4j, configure regular backups using neo4j-admin backup and store them in a secure, geographically separate location. ClickHouse should be configured with replication across multiple nodes if high availability is required.

The system should be deployable in multiple regions or cloud providers to protect against regional outages. Maintain documentation of the complete deployment process, including infrastructure provisioning, container deployment, and configuration steps.

Implement monitoring and alerting for critical system metrics, including database connectivity, worker queue lengths, error rates, and resource utilization. Set up alerts to notify the operations team of any issues that could lead to service disruption.

Regularly test the disaster recovery plan by performing simulated recovery exercises. This includes restoring from backups, failing over to backup systems, and verifying data integrity after recovery operations.

**Section sources**
- [Dockerfile](file://dockers/Dockerfile)
- [neo4j/Dockerfile](file://dockers/neo4j/Dockerfile)
- [alembic.ini](file://alembic.ini)
- [settings_master.py](file://app/settings/settings_master.py)