# Machine Learning Integration

<cite>
**Referenced Files in This Document**   
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [ml_common_funcs.py](file://app/modules/wb_adv_updater/ml_common_funcs.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)
- [models.py](file://app/modules/wb_adv_updater/models.py)
- [requirements.txt](file://requirements.txt)
- [run_update_predict_ctr.py](file://run_update_predict_ctr.py)
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
The Machine Learning Integration in the adv-bot system provides a comprehensive solution for predicting Click-Through Rate (CTR) in advertising campaigns. This documentation details the CTR prediction model architecture, feature engineering process, model training pipeline, and deployment strategy. The system leverages historical campaign data processed through ml_data_manager.py to generate training features and employs the ML model in app/modules/wb_adv_updater/ML.py for real-time predictions. The integration between machine learning components and bidding logic is critical for optimizing advertising performance, with data flowing from ClickHouse analytics to model inference. The system utilizes key machine learning libraries including tensorflow, xgboost, and gensim as specified in requirements.txt.

## Project Structure

```mermaid
graph TD
subgraph "ML Core Components"
ML[ML.py]
DataManager[ml_data_manager.py]
Fitter[fitter.py]
DataGetter[data_getter.py]
CommonFuncs[ml_common_funcs.py]
end
subgraph "Supporting Components"
Runner[runner.py]
Models[models.py]
Word2Vec[word_to_vec_object.py]
GDS[gds_object.py]
end
subgraph "External Dependencies"
Redis[Redis]
Neo4j[Neo4j]
ClickHouse[ClickHouse]
PostgreSQL[PostgreSQL]
end
ML --> DataManager
ML --> DataGetter
ML --> CommonFuncs
Fitter --> DataManager
Fitter --> DataGetter
DataManager --> Word2Vec
DataManager --> GDS
Runner --> ML
Runner --> DataManager
Runner --> Fitter
ML --> Redis
ML --> Neo4j
Fitter --> ClickHouse
DataManager --> PostgreSQL
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)

**Section sources**
- [app/modules/wb_adv_updater](file://app/modules/wb_adv_updater)

## Core Components

The core components of the ML integration include the Predictor class in ML.py which handles real-time CTR predictions, the fitter.py module responsible for model training, and the data_getter.py component that manages feature retrieval from various data sources. The ml_data_manager.py orchestrates the overall ML workflow, coordinating data updates, model training, and prediction processes. The system uses a global model instance stored in memory for efficient inference, with model persistence handled through joblib serialization to disk. Feature vectors for both keywords and product items are stored in Redis for low-latency access during prediction.

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py#L1-L282)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L1-L54)

## Architecture Overview

```mermaid
graph TD
subgraph "Data Sources"
ClickHouse[ClickHouse Analytics]
PostgreSQL[PostgreSQL Database]
Neo4j[Neo4j Graph Database]
Redis[Redis Cache]
end
subgraph "Feature Engineering"
ProductFeatures[Product Feature Extraction]
KeywordFeatures[Keyword Feature Extraction]
ImageFeatures[Image Feature Extraction]
end
subgraph "Model Training"
TrainingData[Training Data Assembly]
GradientBoosting[XGBoost Model Training]
CrossValidation[Cross-Validation]
ModelPersistence[Model Saving]
end
subgraph "Real-time Prediction"
FeatureRetrieval[Feature Retrieval]
Prediction[CTR Prediction]
ResultCaching[Result Caching]
end
subgraph "Integration Points"
BiddingLogic[Bidding Logic]
CampaignManagement[Campaign Management]
end
ClickHouse --> TrainingData
PostgreSQL --> ProductFeatures
Neo4j --> KeywordFeatures
Redis --> ImageFeatures
ProductFeatures --> TrainingData
KeywordFeatures --> TrainingData
ImageFeatures --> TrainingData
TrainingData --> GradientBoosting
GradientBoosting --> CrossValidation
CrossValidation --> ModelPersistence
ModelPersistence --> Prediction
FeatureRetrieval --> Prediction
Prediction --> ResultCaching
ResultCaching --> BiddingLogic
ResultCaching --> CampaignManagement
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)

## Detailed Component Analysis

### CTR Prediction Model Architecture

```mermaid
classDiagram
class Predictor {
+global_model : XGBModel
+update_predict_ctr_process_semaphore : Semaphore
+data_getter : DataGetter
-_predict(df : DataFrame) : DataFrame
+predict_ctr_for_keywords() : None
+_get_df_for_predict(adv_settings : list[AdvSetting]) : DataFrame
+get_nmid_to_item_features(nmids : list) : dict
+get_keyword_features(keywords : list) : dict
+__update_predict_ctr(redis_pipeline : Pipeline, keyword_setting : KeywordSetting, predict_df : DataFrame) : None
}
class Fitter {
-__get_average_vector(nmids : str, df_vectors : DataFrame) : array
+fill_average_vector(df_stat : DataFrame, df_vectors : DataFrame) : DataFrame
}
class DataGetter {
-_gds : DataScience
+normalize_df_data(df : DataFrame, param_for_norm : str) : DataFrame
+get_nmid_offer_id_df(cards : list[CardFromWB]) : DataFrame
+get_list_progress(jobid) : dict
+get_item_features_from_neo(nmids_batch) : list
+get_item_features_from_redis(nmids_batch) : list
+get_keyword_features_from_neo(keywords) : list
+get_keyword_features_from_redis(keywords) : list
}
class MLCommonFuncs {
+data_getter : DataGetter
+path : str
+model_lock : Lock
+save_model(model : XGBModel, time_stamp : str) : None
+load_model() : XGBModel
+get_keyword_features(keywords) : dict
}
Predictor --> DataGetter : "uses"
Predictor --> MLCommonFuncs : "uses"
Fitter --> DataGetter : "uses"
MLCommonFuncs --> DataGetter : "uses"
Predictor --> Fitter : "collaborates with"
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L1-L54)
- [ml_common_funcs.py](file://app/modules/wb_adv_updater/ml_common_funcs.py#L1-L53)

### Feature Engineering Process

```mermaid
flowchart TD
Start([Feature Engineering Process]) --> ProductData["Extract Product Data from DB"]
ProductData --> CharacteristicProcessing["Process Product Characteristics"]
CharacteristicProcessing --> TextCleaning["Clean Text: Lowercase, Remove Special Chars"]
TextCleaning --> WordSplitting["Split Text into Words"]
WordSplitting --> Word2Vec["Apply Word2Vec to Generate Word Vectors"]
Word2Vec --> AverageVectors["Average Vectors for Each Characteristic"]
AverageVectors --> ProductFeatures["Create Product Feature Dictionary"]
ProductData --> ImageProcessing["Process Product Images"]
ImageProcessing --> ImageDownload["Download Main Product Image"]
ImageDownload --> ImageVector["Generate Image Vector via ImageMaster"]
ImageVector --> ImageHash["Calculate Image DHash"]
ImageHash --> ImageFeatures["Store Image Features"]
ProductFeatures --> CombineFeatures["Combine All Product Features"]
ImageFeatures --> CombineFeatures
CombineFeatures --> StoreNeo4j["Store Features in Neo4j Graph Database"]
StoreNeo4j --> StoreRedis["Store Vectors in Redis Cache"]
StoreRedis --> End([Feature Engineering Complete])
style Start fill:#f9f,stroke:#333
style End fill:#f9f,stroke:#333
```

**Diagram sources**
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L1-L295)
- [word_to_vec_object.py](file://app/modules/wb_adv_updater/word_to_vec_object.py)
- [gds_object.py](file://app/modules/wb_adv_updater/gds_object.py)
- [image_master2.py](file://app/utils/image_master/image_master2.py)

### Model Training Pipeline

```mermaid
sequenceDiagram
participant Runner as "runner.py"
participant Fitter as "fitter.py"
participant DataManager as "ml_data_manager.py"
participant DataGetter as "data_getter.py"
participant ClickHouse as "ClickHouse"
participant Redis as "Redis"
participant Neo4j as "Neo4j"
participant ModelStorage as "Model Storage"
Runner->>Fitter : getGradientBoostingFullFitModel()
Fitter->>Fitter : _fit_modelGradientBoosting()
Fitter->>Fitter : _get_df_for_fit()
Fitter->>DataManager : Query Active AdvSettings
DataManager-->>Fitter : List of AdvSettings
loop For each AdvSetting
Fitter->>DataGetter : get_nmid_to_item_features(nmids)
DataGetter->>Neo4j : get_nmid_vectors(nmids_batch)
Neo4j-->>DataGetter : Item Feature Vectors
DataGetter-->>Fitter : Item Features
Fitter->>DataManager : get_keywords_statistic_clickhouse(adv)
DataManager->>ClickHouse : Query Keyword Statistics
ClickHouse-->>DataManager : Keyword Stats (views, clicks, spend)
DataManager-->>Fitter : Keyword Statistics
Fitter->>DataGetter : get_keyword_features_from_redis(keywords)
DataGetter->>Redis : Get Keyword Vectors
Redis-->>DataGetter : Keyword Feature Vectors
DataGetter-->>Fitter : Keyword Features
Fitter->>Fitter : Assemble Training Data Row
end
Fitter->>Fitter : Prepare X (features) and y (CTR)
Fitter->>Fitter : Cross-Validation (if enabled)
Fitter->>Fitter : Train XGBoost Model
Fitter->>ModelStorage : save_model(model)
ModelStorage-->>Fitter : Model Saved
Fitter-->>Runner : Model Training Complete
```

**Diagram sources**
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py#L1-L282)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L1-L295)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L1-L54)
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)

### Deployment Strategy and Integration

```mermaid
flowchart LR
subgraph "Scheduling"
Cron[Cron Job]
RunScript[run_update_predict_ctr.py]
end
subgraph "Execution"
Runner[runner.py]
WbManager[wb_manager.py]
MLComponent[ML.py]
end
subgraph "Data Flow"
RedisCache[Redis Cache]
PredictionResults[Prediction Results]
BiddingSystem[Bidding Logic]
end
Cron --> RunScript
RunScript --> Runner
Runner --> WbManager
WbManager --> MLComponent
MLComponent --> RedisCache
MLComponent --> PredictionResults
PredictionResults --> BiddingSystem
style Cron fill:#ffcccc,stroke:#333
style RunScript fill:#ccffcc,stroke:#333
style Runner fill:#ccccff,stroke:#333
style WbManager fill:#ffffcc,stroke:#333
style MLComponent fill:#ffccff,stroke:#333
style RedisCache fill:#cfffff,stroke:#333
style PredictionResults fill:#cfffcc,stroke:#333
style BiddingSystem fill:#cfcfff,stroke:#333
```

**Diagram sources**
- [run_update_predict_ctr.py](file://run_update_predict_ctr.py#L1-L9)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L96)
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)

## Dependency Analysis

```mermaid
graph TD
ML[ML.py] --> data_getter[data_getter.py]
ML --> ml_common_funcs[ml_common_funcs.py]
ML --> fitter[fitter.py]
ML --> ABC_manager[ABC_manager.py]
ML --> BaseRedis[BaseRedis]
ML --> redis_manager[redis_manager]
ML --> text_cleaner[text_cleaner]
fitter[fitter.py] --> data_getter[data_getter.py]
fitter --> ml_common_funcs[ml_common_funcs.py]
fitter --> data_manager[ml_data_manager.py]
fitter --> settings[settings]
ml_data_manager[ml_data_manager.py] --> ML[ML.py]
ml_data_manager --> fitter[fitter.py]
ml_data_manager --> gds_object[gds_object.py]
ml_data_manager --> word_to_vec_object[word_to_vec_object.py]
ml_data_manager --> BaseRedis[BaseRedis]
ml_data_manager --> redis_manager[redis_manager]
ml_data_manager --> text_cleaner[text_cleaner]
data_getter[data_getter.py] --> ABC_manager[ABC_manager.py]
data_getter --> redis_manager[redis_manager]
data_getter --> DataScience[DataScience]
runner[runner.py] --> wb_manager[wb_manager.py]
runner --> ml_data_manager[ml_data_manager.py]
runner --> message_sender[message_for_not_pay_user_sender]
run_script[run_update_predict_ctr.py] --> runner[runner.py]
style ML fill:#f9f,stroke:#333
style fitter fill:#f9f,stroke:#333
style ml_data_manager fill:#f9f,stroke:#333
style data_getter fill:#f9f,stroke:#333
style runner fill:#f9f,stroke:#333
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)

## Performance Considerations

The ML integration is designed for high-performance operation in a production environment with several key performance considerations:

1. **Low-latency inference**: The system uses Redis as a cache for feature vectors, enabling sub-millisecond retrieval of keyword and product features during prediction.

2. **Parallel processing**: The architecture leverages asyncio for non-blocking I/O operations, allowing concurrent data retrieval from multiple sources (ClickHouse, Neo4j, Redis).

3. **Memory efficiency**: The global model is loaded once and shared across requests, reducing memory overhead and initialization time.

4. **Batch processing**: Feature retrieval operations are batched to minimize database round-trips and network overhead.

5. **Asynchronous execution**: Long-running operations like model training are executed in separate threads using asyncio.to_thread to prevent blocking the event loop.

6. **Caching strategy**: Both feature vectors and prediction results are cached to avoid redundant computation.

7. **Resource limiting**: Semaphores are used to limit concurrent model update processes, preventing resource exhaustion.

8. **Efficient data structures**: Pandas DataFrames are used for efficient data manipulation and XGBoost for high-performance gradient boosting.

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)

## Troubleshooting Guide

### Common Issues and Solutions

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py#L1-L282)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L1-L295)

#### Model Drift
**Symptoms**: Decreasing prediction accuracy over time, increasing discrepancy between predicted and actual CTR.
**Causes**: Changes in user behavior, market conditions, or platform algorithms.
**Solutions**: 
- Implement regular retraining schedule (currently configured to run periodically)
- Monitor prediction accuracy metrics
- Set up alerts for significant performance degradation
- Maintain versioned models for rollback capability

#### Data Quality Problems
**Symptoms**: Missing features, null values in training data, failed feature extraction.
**Causes**: Incomplete product data, missing images, malformed keyword data.
**Solutions**:
- Implement data validation checks in ml_data_manager.py
- Add fallback mechanisms for missing features
- Log data quality issues for monitoring
- Implement data cleansing routines in text_cleaner

#### Performance Bottlenecks
**Symptoms**: Slow prediction times, high CPU/memory usage, timeout errors.
**Causes**: Large feature vectors, unoptimized queries, insufficient caching.
**Solutions**:
- Optimize feature vector dimensions
- Implement query batching
- Increase Redis cache capacity
- Profile and optimize critical code paths

#### Model Training Failures
**Symptoms**: Training process crashes, incomplete model updates, missing model files.
**Causes**: Insufficient training data, memory limitations, file system issues.
**Solutions**:
- Verify minimum data requirements are met
- Monitor system resources during training
- Implement robust error handling in fitter.py
- Ensure proper file permissions and disk space

#### Integration Issues
**Symptoms**: Failed predictions, missing prediction results in bidding system.
**Causes**: Redis connectivity issues, incorrect data formatting, API changes.
**Solutions**:
- Implement comprehensive logging in ML.py
- Add integration tests
- Monitor Redis connectivity and performance
- Implement circuit breakers for external dependencies

## Conclusion

The Machine Learning Integration in the adv-bot system provides a robust framework for CTR prediction in advertising campaigns. The architecture combines historical campaign data from ClickHouse with product and keyword features from multiple sources to train an XGBoost model that delivers real-time predictions. The system is designed for high availability and performance, with careful attention to low-latency inference requirements in high-frequency bidding scenarios. Key strengths include its modular design, comprehensive feature engineering pipeline, and seamless integration with the bidding logic. The use of established libraries like xgboost, gensim, and tensorflow ensures reliability and access to state-of-the-art machine learning techniques. For optimal performance, regular monitoring of model accuracy and data quality is recommended, along with adherence to the established retraining schedule to mitigate model drift.