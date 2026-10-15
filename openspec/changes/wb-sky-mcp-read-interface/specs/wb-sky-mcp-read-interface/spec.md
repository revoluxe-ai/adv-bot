## ADDED Requirements

### Requirement: MCP first version is read-only
Удалённый MCP WB Sky MUST предоставлять только чтение. Инструменты записи, проверки ChangeSet, пробного применения ChangeSet, применения ChangeSet и любой мутации рекламы, эксперимента или кабинета MUST NOT существовать в этой версии.

#### Scenario: Write tool is not advertised
- **WHEN** клиент запрашивает список инструментов MCP
- **THEN** список MUST содержать только профиль, список магазинов, возможности и AI-пакет
- **AND** инструменты записи и ChangeSet MUST NOT быть в списке

#### Scenario: Mutation request is rejected
- **WHEN** клиент вызывает имя инструмента вне списка чтения
- **THEN** сервер MUST отказать
- **AND** MUST NOT изменить рекламу, кабинет или эксперимент

### Requirement: OAuth authorization code with PKCE
ChatGPT MUST входить как OAuth-клиент по Authorization Code + PKCE. Метод проверки MUST быть S256. Отдельная страница логина с паролем MUST NOT использоваться. Согласие человека MUST происходить в существующем Telegram-боте WB Sky.

#### Scenario: Authorize creates a one-time session
- **WHEN** клиент вызывает авторизацию с известным client id, точно совпавшим адресом возврата, state, scope чтения и PKCE S256
- **THEN** сервер MUST создать одноразовую сессию авторизации с коротким сроком
- **AND** MUST вернуть только переход в существующий Telegram-бот
- **AND** MUST NOT показать форму пароля или регистрацию на сайте

#### Scenario: Authorize rejects weak or foreign requests
- **WHEN** нет PKCE S256, запрошена область кроме чтения, адрес возврата не совпал точно или клиент неизвестен
- **THEN** сервер MUST отказать
- **AND** MUST NOT выдать код авторизации

#### Scenario: Deep link is not an API credential
- **WHEN** кто-то предъявляет токен глубокой ссылки, билет возврата или код авторизации как bearer к MCP
- **THEN** сервер MUST отказать
- **AND** эти значения MUST быть одноразовыми, короткоживущими и связанными с исходными client, redirect и state

#### Scenario: Opening the bot is not consent
- **WHEN** пользователь только открыл глубокую ссылку
- **THEN** сервер MUST NOT считать подключение подтверждённым
- **AND** код авторизации MUST NOT быть выдан до явного подтверждения в боте

#### Scenario: Confirm binds the canonical principal
- **WHEN** пользователь явно подтверждает подключение в боте
- **THEN** сервер MUST связать сессию с каноническим принципалом WB Sky, найденным по Telegram-пользователю
- **AND** MUST NOT записать Telegram user id как субъект токена доступа

#### Scenario: Return completes the original transaction
- **WHEN** пользователь открывает одноразовую ссылку возврата после подтверждения
- **THEN** сервер MUST перенаправить на заранее проверенный адрес клиента
- **AND** ответ MUST содержать код авторизации и исходный state
- **AND** MUST NOT перенаправить на адрес, которого не было в сессии

#### Scenario: Token exchange checks PKCE
- **WHEN** клиент меняет код на токен с верным verifier
- **THEN** сервер MUST выдать access token принципала со scope чтения
- **AND** повторное использование того же кода MUST быть отказано

### Requirement: Token identifies the principal and shops stay server-side
Access token MUST идентифицировать канонический принципал WB Sky и scope чтения. Постоянный список магазинов MUST NOT быть источником прав. На каждом защищённом вызове сервер MUST заново прочитать текущие разрешённые магазины. Неизвестная связь принципала и магазина MUST закрываться отказом.

#### Scenario: Profile hides credentials
- **WHEN** авторизованный клиент запрашивает профиль
- **THEN** ответ MUST содержать принципала и scope чтения
- **AND** MUST NOT содержать токен бота, токен WB API, пароль и Telegram user id как ключ доступа

