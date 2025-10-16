# WB Adv Updater

<cite>
**Referenced Files in This Document**   
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr.py](file://app/core/redis_manager_v2/mixins/predict_ctr.py)
- [models.py](file://app/modules/wb_adv_updater/models.py)
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
The WB Adv Updater module is a sophisticated advertising optimization system that integrates machine learning to enhance ad performance on the Wildberries platform. This document provides a comprehensive analysis of the module's architecture, functionality, and implementation details, focusing on its predictive analytics capabilities and automated adjustment mechanisms. The system leverages ML models to predict click-through rates (CTR) and optimize bidding strategies, enabling data-driven decisions for advertising campaigns.

## Project Structure
The WB Adv Updater module is organized within the application's modular structure, with dedicated components for machine learning, data management, and integration with external services. The module follows a clean separation of concerns, with distinct components handling data retrieval, model training, prediction, and ad updates.

```mermaid
graph TB
subgraph "WB Adv Updater Module"
ML[ML.py]
DataManager[data_manager.py]
Fitter[fitter.py]
DataGetter[data_getter.py]
DataSetter[data_setter.py]
Runner[runner.py]
Models[models.py]
ABC[ABC_manager.py]
Utils[ml_common_funcs.py]
end
subgraph "GRPC Services"
PredictClient[predict_ctr_client.py]
PredictProto[predict_ctr_service.proto]
end
subgraph "Redis Integration"
PredictCTR[predict_ctr.py]
BaseRedis[BaseRedisManager]
end
ML --> DataManager
ML --> Fitter
ML --> DataGetter
DataSetter --> DataManager
Fitter --> DataGetter
Fitter --> DataManager
Runner --> ML
DataGetter --> PredictClient
PredictClient --> PredictProto
ML --> PredictCTR
DataSetter --> PredictCTR
style ML fill:#f9f,stroke:#333
style DataManager fill:#f9f,stroke:#333
style Fitter fill:#f9f,stroke:#333
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr.py](file://app/core/redis_manager_v2/mixins/predict_ctr.py)

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

## Core Components

The WB Adv Updater module consists of several core components that work together to optimize advertising performance through machine learning. The system integrates with Wildberries' API to retrieve advertising data, applies ML models to predict CTR, and automatically adjusts bidding strategies based on these predictions. The architecture follows a pipeline approach, with data flowing from external sources through preprocessing, model inference, and finally to ad updates.

The ML component (ML.py) serves as the central orchestrator, coordinating data retrieval, model prediction, and result storage. It works in conjunction with the fitter module for model training and the data manager for handling advertising statistics. The GRPC prediction service enables integration with external ML models, allowing for scalable and efficient CTR prediction.

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

## Architecture Overview

The WB Adv Updater follows a microservices-inspired architecture with clear separation between data processing, machine learning, and ad management components. The system is designed to be asynchronous and non-blocking, leveraging Python's asyncio framework for efficient resource utilization.

```mermaid
graph LR
A[Wildberries API] --> B[Data Getter]
B --> C[ClickHouse Database]
C --> D[Data Manager]
D --> E[Fitter]
E --> F[ML Model Training]
F --> G[Model Storage]
G --> H[ML Predictor]
H --> I[GRPC Service]
I --> J[Redis Cache]
J --> K[Data Setter]
K --> L[Wildberries API Updates]
M[Configuration] --> D
M --> E
M --> H
N[Scheduler] --> H
N --> K
style A fill:#ccf,stroke:#333
style B fill:#cfc,stroke:#333
style C fill:#cfc,stroke:#333
style D fill:#cfc,stroke:#333
style E fill:#cfc,stroke:#333
style F fill:#cfc,stroke:#333
style G fill:#cfc,stroke:#333
style H fill:#cfc,stroke:#333
style I fill:#cfc,stroke:#333
style J fill:#cfc,stroke:#333
style K fill:#cfc,stroke:#333
style L fill:#ccf,stroke:#333
```

**Diagram sources**
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr.py](file://app/core/redis_manager_v2/mixins/predict_ctr.py)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py)

## Detailed Component Analysis

### ML Component Analysis
The ML component is the central processing unit of the WB Adv Updater, responsible for coordinating CTR prediction and model management. It implements a comprehensive pipeline for feature extraction, model inference, and result storage.

#### ML Class Diagram
```mermaid
classDiagram
class Predictor {
+_predict(df) DataFrame
+predict_ctr_for_keywords() void
+_get_df_for_predict(adv_settings) DataFrame
+get_nmid_to_item_features(nmids) dict
+get_keyword_features(clear_keywords) dict
+__update_predict_ctr(redis_pipeline, keyword_setting, predict_df) void
}
class Fitter {
+__get_average_vector(nmids, df_vectors) array
+fill_average_vector(df_stat, df_vectors) DataFrame
}
class DataGetter {
+normalize_df_data(df, param_for_norm) DataFrame
+get_nmid_offer_id_df(cards) DataFrame
+get_list_progress(jobid) dict
+get_item_features_from_neo(nmids_batch) dict
+get_item_features_from_redis(nmids_batch) dict
+get_keyword_features_from_neo(keywords) dict
+get_keyword_features_from_redis(keywords) list
}
class DataSetter {
+__init__(wb_api) void
+_update_minus_keywords_in_adv(adv_setting, keywords) void
+update_minus_keywords_in_adv(adv_setting, wb_cabinet, keywords) void
+update_minus_keywords(adv_settings) void
}
Predictor --> DataGetter : "uses"
Predictor --> Fitter : "uses"
DataSetter --> DataManager : "uses"
DataSetter --> SearchAdvsManager : "uses"
Fitter --> DataGetter : "uses"
Fitter --> DataManager : "uses"
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

#### CTR Prediction Workflow
```mermaid
sequenceDiagram
participant Scheduler as "Scheduler"
participant ML as "ML Predictor"
participant DataGetter as "Data Getter"
participant Redis as "Redis Cache"
participant GRPC as "GRPC Service"
participant DataSetter as "Data Setter"
participant Wildberries as "Wildberries API"
Scheduler->>ML : run_update_predict_ctr()
ML->>DataGetter : get_adv_settings()
DataGetter->>Wildberries : fetch campaign data
Wildberries-->>DataGetter : campaign data
DataGetter->>DataGetter : extract nmids and keywords
DataGetter->>Redis : get_item_features(nmids)
Redis-->>DataGetter : item vectors
DataGetter->>Redis : get_keyword_features(keywords)
Redis-->>DataGetter : keyword vectors
DataGetter->>ML : return feature data
ML->>GRPC : PredictCtrRequest(nmids, phrases)
GRPC-->>ML : PredictCtrResponse(predictions)
ML->>Redis : set_predict_ctr_with_pipeline()
Redis-->>ML : confirmation
ML->>DataSetter : update_ad_settings()
DataSetter->>Wildberries : update_minus_phrases()
Wildberries-->>DataSetter : update confirmation
DataSetter-->>ML : operation result
ML-->>Scheduler : process complete
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr.py](file://app/core/redis_manager_v2/mixins/predict_ctr.py)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py)

### GRPC Prediction Service Integration
The GRPC prediction service provides a scalable interface for CTR prediction, enabling the system to leverage external ML models without tight coupling.

#### GRPC Service Flowchart
```mermaid
flowchart TD
Start([Start Prediction]) --> ValidateInput["Validate nmids and phrases"]
ValidateInput --> InputValid{"Input Valid?"}
InputValid --> |No| ReturnError["Return Error Response"]
InputValid --> |Yes| ConnectGRPC["Connect to GRPC Service"]
ConnectGRPC --> CreateRequest["Create PredictCtrRequest"]
CreateRequest --> SendRequest["Send Request to PredictCtr"]
SendRequest --> ReceiveResponse["Receive PredictCtrResponse"]
ReceiveResponse --> CheckResponse{"Response Valid?"}
CheckResponse --> |No| HandleError["Handle GRPC Error"]
CheckResponse --> |Yes| ProcessPredictions["Process Predictions Dictionary"]
ProcessPredictions --> StoreResults["Store in Redis Cache"]
StoreResults --> UpdateAds["Update Ad Settings"]
UpdateAds --> End([Prediction Complete])
HandleError --> ReturnError
ReturnError --> End
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr.py](file://app/core/redis_manager_v2/mixins/predict_ctr.py)

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)

## Dependency Analysis

The WB Adv Updater module has a well-defined dependency structure, with clear relationships between components. The system relies on several external services and databases to function effectively.

```mermaid
graph TD
A[WB Adv Updater] --> B[Wildberries API]
A --> C[ClickHouse Database]
A --> D[Redis Cache]
A --> E[GRPC Prediction Service]
A --> F[PostgreSQL Database]
B --> G[Wildberries Platform]
C --> H[Analytics Data]
D --> I[Feature Vectors]
D --> J[Prediction Results]
E --> K[ML Models]
F --> L[Configuration Data]
A --> M[Scheduler]
M --> N[Cron Jobs]
style A fill:#f9f,stroke:#333
style B fill:#ccf,stroke:#333
style C fill:#ccf,stroke:#333
style D fill:#ccf,stroke:#333
style E fill:#ccf,stroke:#333
style F fill:#ccf,stroke:#333
style M fill:#ccf,stroke:#333
```

**Diagram sources**
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr.py](file://app/core/redis_manager_v2/mixins/predict_ctr.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)

**Section sources**
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

## Performance Considerations

The WB Adv Updater is designed with performance in mind, implementing several optimization strategies to handle large volumes of advertising data efficiently. The system uses asynchronous processing to maximize throughput and minimize latency in the prediction pipeline.

Key performance optimizations include:
- Asynchronous I/O operations for database and API calls
- Batch processing of feature vectors and predictions
- Redis caching of frequently accessed data
- Parallel execution of independent tasks
- Efficient data structures for feature representation

The system also implements rate limiting and error handling to ensure stability under high load conditions. Configuration options allow for tuning of performance parameters based on specific deployment requirements.

## Troubleshooting Guide

Common issues with the WB Adv Updater typically fall into several categories: model drift, prediction accuracy degradation, and API integration problems.

### Model Drift and Accuracy Issues
- **Symptoms**: Decreasing prediction accuracy over time, CTR predictions diverging from actual performance
- **Causes**: Changes in market conditions, shifts in user behavior, outdated training data
- **Solutions**: Regular model retraining, monitoring prediction vs. actual performance, implementing model versioning

### API Integration Problems
- **Symptoms**: Failed updates, timeout errors, authentication issues
- **Causes**: Rate limiting, network connectivity issues, API changes
- **Solutions**: Implement retry logic with exponential backoff, monitor API status, maintain up-to-date API clients

### Configuration Issues
- **Symptoms**: Unexpected behavior, incorrect predictions, failed updates
- **Causes**: Incorrect parameter settings, missing configuration values
- **Solutions**: Validate configuration on startup, implement configuration validation, provide clear error messages

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)

## Conclusion

The WB Adv Updater module represents a sophisticated integration of machine learning and advertising optimization, providing automated CTR prediction and bid adjustment capabilities for Wildberries advertising campaigns. The system's modular architecture enables flexible configuration and maintenance, while its use of GRPC services allows for scalable ML inference.

Key strengths of the implementation include its comprehensive data pipeline, robust error handling, and efficient use of caching to minimize latency. The system effectively bridges the gap between raw advertising data and actionable insights, enabling data-driven optimization of ad performance.

Future enhancements could include more sophisticated ML models, real-time adaptation to market changes, and enhanced visualization of performance metrics to support strategic decision-making.