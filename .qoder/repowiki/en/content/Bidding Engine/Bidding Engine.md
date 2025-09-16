# Bidding Engine

<cite>
**Referenced Files in This Document**   
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [models.py](file://app/modules/wb_adv_updater/models.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [ml_common_funcs.py](file://app/modules/wb_adv_updater/ml_common_funcs.py)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py)
- [auction_adv.py](file://app/core/wb_api/data_classes/advs/auction_adv.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Bidding Engine Architecture](#bidding-engine-architecture)
3. [Core Components](#core-components)
4. [CTR Prediction System](#ctr-prediction-system)
5. [Bid Optimization Logic](#bid-optimization-logic)
6. [Bidding Modes and Configuration](#bidding-modes-and-configuration)
7. [Domain Models](#domain-models)
8. [Performance Considerations](#performance-considerations)
9. [Common Issues and Solutions](#common-issues-and-solutions)
10. [Integration and Invocation Flow](#integration-and-invocation-flow)

## Introduction
The Bidding Engine component of the adv-bot system is responsible for automated bidding decisions in Wildberries advertising campaigns. This document provides a comprehensive analysis of the bidding system, covering machine learning-based CTR prediction, bid optimization algorithms, auction strategies, and configuration options. The system integrates machine learning models with real-time bidding logic to optimize advertising performance while preventing overbidding and managing campaign budgets effectively.

## Bidding Engine Architecture

```mermaid
graph TD
subgraph "Data Sources"
ClickHouse[(ClickHouse)]
Redis[(Redis)]
PostgreSQL[(PostgreSQL)]
end
subgraph "ML Components"
Fitter[Fitter]
Predictor[Predictor]
Model[ML Model]
end
subgraph "Bidding Components"
Bidder[Bidder]
DataManager[DataManager]
DataSetter[DataSetter]
end
subgraph "Configuration"
AdvSetting[AdvSetting]
Settings[Settings]
end
ClickHouse --> Fitter
Redis --> Fitter
PostgreSQL --> Fitter
Fitter --> Model
Model --> Predictor
Predictor --> Redis
Redis --> DataManager
DataManager --> Bidder
AdvSetting --> Bidder
AdvSetting --> DataManager
Bidder --> WBApi[Wildberries API]
DataSetter --> WBApi
DataManager --> DataSetter
style Fitter fill:#f9f,stroke:#333
style Predictor fill:#f9f,stroke:#333
style Bidder fill:#bbf,stroke:#333
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

## Core Components

The Bidding Engine consists of several interconnected components that work together to make intelligent bidding decisions. The system combines machine learning predictions with rule-based optimization logic to adjust bids based on campaign performance and market conditions.

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

## CTR Prediction System

### Machine Learning Model Architecture

```mermaid
classDiagram
class Predictor {
+predict_ctr_for_keywords() void
+_get_df_for_predict(adv_settings) DataFrame
+_predict(df) DataFrame
+get_keyword_features(keywords) dict
+get_nmid_to_item_features(nmids) dict
+__update_predict_ctr(redis_pipeline, keyword_setting, predict_df) void
}
class Fitter {
+__get_average_vector(nmids, df_vectors) array
+fill_average_vector(df_stat, df_vectors) DataFrame
+_get_df_for_fit() DataFrame
+_bayesian_apply(df) DataFrame
+get_nmid_to_item_features(nmids_batch) dict
}
class DataGetter {
+get_item_features_from_redis(nmids_batch) list
+get_keyword_features_from_redis(keywords) list
+get_item_features_from_neo(nmids_batch) list
+get_keyword_features_from_neo(keywords) list
}
class MLCommonFuncs {
+save_model(model, time_stamp) void
+load_model() XGBModel
+get_keyword_features(keywords) dict
}
Predictor --> DataGetter : "uses"
Fitter --> DataGetter : "uses"
Predictor --> MLCommonFuncs : "uses"
Fitter --> MLCommonFuncs : "uses"
Predictor --> Redis : "writes predictions"
Fitter --> ClickHouse : "reads training data"
Fitter --> Redis : "reads features"
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [ml_common_funcs.py](file://app/modules/wb_adv_updater/ml_common_funcs.py)

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)

The CTR prediction system uses an XGBoost regression model trained on historical campaign data to predict click-through rates for keywords. The model combines item features (derived from product vectors) and keyword features (derived from text vectors) to make predictions.

The training process in `fitter.py` collects data from active advertising campaigns, normalizes features, and trains the model using cross-validation to ensure robustness. The prediction process in `ML.py` retrieves the trained model, gathers current campaign data, and generates CTR predictions that are stored in Redis for low-latency access during bidding.

## Bid Optimization Logic

### Bidding Decision Flow

```mermaid
flowchart TD
Start([Start Bid Process]) --> GetCampaignData["Retrieve Campaign Settings"]
GetCampaignData --> CheckBidderActive{"Bidder Active?"}
CheckBidderActive --> |No| End([Exit])
CheckBidderActive --> |Yes| GetKeywords["Retrieve Keywords"]
GetKeywords --> ClassifyKeywords["Classify as Good/Bad"]
ClassifyKeywords --> GetCurrentCPM["Get Current CPM"]
GetCurrentCPM --> GetBestKeyword["Find Best Performing Keyword"]
GetBestKeyword --> CheckPosition{"Position < Max?"}
CheckPosition --> |Yes| DecreaseBid["Decrease CPM by Step"]
CheckPosition --> |No| CheckPosition2{"Position > Max?"}
CheckPosition2 --> |Yes| IncreaseBid["Increase CPM by Step"]
CheckPosition2 --> |No| MaintainBid["Maintain Current CPM"]
DecreaseBid --> ApplyMaxCPM["Apply Max CPM Limit"]
IncreaseBid --> ApplyMaxCPM
MaintainBid --> ApplyMaxCPM
ApplyMaxCPM --> CheckResetPlace["Check Reset Place Setting"]
CheckResetPlace --> |Position > Max & Reset Enabled| UpdateMaxPlace["Update Max Place"]
CheckResetPlace --> |No| ApplyMinCPM["Apply Minimum CPM"]
UpdateMaxPlace --> ApplyMinCPM
ApplyMinCPM --> SendBid["Send New CPM to API"]
SendBid --> End
```

**Diagram sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

**Section sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

The bid optimization logic in `bidder.py` implements a feedback control system that adjusts bids based on keyword performance and position. The algorithm compares the current position of the best-performing keyword against the target maximum position and adjusts the CPM accordingly:

- If the position is better than the target, decrease the bid by the configured step
- If the position is worse than the target, increase the bid by the configured step
- If the position matches the target, maintain the current bid

The system enforces maximum and minimum bid constraints to prevent overbidding and ensure bids remain within acceptable ranges.

## Bidding Modes and Configuration

### Configuration Options

| Configuration Parameter | Description | Default Value | Source |
|------------------------|-------------|---------------|------|
| bidder_for_auto | Enables/disables automatic bidding | True | [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L425) |
| bidder_step | Bid adjustment step in rubles | DEFAULT_BIDDER_STEP | [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L405) |
| max_cpm | Maximum allowable CPM | None | [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L391) |
| max_place | Target maximum position | None | [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L392) |
| reset_place | Automatically adjust max_place when target is achieved | True | [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L403) |
| exponent_predict_ctr | Exponent for CTR prediction | settings.DEFAULT_CTR_EXPONENTA | [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L408) |
| auction_boost_all_phrase_mode | Enable auction boost for all phrases | False | [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L414) |

The system supports different bidding modes through configuration settings stored in the `AdvSetting` model. The primary mode is automatic bidding (`bidder_for_auto`), which enables the bid optimization algorithm to run continuously. The step mode allows for manual bid adjustments with the system providing recommendations based on performance data.

**Section sources**
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)

## Domain Models

### BidStrategy and Related Entities

```mermaid
erDiagram
ADV_SETTING {
int id PK
string name
int adv_id
int wb_cabinet_id FK
boolean bidder_for_auto
int bidder_step
int max_cpm
int max_place
boolean reset_place
float exponent_predict_ctr
boolean auction_boost_all_phrase_mode
}
KEYWORD_SETTING {
int id PK
string text
int adv_setting_id FK
int hard_status
float predict_ctr
boolean relevant
}
CALCULATED_KEYWORD {
string text
int clicks
int views
int spend
int position
float predict_ctr
float baes_ctr
int status
string reason
}
ADV_SETTING ||--o{ KEYWORD_SETTING : "contains"
ADV_SETTING ||--o{ CALCULATED_KEYWORD : "analyzes"
KEYWORD_SETTING }|--|| CALCULATED_KEYWORD : "maps to"
```

**Diagram sources**
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

The domain model centers around the `AdvSetting` entity, which contains configuration for bidding behavior. Each advertising campaign has associated keywords stored in `KeywordSetting`, which are analyzed and classified as good or bad based on performance metrics. The `CalculatedKeyword` entity represents the runtime analysis of keyword performance, including predicted CTR, actual performance, and bidding status.

## Performance Considerations

### Low-Latency Bid Processing

```mermaid
flowchart LR
subgraph "High Latency Sources"
Database[(PostgreSQL)]
ClickHouse[(ClickHouse)]
WildberriesAPI[Wildberries API]
end
subgraph "Low Latency Cache"
Redis[(Redis)]
end
Database --> |Periodic| Redis
ClickHouse --> |Periodic| Redis
Redis --> |Real-time| Bidder
Bidder --> |Real-time| Redis
Bidder --> |Real-time| WildberriesAPI
style Redis fill:#cfc,stroke:#333
style Database fill:#fcc,stroke:#333
style ClickHouse fill:#fcc,stroke:#333
style WildberriesAPI fill:#fcc,stroke:#333
```

**Diagram sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)

The Bidding Engine is optimized for low-latency operations by leveraging Redis as a high-performance cache. All frequently accessed data, including CTR predictions, keyword positions, and campaign settings, are stored in Redis to minimize database queries during the bidding process.

The system uses several optimization techniques:
- Asynchronous I/O operations to prevent blocking
- Batch processing of keyword updates
- In-memory data structures for fast access
- Connection pooling for database and API access
- Caching of frequently accessed data

These optimizations ensure that bid decisions can be made quickly, typically within milliseconds, allowing the system to respond rapidly to changing market conditions.

**Section sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)

## Common Issues and Solutions

### Overbidding Prevention

```mermaid
flowchart TD
Start --> CheckMaxCPM["Check max_cpm setting"]
CheckMaxCPM --> |CPM < max_cpm| ApplyBid["Apply calculated bid"]
CheckMaxCPM --> |CPM >= max_cpm| CapBid["Cap at max_cpm"]
CapBid --> CheckResetPlace["Check reset_place setting"]
CheckResetPlace --> |Enabled| UpdateTarget["Update max_place to current + 1"]
CheckResetPlace --> |Disabled| MaintainTarget["Maintain current target"]
UpdateTarget --> LogAdjustment["Log position adjustment"]
MaintainTarget --> LogAdjustment
LogAdjustment --> Complete["Bid adjustment complete"]
```

**Diagram sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

The system addresses common bidding issues through several mechanisms:

**Overbidding Prevention**: The system enforces maximum bid limits through the `max_cpm` parameter and automatically caps bids that exceed this threshold. When the maximum bid is reached, the system can optionally adjust the target position to prevent continuous bid escalation.

**Prediction Inaccuracies**: The CTR prediction model uses Bayesian averaging to handle keywords with limited historical data. For keywords with insufficient views, the system applies a conservative approach by not classifying them as bad based solely on low performance.

**Position Instability**: The bid adjustment algorithm uses a step-based approach rather than proportional control to prevent oscillation and ensure stable positioning. The step size is configurable to balance responsiveness and stability.

**Budget Management**: The system checks cabinet balance before making bid adjustments to ensure sufficient funds are available for continued advertising.

**Section sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [ML.py](file://app/modules/wb_adv_updater/ML.py)

## Integration and Invocation Flow

### Campaign Update and Bidding Decision Sequence

```mermaid
sequenceDiagram
participant Scheduler as "Scheduler"
participant Bidder as "Bidder"
participant DataManager as "DataManager"
participant Predictor as "Predictor"
participant Redis as "Redis"
participant WildberriesAPI as "Wildberries API"
Scheduler->>Bidder : _run_bidder_process()
Bidder->>DataManager : Get active AdvSettings
DataManager->>PostgreSQL : SELECT AdvSetting
PostgreSQL-->>DataManager : Return settings
DataManager-->>Bidder : Return settings
loop For each AdvSetting
Bidder->>DataManager : get_good_bad_phrases(adv_setting)
DataManager->>ClickHouse : Query keyword statistics
ClickHouse-->>DataManager : Return stats
DataManager->>Redis : Get keyword positions
Redis-->>DataManager : Return positions
DataManager->>Redis : Get CTR predictions
Redis-->>DataManager : Return predictions
DataManager-->>Bidder : Return classified keywords
Bidder->>Bidder : Calculate new CPM
Bidder->>WildberriesAPI : update_cpm(adv_id, new_cpm)
WildberriesAPI-->>Bidder : Confirmation
end
Bidder-->>Scheduler : Process complete
```

**Diagram sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [ML.py](file://app/modules/wb_adv_updater/ML.py)

The integration flow begins with a scheduler that invokes the bidding process at regular intervals. The `Bidder` component retrieves active campaign settings from the database and processes each campaign individually. For each campaign, it requests keyword analysis from the `DataManager`, which aggregates data from multiple sources including ClickHouse (historical statistics), Redis (current positions and predictions), and the database (campaign configuration).

The classified keywords are used to determine the appropriate bid adjustment, which is then applied through the Wildberries API. This end-to-end process ensures that bidding decisions are based on comprehensive, up-to-date information from multiple data sources.

**Section sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [ML.py](file://app/modules/wb_adv_updater/ML.py)