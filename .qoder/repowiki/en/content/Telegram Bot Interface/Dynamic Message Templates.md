# Dynamic Message Templates

<cite>
**Referenced Files in This Document**
- [templates.py](file://app/client_bot/user_interface/message_templates/templates.py)
- [base.py](file://app/client_bot/user_interface/message_templates/base.py)
- [messages.py](file://app/client_bot/user_interface/views/messages/messages.py)
- [adv_keyword_messages.py](file://app/client_bot/user_interface/views/messages/adv_keyword_messages/adv_keyword_messages.py)
- [last_auto_update_informer.py](file://app/client_bot/user_interface/views/messages/last_auto_update_informer/last_auto_update_informer.py)
- [positions_graphic_messanges.py](file://app/client_bot/user_interface/views/messages/positions_graphic_messanges/positions_graphic_messanges.py)
- [graphic_positions_creator.py](file://app/utils/graphic_positions_creator/graphic_positions_creator.py)
- [classes.py](file://app/utils/graphic_positions_creator/classes.py)
- [file_handler.py](file://app/file_handler.py)
- [message_manager.py](file://app/client_bot/message_manager.py)
- [const.py](file://app/client_bot/const.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Template Architecture Overview](#template-architecture-overview)
3. [Core Template Classes](#core-template-classes)
4. [Specialized Message Builders](#specialized-message-builders)
5. [Integration with Graphic Systems](#integration-with-graphic-systems)
6. [Performance Considerations](#performance-considerations)
7. [Conditional Content Rendering](#conditional-content-rendering)
8. [Template Consistency Management](#template-consistency-management)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Best Practices](#best-practices)

## Introduction

The dynamic message templating system in the adv-bot framework provides a sophisticated mechanism for constructing context-aware responses using data from business logic modules. This system enables the creation of personalized, data-driven messages that adapt to user permissions, subscription status, campaign state, and other contextual factors.

The architecture is built around a hierarchical template system that supports multiple content types including text-only messages, messages with inline keyboards, images, and combinations thereof. The system integrates seamlessly with the Telegram Bot API through the Aiogram framework while maintaining high performance and scalability under heavy load conditions.

## Template Architecture Overview

The message templating system follows a modular architecture with clear separation of concerns between template definition, data binding, and message delivery.

```mermaid
graph TB
subgraph "Template Layer"
Base[Base Template Class]
Text[Text Template]
TextWithKeyboard[Text + Keyboard]
TextWithImage[Text + Image]
TextWithKeyboardAndImage[Text + Keyboard + Image]
TextWithKeyboardPagination[Text + Keyboard + Pagination]
end
subgraph "Message Builders"
AdvKeywords[Adv Keywords Builder]
AutoUpdate[Auto Update Informer]
PositionsGraphic[Positions Graphic Messages]
SpecializedMessages[Specialized Message Types]
end
subgraph "Data Sources"
BusinessLogic[Business Logic Modules]
RedisCache[Redis Cache]
Database[Database]
ExternalAPI[External APIs]
end
subgraph "Output Layer"
TelegramBot[Telegram Bot API]
FileHandler[File Handler]
MessageManager[Message Manager]
end
Base --> Text
Base --> TextWithKeyboard
Base --> TextWithImage
Base --> TextWithKeyboardAndImage
Base --> TextWithKeyboardPagination
Text --> AdvKeywords
TextWithKeyboard --> AutoUpdate
TextWithImage --> PositionsGraphic
TextWithKeyboardAndImage --> SpecializedMessages
AdvKeywords --> BusinessLogic
AutoUpdate --> RedisCache
PositionsGraphic --> Database
SpecializedMessages --> ExternalAPI
BusinessLogic --> TelegramBot
RedisCache --> FileHandler
Database --> MessageManager
ExternalAPI --> TelegramBot
```

**Diagram sources**
- [templates.py](file://app/client_bot/user_interface/message_templates/templates.py#L1-L186)
- [base.py](file://app/client_bot/user_interface/message_templates/base.py#L1-L32)

**Section sources**
- [templates.py](file://app/client_bot/user_interface/message_templates/templates.py#L1-L186)
- [base.py](file://app/client_bot/user_interface/message_templates/base.py#L1-L32)

## Core Template Classes

### Base Template Class

The foundation of the template system is the abstract `Base` class that provides common functionality for all template types.

```mermaid
classDiagram
class Base {
-Bot _bot
-int _chat_id
+Bot bot
+int chat_id
+__call__(*args, **kwargs) None
+get_content_type() str
-__get_parent_class_name() str
}
class TextWithKeyboard {
<<abstract>>
+str text
+InlineKeyboardMarkup keyboard
+__call__() tuple[Message, str]
}
class TextWithImage {
<<abstract>>
+text property
+image property
+__call__() Message
}
class Text {
<<abstract>>
+text property
+__call__() LastMessage
}
class TextWithKeyboardAndImage {
<<abstract>>
+text property
+keyboard property
+image property
+image setter
+__call__() Message
}
Base <|-- TextWithKeyboard
Base <|-- TextWithImage
Base <|-- Text
Base <|-- TextWithKeyboardAndImage
```

**Diagram sources**
- [base.py](file://app/client_bot/user_interface/message_templates/base.py#L6-L32)
- [templates.py](file://app/client_bot/user_interface/message_templates/templates.py#L45-L186)

### Template Type Hierarchy

The system defines several specialized template types, each designed for specific messaging scenarios:

1. **Text Templates**: Simple text-only messages
2. **TextWithKeyboard**: Messages with inline keyboard navigation
3. **TextWithImage**: Messages with embedded images
4. **TextWithKeyboardAndImage**: Combined keyboard and image support
5. **TextWithKeyboardPagination**: Paginated content with navigation controls

Each template type inherits from the base class and implements specific properties for content generation while maintaining consistent behavior across the system.

**Section sources**
- [templates.py](file://app/client_bot/user_interface/message_templates/templates.py#L45-L186)
- [base.py](file://app/client_bot/user_interface/message_templates/base.py#L6-L32)

## Specialized Message Builders

### Adv Keyword Messages Builder

The `AdvKeywordsSetting` class handles the construction of comprehensive keyword performance reports with integrated graphics and statistical data.

```mermaid
sequenceDiagram
participant Client as Client Request
participant Builder as AdvKeywordsSetting
participant StatManager as CommonAdvsStatDataManager
participant GraphicCreator as Graphic Positions Creator
participant Telegram as Telegram API
Client->>Builder : __call__(state, sort_mode)
Builder->>Builder : Apply filters and sorting
Builder->>StatManager : get_data(adv_setting, keywords, days)
StatManager-->>Builder : CommonAdvsStatData
Builder->>GraphicCreator : get_keyword_history_graphic(adv_id, keywords)
GraphicCreator-->>Builder : BytesIO graphic
Builder->>Builder : Build formatted text
Builder->>Telegram : send_photo(caption, photo, keyboard)
Telegram-->>Client : Message response
```

**Diagram sources**
- [adv_keyword_messages.py](file://app/client_bot/user_interface/views/messages/adv_keyword_messages/adv_keyword_messages.py#L30-L259)

Key features of the Adv Keyword Messages Builder:

- **Dynamic Filtering**: Supports keyword filtering with partial match and exact match modes
- **Statistical Aggregation**: Calculates CTR, spend, orders, and prediction metrics
- **Visual Integration**: Generates real-time keyword position graphics
- **Sorting Options**: Multiple sorting modes for keyword presentation
- **Pagination Support**: Handles large keyword lists with pagination controls

### Last Auto Update Informer

The `LastAutoUpdateSettingInformer` provides automated status updates for various campaign settings and operations.

```mermaid
classDiagram
class LastAutoUpdateSettingInformer {
-LastAutoDeleteFromWhiteList delete_from_white_list
-LastAutoAddPhraseToWhiteList add_to_white_list
-LastSetUpTargetPlace up_target_place
-LastSetDownTargetPlace down_target_place
-LastUpdateFirstPhrase update_top_key
+str delete_from_white_list_str
+str add_to_white_list_str
+str up_target_place_str
+str down_target_place_str
+str update_top_key_str
+update_data() None
+to_str_timestamp(datetime) str
}
class LastAutoDeleteFromWhiteList {
+get() datetime
}
class LastAutoAddPhraseToWhiteList {
+get() datetime
}
class LastSetUpTargetPlace {
+get() datetime
}
class LastSetDownTargetPlace {
+get() datetime
}
class LastUpdateFirstPhrase {
+get() datetime
}
LastAutoUpdateSettingInformer --> LastAutoDeleteFromWhiteList
LastAutoUpdateSettingInformer --> LastAutoAddPhraseToWhiteList
LastAutoUpdateSettingInformer --> LastSetUpTargetPlace
LastAutoUpdateSettingInformer --> LastSetDownTargetPlace
LastAutoUpdateSettingInformer --> LastUpdateFirstPhrase
```

**Diagram sources**
- [last_auto_update_informer.py](file://app/client_bot/user_interface/views/messages/last_auto_update_informer/last_auto_update_informer.py#L10-L43)

### Positions Graphic Messages

The positions graphic system creates visual representations of keyword performance trends.

```mermaid
flowchart TD
Start([Graphic Generation Request]) --> GetKeywords["Get Keyword Positions"]
GetKeywords --> SortKeywords["Sort by Relevance"]
SortKeywords --> FilterKeywords["Filter Top 5 Keywords"]
FilterKeywords --> CreateDataFrame["Create Position DataFrame"]
CreateDataFrame --> GeneratePlot["Generate Matplotlib Plot"]
GeneratePlot --> CheckLegend{"Need Legend?"}
CheckLegend --> |Yes| CreateLegend["Create Separate Legend"]
CheckLegend --> |No| EmbedLegend["Embed Legend in Plot"]
CreateLegend --> SaveImages["Save Images to BytesIO"]
EmbedLegend --> SaveImages
SaveImages --> ReturnResults["Return Image Streams"]
ReturnResults --> End([Complete])
```

**Diagram sources**
- [positions_graphic_messanges.py](file://app/client_bot/user_interface/views/messages/positions_graphic_messanges/positions_graphic_messanges.py#L1-L44)
- [graphic_positions_creator.py](file://app/utils/graphic_positions_creator/graphic_positions_creator.py#L30-L168)

**Section sources**
- [adv_keyword_messages.py](file://app/client_bot/user_interface/views/messages/adv_keyword_messages/adv_keyword_messages.py#L30-L259)
- [last_auto_update_informer.py](file://app/client_bot/user_interface/views/messages/last_auto_update_informer/last_auto_update_informer.py#L10-L43)
- [positions_graphic_messanges.py](file://app/client_bot/user_interface/views/messages/positions_graphic_messanges/positions_graphic_messanges.py#L1-L44)

## Integration with Graphic Systems

### Graphic Positions Creator

The graphic positions creator module handles the generation of keyword performance visualizations using advanced plotting libraries.

```mermaid
sequenceDiagram
participant Template as Message Template
participant Creator as Graphic Positions Creator
participant DataMgr as Data Manager
participant ClickHouse as ClickHouse DB
participant Matplotlib as Matplotlib Library
participant Seaborn as Seaborn Library
Template->>Creator : get_keyword_history_graphic(adv_id, keywords)
Creator->>DataMgr : get_keyword_positions_from_click_house(nmid)
DataMgr->>ClickHouse : Query keyword positions
ClickHouse-->>DataMgr : Position data
DataMgr-->>Creator : List[WBItemPosition]
Creator->>Creator : Group positions by keyword
Creator->>Creator : Sort keywords by relevance
Creator->>Creator : Create DataFrame for plotting
Creator->>Matplotlib : Configure plot settings
Creator->>Seaborn : Generate line plots
Seaborn-->>Creator : Plot data
Creator->>Creator : Save to BytesIO stream
Creator-->>Template : BytesIO graphic + legend
```

**Diagram sources**
- [graphic_positions_creator.py](file://app/utils/graphic_positions_creator/graphic_positions_creator.py#L30-L168)
- [classes.py](file://app/utils/graphic_positions_creator/classes.py#L1-L10)

### File Management and Caching

The file handler system manages image caching and optimization for efficient message delivery.

```mermaid
flowchart TD
ImageRequest[Image Request] --> CheckLocal{"Local Cache<br/>Available?"}
CheckLocal --> |Yes| LoadLocal["Load from Local Cache"]
CheckLocal --> |No| CheckRemote{"Remote URL<br/>Available?"}
CheckRemote --> |Yes| DownloadRemote["Download from Remote"]
CheckRemote --> |No| LoadFromFile["Load from File Path"]
DownloadRemote --> ConvertFormat["Convert Format if Needed"]
LoadLocal --> ConvertFormat
LoadFromFile --> ConvertFormat
ConvertFormat --> CalculateHash["Calculate MD5 Hash"]
CalculateHash --> CheckTelegram{"Telegram File<br/>Exists?"}
CheckTelegram --> |Yes| ReturnExisting["Return Existing File ID"]
CheckTelegram --> |No| UploadNew["Upload New File"]
UploadNew --> StoreCache["Store in Cache"]
StoreCache --> ReturnNew["Return New File ID"]
ReturnExisting --> End[Complete]
ReturnNew --> End
```

**Diagram sources**
- [file_handler.py](file://app/file_handler.py#L40-L113)

**Section sources**
- [graphic_positions_creator.py](file://app/utils/graphic_positions_creator/graphic_positions_creator.py#L30-L168)
- [classes.py](file://app/utils/graphic_positions_creator/classes.py#L1-L10)
- [file_handler.py](file://app/file_handler.py#L40-L113)

## Performance Considerations

### Asynchronous Operations and Concurrency

The message templating system is designed to handle high-load scenarios through careful use of asynchronous operations and concurrent processing.

```mermaid
graph LR
subgraph "Concurrent Processing Strategies"
AsyncOps[Asynchronous Operations]
ParallelFetch[Parallel Data Fetching]
BatchProcessing[Batch Processing]
QueueManagement[Queue Management]
end
subgraph "Performance Optimizations"
Caching[Redis Caching]
LazyLoading[Lazy Loading]
MemoryOptimization[Memory Optimization]
ConnectionPooling[Connection Pooling]
end
subgraph "Scalability Features"
HorizontalScaling[Horizontal Scaling]
LoadBalancing[Load Balancing]
ResourceMonitoring[Resource Monitoring]
AutoScaling[Auto-scaling]
end
AsyncOps --> Caching
ParallelFetch --> LazyLoading
BatchProcessing --> MemoryOptimization
QueueManagement --> ConnectionPooling
Caching --> HorizontalScaling
LazyLoading --> LoadBalancing
MemoryOptimization --> ResourceMonitoring
ConnectionPooling --> AutoScaling
```

### Memory Management and Optimization

The system implements several strategies to minimize memory usage and optimize performance:

1. **Lazy Evaluation**: Template properties are computed only when needed
2. **Streaming Processing**: Large datasets are processed in chunks
3. **Efficient Data Structures**: Use of appropriate data structures for different operations
4. **Garbage Collection**: Proper cleanup of temporary objects and resources

### Scalability Patterns

The architecture supports horizontal scaling through:

- **Stateless Design**: Templates don't maintain internal state between requests
- **Shared Resources**: Efficient sharing of expensive resources like database connections
- **Circuit Breakers**: Protection against cascading failures
- **Rate Limiting**: Built-in throttling mechanisms for external API calls

**Section sources**
- [graphic_positions_creator.py](file://app/utils/graphic_positions_creator/graphic_positions_creator.py#L100-L168)
- [file_handler.py](file://app/file_handler.py#L40-L113)

## Conditional Content Rendering

### User Permission-Based Rendering

The system adapts content based on user permissions and roles:

```mermaid
flowchart TD
UserRequest[User Request] --> CheckPermissions["Check User Permissions"]
CheckPermissions --> HasAdmin{"Has Admin<br/>Access?"}
HasAdmin --> |Yes| AdminContent["Render Admin Content"]
HasAdmin --> |No| StandardContent["Render Standard Content"]
StandardContent --> CheckSubscription{"Subscription<br/>Active?"}
CheckSubscription --> |Yes| PremiumFeatures["Enable Premium Features"]
CheckSubscription --> |No| BasicFeatures["Limit to Basic Features"]
PremiumFeatures --> RenderMessage["Render Final Message"]
BasicFeatures --> RenderMessage
AdminContent --> RenderMessage
RenderMessage --> SendToUser["Send to User"]
```

### Subscription Status Adaptation

Different subscription tiers trigger different content rendering strategies:

- **Free Tier**: Limited statistics, basic visualizations
- **Premium Tier**: Full analytics, advanced graphics, real-time updates
- **Enterprise Tier**: Custom dashboards, priority processing, dedicated support

### Campaign State Awareness

The system renders content differently based on campaign lifecycle stages:

- **Setup Phase**: Guidance and tutorial content
- **Active Phase**: Performance metrics and optimization tips
- **Paused Phase**: Resume options and performance summary
- **Completed Phase**: Final report and recommendations

**Section sources**
- [messages.py](file://app/client_bot/user_interface/views/messages/messages.py#L582-L710)

## Template Consistency Management

### Centralized Configuration

The system maintains consistency through centralized configuration management:

```mermaid
graph TB
subgraph "Configuration Sources"
GlobalConfig[Global Config]
TemplateConfig[Template Config]
UserPreferences[User Preferences]
SessionData[Session Data]
end
subgraph "Consistency Mechanisms"
ValidationRules[Validation Rules]
DefaultValues[Default Values]
FallbackStrategies[Fallback Strategies]
VersionControl[Version Control]
end
subgraph "Quality Assurance"
UnitTests[Unit Tests]
IntegrationTests[Integration Tests]
SmokeTests[Smoke Tests]
RegressionTests[Regression Tests]
end
GlobalConfig --> ValidationRules
TemplateConfig --> DefaultValues
UserPreferences --> FallbackStrategies
SessionData --> VersionControl
ValidationRules --> UnitTests
DefaultValues --> IntegrationTests
FallbackStrategies --> SmokeTests
VersionControl --> RegressionTests
```

### Template Versioning and Migration

The system supports template versioning to ensure backward compatibility:

- **Schema Evolution**: Gradual migration of template structures
- **Backward Compatibility**: Support for older template formats
- **Automatic Migration**: Seamless conversion between versions
- **Rollback Capability**: Ability to revert to previous versions

### Quality Assurance Processes

Comprehensive testing ensures template reliability:

- **Automated Testing**: Continuous integration with template validation
- **Manual Review**: Human oversight for complex templates
- **Performance Testing**: Load testing with realistic scenarios
- **User Acceptance Testing**: Real-world validation by end users

**Section sources**
- [templates.py](file://app/client_bot/user_interface/message_templates/templates.py#L1-L186)
- [base.py](file://app/client_bot/user_interface/message_templates/base.py#L1-L32)

## Troubleshooting Guide

### Common Issues and Solutions

#### Template Rendering Failures

**Problem**: Templates fail to render with missing data
**Solution**: 
1. Verify data source connectivity
2. Check template property implementations
3. Implement proper error handling and fallbacks
4. Log detailed error information for debugging

#### Performance Degradation

**Problem**: Slow message delivery under load
**Solutions**:
1. Optimize database queries and caching
2. Implement connection pooling
3. Use asynchronous processing where appropriate
4. Monitor resource usage and scale accordingly

#### Image Generation Issues

**Problem**: Graphics fail to generate or display incorrectly
**Solutions**:
1. Verify matplotlib and seaborn installations
2. Check image format compatibility
3. Implement graceful degradation for unsupported formats
4. Test with various data sets and edge cases

### Debugging Tools and Techniques

The system provides several debugging capabilities:

- **Logging Integration**: Comprehensive logging at all levels
- **Template Inspection**: Runtime inspection of template properties
- **Performance Profiling**: Built-in performance monitoring
- **Error Tracking**: Centralized error reporting and analysis

**Section sources**
- [message_manager.py](file://app/client_bot/message_manager.py#L1-L34)
- [file_handler.py](file://app/file_handler.py#L40-L113)

## Best Practices

### Template Design Principles

1. **Single Responsibility**: Each template should handle one specific messaging scenario
2. **Composition Over Inheritance**: Favor composition for complex templates
3. **Immutable Data**: Templates should not modify input data
4. **Clear Separation**: Distinct separation between data and presentation logic

### Performance Optimization Guidelines

1. **Lazy Loading**: Defer expensive computations until absolutely necessary
2. **Caching Strategy**: Implement multi-level caching for frequently accessed data
3. **Resource Management**: Properly manage database connections and file handles
4. **Async Operations**: Use asynchronous patterns for I/O-bound operations

### Security Considerations

1. **Input Validation**: Thorough validation of all input data
2. **SQL Injection Prevention**: Use parameterized queries for database access
3. **XSS Prevention**: Proper escaping of user-generated content
4. **Rate Limiting**: Implement appropriate rate limiting for external API calls

### Maintenance and Evolution

1. **Documentation**: Maintain comprehensive documentation for all templates
2. **Testing**: Implement comprehensive test suites for template functionality
3. **Monitoring**: Set up monitoring for template performance and reliability
4. **Version Control**: Use version control for template changes and rollbacks

The dynamic message templating system provides a robust, scalable foundation for delivering personalized, context-aware messages in the adv-bot ecosystem. Through careful design and implementation of performance optimizations, the system maintains high reliability and responsiveness even under heavy load conditions.