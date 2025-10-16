# Advertising Updater Module

<cite>
**Referenced Files in This Document**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)
- [wb_adv_api.py](file://app/modules/wb_adv_updater/wb_adv_api.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [models.py](file://app/modules/wb_adv_updater/models.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py)
- [graph_vector_updater.py](file://app/modules/wb_adv_updater/graph_vector_updater.py)
- [ABC_manager.py](file://app/modules/wb_adv_updater/ABC_manager.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Module Architecture](#module-architecture)
3. [Core Components](#core-components)
4. [ML Integration](#ml-integration)
5. [Data Management](#data-management)
6. [API Interface](#api-interface)
7. [Execution Flow](#execution-flow)
8. [Configuration and Scheduling](#configuration-and-scheduling)
9. [Performance Considerations](#performance-considerations)
10. [Error Handling](#error-handling)
11. [Troubleshooting Guide](#troubleshooting-guide)
12. [Conclusion](#conclusion)

## Introduction

The Advertising Updater Module is a sophisticated system designed to synchronize ad campaign data between Wildberries and the internal system using machine learning-driven optimization. This module serves as the central orchestrator for managing ad state transitions, bid adjustments, and intelligent keyword optimization through advanced CTR prediction and bid optimization logic.

The module integrates seamlessly with Wildberries' API ecosystem while leveraging machine learning models to optimize advertising performance. It handles real-time data synchronization, predictive analytics, and automated optimization decisions to maximize ROI for advertising campaigns.

## Module Architecture

The Advertising Updater Module follows a modular architecture with clear separation of concerns:

```mermaid
graph TB
subgraph "Core Orchestrator"
WBManager[WBManager]
Runner[Runner]
end
subgraph "ML Engine"
Predictor[Predictor]
Fitter[Fitter]
DataGetter[DataGetter]
DataSetter[DataSetter]
end
subgraph "Data Layer"
DataManager[DataManager]
MLDataManager[MLDataManager]
GraphUpdater[GraphUpdater]
end
subgraph "API Interface"
WBAdvAPI[WBAdvAPI]
WBApi[WBApi]
end
subgraph "Storage Layer"
Redis[Redis Cache]
ClickHouse[ClickHouse]
Neo4j[Neo4j Graph]
PostgreSQL[PostgreSQL]
end
WBManager --> Predictor
WBManager --> DataSetter
Runner --> WBManager
Predictor --> DataGetter
Fitter --> DataGetter
DataGetter --> Redis
DataGetter --> Neo4j
DataSetter --> WBApi
DataManager --> ClickHouse
MLDataManager --> Redis
GraphUpdater --> Neo4j
WBAdvAPI --> WBApi
WBManager --> Redis
WBManager --> ClickHouse
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L50)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L30)
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L50)

## Core Components

### WBManager - Central Orchestrator

The WBManager class serves as the central orchestrator for the entire advertising updater system. It coordinates all major operations including keyword updates, CTR predictions, and bid optimizations.

```mermaid
classDiagram
class WBManager {
+update_all_keywords_on_wb(client_session) None
+update_predict_ctr() None
+update_all_keyword_data(wb_api, adv_setting, wb_cabinet) None
+common_keyword_stat_update(adv_setting, wb_api) None
+update_clusters_for_adv(adv, wb_api) None
+update_keywords_stat_in_click_house(keyword_stats, adv_id, table_name) None
+MessageCounter message_counter
+update_wb_config_data(client_session) None
+update_wb_config_data_run(client_session) None
}
class MessageCounter {
-datetime _last_time_send
-timedelta _period
+add_send() None
+check_last_time() bool
}
class AdvSetting {
+int adv_id
+string name
+bool bot_active
+list nmids
+float max_cpc
+int min_views_for_ml_predict
}
class KeywordStat {
+string text
+int views
+int clicks
+float spend
+date date
}
WBManager --> MessageCounter : "uses"
WBManager --> AdvSetting : "manages"
WBManager --> KeywordStat : "processes"
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L200-L250)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L350-L400)

Key responsibilities of WBManager include:

- **Keyword Synchronization**: Real-time updates of keyword statistics from Wildberries API
- **CTR Prediction Updates**: Periodic recalculation of click-through rates using ML models
- **Ad State Management**: Monitoring and updating ad campaign statuses
- **Cluster Management**: Managing keyword clustering for optimization
- **Configuration Updates**: Regular updates of minimum CPM data from Wildberries

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L200-L427)

### Data Management Layer

The data management layer handles complex data transformations and storage operations:

```mermaid
sequenceDiagram
participant Client as "Client Session"
participant WBManager as "WBManager"
participant DataManager as "DataManager"
participant ClickHouse as "ClickHouse"
participant Redis as "Redis Cache"
Client->>WBManager : update_all_keywords_on_wb()
WBManager->>DataManager : get_keywords_statistic_clickhouse()
DataManager->>ClickHouse : query keyword statistics
ClickHouse-->>DataManager : raw statistics data
DataManager->>Redis : set_predict_ctrs()
Redis-->>DataManager : CTR predictions
DataManager-->>WBManager : processed keywords
WBManager->>WBManager : update_clusters_for_adv()
WBManager-->>Client : completion signal
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L250-L350)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L100-L200)

**Section sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L100)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L250-L350)

## ML Integration

### Predictor Class

The Predictor class is the heart of the ML integration, responsible for CTR prediction and bid optimization:

```mermaid
classDiagram
class Predictor {
+_predict(df) DataFrame
+predict_ctr_for_keywords() None
+_get_df_for_predict(adv_settings) DataFrame
+get_nmid_to_item_features(nmids) dict
+get_keyword_features(clear_keywords) list
-__update_predict_ctr(redis_pipeline, keyword_setting, predict_df) None
}
class Fitter {
+fill_average_vector(df_stat, df_vectors) DataFrame
+__get_average_vector(nmids, df_vectors) ndarray
}
class DataGetter {
+get_item_features_from_redis(nmids_batch) list
+get_keyword_features_from_redis(keywords) list
+normalize_df_data(df, param_for_norm) DataFrame
}
class AdvSetting {
+int adv_id
+string type
+list nmids
+float exponent_predict_ctr
}
Predictor --> Fitter : "uses"
Predictor --> DataGetter : "uses"
Predictor --> AdvSetting : "processes"
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L50-L150)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py#L1-L50)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L1-L50)

### ML Training and Model Management

The ML system includes sophisticated training and model management capabilities:

```mermaid
flowchart TD
Start([Training Start]) --> GetDF["Get Training Data<br/>from ClickHouse"]
GetDF --> ProcessFeatures["Process Item & Keyword Features"]
ProcessFeatures --> BayesianApply["Apply Bayesian Statistics<br/>for CTR Calculation"]
BayesianApply --> TrainModel["Train XGBoost Model"]
TrainModel --> SaveModel["Save Model to Disk"]
SaveModel --> UpdatePredictions["Update Predictions in Redis"]
UpdatePredictions --> End([Training Complete])
TrainModel --> ValidateModel{"Model Validation"}
ValidateModel --> |Pass| SaveModel
ValidateModel --> |Fail| Retry["Retry Training"]
Retry --> GetDF
```

**Diagram sources**
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py#L20-L100)
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L80-L150)

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L254)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py#L1-L100)

## Data Management

### Data Transformation Pipeline

The module implements a sophisticated data transformation pipeline that converts between internal models and external API formats:

```mermaid
flowchart LR
subgraph "External Data"
WBApi[Wildberries API]
APIResponse[API Response]
end
subgraph "Internal Processing"
RawData[Raw Data]
DataValidation[Data Validation]
FeatureExtraction[Feature Extraction]
Normalization[Normalization]
end
subgraph "Storage"
ClickHouse[ClickHouse]
Redis[Redis Cache]
Neo4j[Neo4j Graph]
end
WBApi --> APIResponse
APIResponse --> RawData
RawData --> DataValidation
DataValidation --> FeatureExtraction
FeatureExtraction --> Normalization
Normalization --> ClickHouse
Normalization --> Redis
Normalization --> Neo4j
```

**Diagram sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L50-L150)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L50-L150)

### Vector Management

The system manages various types of vector representations for optimization:

```mermaid
classDiagram
class ItemFeature {
+int id
+int nmid
+JSONB vector
}
class KeywordFeature {
+int id
+string keyword
+JSONB vector
}
class GraphUpdater {
+update_graph_run(length) None
+_update_nmids_vectors() None
+_update_keywords_vectors() None
-_gds DataScience
-_data_getter DataGetter
}
class Word2VecObject {
+average_vector_from_sentence(sentence) list
}
GraphUpdater --> ItemFeature : "updates"
GraphUpdater --> KeywordFeature : "updates"
GraphUpdater --> Word2VecObject : "uses"
```

**Diagram sources**
- [graph_vector_updater.py](file://app/modules/wb_adv_updater/graph_vector_updater.py#L1-L50)
- [models.py](file://app/modules/wb_adv_updater/models.py#L1-L30)

**Section sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L100-L300)
- [graph_vector_updater.py](file://app/modules/wb_adv_updater/graph_vector_updater.py#L1-L128)

## API Interface

### WBAdvAPI Implementation

The WBAdvAPI class provides a clean interface to Wildberries' advertising APIs:

```mermaid
classDiagram
class WBAdvAPI {
<<interface>>
}
class BaseAPI {
+session ClientSession
+headers Headers
+requests(session, method, url, data) str
}
class AdvMixin {
+PREFIX string
+get_min_cpm_adv_data() MinCPMData
+get_advertIds() list[int]
+create_auto_adv(name, subject_id, balance_type, start_status) int
+start_adv(adv_id) None
+check_balance(adv_id) dict
}
class WBApi {
+advert AdvMixin
+wb_access WBCabinetAccess
+client_session ClientSession
}
WBAdvAPI --|> BaseAPI : "extends"
WBAdvAPI --|> AdvMixin : "extends"
WBApi --> WBAdvAPI : "uses"
```

**Diagram sources**
- [wb_adv_api.py](file://app/modules/wb_adv_updater/wb_adv_api.py#L1-L6)
- [app/core/wb_api/base.py](file://app/core/wb_api/base.py)
- [app/core/wb_api/mixins/adv.py](file://app/core/wb_api/mixins/adv.py)

**Section sources**
- [wb_adv_api.py](file://app/modules/wb_adv_updater/wb_adv_api.py#L1-L6)

## Execution Flow

### Main Runner Coroutines

The runner module orchestrates all asynchronous operations:

```mermaid
sequenceDiagram
participant MainLoop as "Main Loop"
participant PaymentWorker as "Payment Worker"
participant TokenChecker as "Token Checker"
participant VectorUpdater as "Vector Updater"
participant ModelTrainer as "Model Trainer"
loop Every 24 Hours
MainLoop->>PaymentWorker : process_payment_for_advs()
PaymentWorker->>PaymentWorker : Calculate daily payments
PaymentWorker-->>MainLoop : Payment processed
end
loop Daily at 9 : 00 AM
MainLoop->>TokenChecker : process_token_expiration_check()
TokenChecker->>TokenChecker : Check token expirations
TokenChecker-->>MainLoop : Tokens checked
end
loop Continuous
MainLoop->>VectorUpdater : run_update_vectors_in_redis()
VectorUpdater->>VectorUpdater : Update Redis vectors
VectorUpdater-->>MainLoop : Vectors updated
MainLoop->>VectorUpdater : run_vector_update_in_neo4j()
VectorUpdater->>VectorUpdater : Update Neo4j vectors
VectorUpdater-->>MainLoop : Graph updated
end
loop Hourly
MainLoop->>ModelTrainer : run_update_model()
ModelTrainer->>ModelTrainer : Train new model
ModelTrainer-->>MainLoop : Model trained
end
```

**Diagram sources**
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L50-L144)

### Keyword Update Workflow

```mermaid
flowchart TD
Start([Start Keyword Update]) --> GetAdvSettings["Get Active AdvSettings"]
GetAdvSettings --> CreateTasks["Create Async Tasks"]
CreateTasks --> ProcessTask["Process Individual Task"]
ProcessTask --> GetKeywordStats["Get Keyword Stats from WB"]
GetKeywordStats --> UpdateClickHouse["Update ClickHouse"]
UpdateClickHouse --> GetGoodBadPhrases["Get Good/Bad Phrases"]
GetGoodBadPhrases --> UpdateMinusKeywords["Update Minus Keywords"]
UpdateMinusKeywords --> UpdateClusters["Update Clusters"]
UpdateClusters --> SetAdvState["Set Advert State"]
SetAdvState --> Complete([Task Complete])
ProcessTask --> HandleError{"Error Occurred?"}
HandleError --> |Yes| LogError["Log Error"]
HandleError --> |No| GetKeywordStats
LogError --> Complete
```

**Diagram sources**
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L20-L50)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L250-L350)

**Section sources**
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L144)

## Configuration and Scheduling

### Update Intervals and Timing

The module implements sophisticated scheduling patterns for different operations:

- **Keyword Updates**: Every 5 seconds for continuous monitoring
- **CTR Predictions**: Hourly updates with semaphore control (max 10 concurrent)
- **Model Training**: Hourly training with automatic retry mechanisms
- **Vector Updates**: Continuous updates with Neo4j job coordination
- **Token Checks**: Daily at 9:00 AM
- **Payments**: Daily at 3:00 AM

### Configuration Options

The system supports extensive configuration options:

```python
# ML Model Selection
ML_MODEL_PATH = "app/keyword_async_ml_updater/data/model.ml"

# Update Intervals
KEYWORD_UPDATE_INTERVAL = 5  # seconds
CTR_PREDICT_INTERVAL = 3600  # seconds
MODEL_TRAIN_INTERVAL = 3600  # seconds

# Performance Settings
MAX_CONCURRENT_UPDATES = 10
VECTOR_UPDATE_BATCH_SIZE = 100

# Caching Strategies
REDIS_CACHE_TTL = 3600  # seconds
CLICKHOUSE_CACHE_TTL = 86400  # seconds
```

**Section sources**
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L30-L80)
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L20-L30)

## Performance Considerations

### High-Frequency Bidding Operations

The module is designed to handle high-frequency bidding operations efficiently:

```mermaid
flowchart TD
subgraph "Performance Optimization"
Semaphore[Asyncio Semaphore<br/>Max 10 Concurrent]
BatchInsert[Batch Insert Operations<br/>100 Records per Batch]
ParallelProcessing[Parallel Keyword Processing<br/>Multiple AdvSettings]
CachingLayer[Caching Layer<br/>Redis + ClickHouse]
end
subgraph "Memory Management"
MemoryPool[Memory Pool<br/>Pre-allocated Buffers]
GarbageCollection[Garbage Collection<br/>Automatic Cleanup]
StreamProcessing[Stream Processing<br/>Chunked Data Loading]
end
subgraph "Network Optimization"
ConnectionPooling[Connection Pooling<br/>HTTP Sessions]
RetryMechanism[Retry Mechanism<br/>Exponential Backoff]
TimeoutManagement[Timeout Management<br/>Configurable Timeouts]
end
Semaphore --> ParallelProcessing
BatchInsert --> CachingLayer
ParallelProcessing --> MemoryPool
MemoryPool --> StreamProcessing
ConnectionPooling --> RetryMechanism
RetryMechanism --> TimeoutManagement
```

### Caching Strategies

The system implements multi-layer caching for optimal performance:

1. **Redis Cache**: Hot data caching with TTL management
2. **ClickHouse Cache**: Historical data aggregation
3. **Neo4j Cache**: Graph data for vector operations
4. **Memory Cache**: In-memory caching for frequently accessed data

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L20-L30)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L100-L150)

## Error Handling

### Distributed Update Error Handling

The module implements comprehensive error handling for distributed updates:

```mermaid
flowchart TD
ErrorOccurred[Error Occurred] --> ClassifyError{Classify Error Type}
ClassifyError --> |Network Error| NetworkRetry[Network Retry<br/>Exponential Backoff]
ClassifyError --> |API Error| APIMaxRetry[API Max Retries<br/>Default: 3]
ClassifyError --> |Data Error| DataValidation[Data Validation<br/>Fallback Values]
ClassifyError --> |System Error| SystemRestart[System Restart<br/>Graceful Shutdown]
NetworkRetry --> CheckRetryCount{Retry Count < Max?}
CheckRetryCount --> |Yes| WaitBackoff[Wait Exponential Backoff]
CheckRetryCount --> |No| LogFailure[Log Failure]
APIMaxRetry --> CheckAPICount{API Count < Max?}
CheckAPICount --> |Yes| WaitAPI[Wait API Rate Limit]
CheckAPICount --> |No| LogAPIError[Log API Error]
DataValidation --> UseDefaults[Use Default Values]
SystemRestart --> GracefulShutdown[Graceful Shutdown]
WaitBackoff --> RetryOperation[Retry Operation]
WaitAPI --> RetryOperation
UseDefaults --> ContinueProcessing[Continue Processing]
LogFailure --> ContinueProcessing
LogAPIError --> ContinueProcessing
GracefulShutdown --> RestartSystem[Restart System]
RetryOperation --> Success[Operation Successful]
ContinueProcessing --> Success
RestartSystem --> Success
```

### Error Recovery Patterns

The system implements several error recovery patterns:

1. **Circuit Breaker Pattern**: Prevents cascading failures
2. **Bulkhead Pattern**: Isolates failures between different components
3. **Retry with Backoff**: Intelligent retry mechanisms
4. **Fallback Mechanisms**: Graceful degradation when primary systems fail

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L300-L400)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L100-L144)

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. ML Model Training Failures

**Symptoms**: Model training fails with memory errors or convergence issues.

**Solutions**:
- Check available memory and adjust batch sizes
- Verify data quality and remove outliers
- Adjust learning rate parameters
- Monitor training progress with logging

#### 2. API Rate Limiting

**Symptoms**: Frequent API timeout errors and rate limiting responses.

**Solutions**:
- Implement exponential backoff retry mechanism
- Increase wait times between API calls
- Use connection pooling for HTTP sessions
- Monitor API usage metrics

#### 3. Redis Connection Issues

**Symptoms**: Redis connection timeouts and data inconsistency.

**Solutions**:
- Verify Redis server health and connectivity
- Implement connection retry mechanisms
- Use Redis sentinel for high availability
- Monitor Redis memory usage

#### 4. ClickHouse Performance Issues

**Symptoms**: Slow queries and high resource consumption.

**Solutions**:
- Optimize query patterns and indexing
- Implement data partitioning strategies
- Use materialized views for complex aggregations
- Monitor query execution plans

### Diagnostic Tools

The module includes several diagnostic tools:

```python
# Enable debug logging
logger.setLevel(logging.DEBUG)

# Monitor system health
async def monitor_system_health():
    # Check Redis connectivity
    # Verify API endpoints
    # Monitor memory usage
    # Track error rates
    pass

# Performance profiling
async def profile_operations():
    # Profile keyword update operations
    # Measure ML prediction times
    # Analyze data transfer rates
    pass
```

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L350-L427)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L120-L144)

## Conclusion

The Advertising Updater Module represents a sophisticated system for managing Wildberries advertising campaigns with machine learning-driven optimization. Its modular architecture, comprehensive error handling, and performance optimizations make it suitable for high-volume, mission-critical advertising operations.

Key strengths of the module include:

- **Scalable Architecture**: Modular design allows for easy extension and maintenance
- **Machine Learning Integration**: Advanced CTR prediction and bid optimization
- **High Availability**: Robust error handling and recovery mechanisms
- **Performance Optimization**: Multi-layer caching and efficient data processing
- **Real-time Capabilities**: Continuous monitoring and updates

The module continues to evolve with new features and optimizations, maintaining its position as a critical component in the advertising automation ecosystem.