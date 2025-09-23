FROM neo4j:2025.07.1

# Копируем плагины из текущей директории в контейнер
COPY apoc-2025.07.1-core.jar /var/lib/neo4j/plugins/apoc.jar
COPY neo4j-graph-data-science-2.20.0.jar /var/lib/neo4j/plugins/neo4j-graph-data-science.jar

# Устанавливаем правильные права на файлы плагинов
RUN chown neo4j:neo4j /var/lib/neo4j/plugins/apoc.jar \
    && chown neo4j:neo4j /var/lib/neo4j/plugins/neo4j-graph-data-science.jar

# Открываем порты для Neo4j
EXPOSE 7474 7473 7687

# Запускаем Neo4j
CMD ["neo4j"]