#### Scenario: Shop list follows current cabinets
- **WHEN** авторизованный клиент запрашивает список магазинов
- **THEN** ответ MUST содержать только магазины, связанные с принципалом сейчас
- **AND** пустой список MUST быть успешным пустым результатом, а не данными чужого магазина

#### Scenario: Removed shop disappears immediately
- **WHEN** связь пользователя с магазином уже снята, даже если access token ещё не истёк
- **THEN** чтение этого shop_id MUST получить отказ
- **AND** сервер MUST NOT ждать истечения токена

#### Scenario: Foreign shop id fails closed
- **WHEN** аргумент shop_id не входит в текущие магазины принципала или магазин неизвестен
- **THEN** сервер MUST отказать
- **AND** MUST NOT вернуть данные этого магазина

### Requirement: Disconnect revokes ChatGPT access immediately
Пользователь MUST иметь возможность в боте увидеть активные подключения ChatGPT и отключить их. Отключение MUST лишать силы уже выданные access token этого подключения, не удаляя пользователя WB Sky и не снимая кабинеты само по себе.

#### Scenario: Disconnect invalidates tokens
- **WHEN** пользователь отключает подключение ChatGPT в боте
- **THEN** следующие вызовы MCP этим подключением MUST получить отказ
- **AND** refresh этого подключения MUST перестать выдавать новый доступ

#### Scenario: Already revoked connection stays denied
- **GIVEN** подключение уже отключено и нового события отключения нет
- **WHEN** клиент вызывает любой инструмент чтения со старым access token
- **THEN** сервер MUST отказать

### Requirement: Capabilities are explicit and dynamic
Возможности магазина MUST считаться для текущего принципала, магазина, scope и версии транспорта. Неподдерживаемое MUST быть явно неподдерживаемым. Сервер MUST NOT подменять отсутствие поддержки догадкой.

#### Scenario: Capabilities list only real read support
- **WHEN** у принципала есть доступ к магазину и запрошены возможности
- **THEN** ответ MUST включать только чтение, которое эта версия реально обслуживает
- **AND** запись, ChangeSet и прямые изменения рекламы MUST быть помечены как неподдерживаемые

#### Scenario: Capabilities without a grant fail closed
- **WHEN** shop_id не разрешён принципалу
- **THEN** сервер MUST отказать
- **AND** MUST NOT вернуть возможности как будто доступ есть

### Requirement: AI package read matches the canonical package
Инструмент AI-пакета MUST вернуть машинное представление уже собранного Full AI Package для одного магазина и периода. Он MUST NOT вводить вторую семантику датасетов, покрытия или пробелов. Бинарный ZIP MUST NOT быть обязательным телом ответа. Крупное содержимое MUST быть ограничено по размеру и явно помечено как опущенное, без заявления полной полноты вложенных байт.

#### Scenario: Package returns structured canonical content
- **WHEN** принципал с доступом запрашивает AI-пакет магазина и корректный период
- **THEN** ответ MUST содержать manifest и карточки того же пакета
- **AND** семейства со статусом GAP MUST остаться GAP
- **AND** PARTIAL и UNKNOWN MUST сохраниться как в каноническом пакете

#### Scenario: Oversized payload is omitted honestly
- **WHEN** отдельный файл пакета больше транспортного предела
- **THEN** ответ MUST сохранить имя, хеш и размер
- **AND** MUST опустить байты
- **AND** MUST NOT назвать опущенные байты полностью вложенными

#### Scenario: One shop per package
- **WHEN** запрошен пакет
- **THEN** результат MUST относиться ровно к одному shop_id из аргумента, если он разрешён
- **AND** MUST NOT смешивать ряды другого магазина

### Requirement: Auth and read dependencies fail closed
Если хранилище сессий, принципалов или текущих прав недоступно, защищённый вызов и незавершённая авторизация MUST получить отказ. Сервер MUST NOT пропускать вызов по устаревшей копии прав.

#### Scenario: Auth backend unavailable
- **WHEN** хранилище OAuth-транзакций или база принципала и кабинетов недоступны во время авторизации или инструмента
- **THEN** сервер MUST отказать
- **AND** MUST NOT выдать код, токен или данные магазина
