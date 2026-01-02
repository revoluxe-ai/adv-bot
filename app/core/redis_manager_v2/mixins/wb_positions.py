


#
#
# class WBPositionsMixin(WBClustersMixin):
#     ...
    # async def add_positions_to_redis(
    #     self: BaseRedisManagerProtocol, positions: list[WBItemPosition]
    # ) -> None:
    #     base_key = "adv_positions"
    #     for position in positions:
    #         position.timestamp = datetime.now()
    #         key = f"{base_key}:{position.keyword_text}:{position.nmid}"
    #         position_dict = position.to_dict()
    #         await self._client.set(key, json.dumps(position_dict))
    #
    # async def get_keyword_position(
    #     self: BaseRedisManagerProtocol, keyword: str, nmid: int
    # ) -> WBItemPosition | None:
    #     base_key = f"adv_positions:{keyword}:{nmid}"
    #     json_data = await self._client.get(base_key)
    #     if not json_data:
    #         cluster, _ = await super().get_cluster_and_preset(keyword)
    #         if not cluster:
    #             return None
    #         base_key = f"adv_positions:{cluster}:{nmid}"
    #         json_data = await self._client.get(base_key)
    #         if not json_data:
    #             return None
    #         else:
    #             position = WBItemPosition.from_dict(json.loads(json_data))
    #             return position
    #     position = WBItemPosition.from_dict(json.loads(json_data))
    #     return position

    # async def get_keywords_positions(
    #     self: BaseRedisManagerProtocol, adv_setting, texts
    # ):
    #     keys = [
    #         "adv_positions:" + text + ":" + str(adv_setting.nmids[0]) for text in texts
    #     ]
    #     results = await self._client.mget(keys)
    #     positions = []
    #     missing_texts = []
    #
    #     for text, json_data in zip(texts, results):
    #         if json_data:
    #             position = WBItemPosition.from_dict(json.loads(json_data))
    #             position.keyword_text = text
    #             positions.append(position)
    #         else:
    #             missing_texts.append(text)
    #
    #     if missing_texts:
    #         cluster_keys = []
    #         cluster_map = {}
    #
    #         for text in missing_texts:
    #             cluster, _ = await super().get_cluster_and_preset(text)
    #             if cluster:
    #                 key = "adv_positions:" + cluster + ":" + str(adv_setting.nmids[0])
    #                 cluster_keys.append(key)
    #                 cluster_map[key] = text
    #
    #         if cluster_keys:
    #             cluster_results = await self._client.mget(cluster_keys)
    #
    #             for key, json_data in zip(cluster_keys, cluster_results):
    #                 if json_data:
    #                     position = WBItemPosition.from_dict(json.loads(json_data))
    #                     position.keyword_text = cluster_map[key]
    #                     positions.append(position)
    #
    #     return positions

    # async def set_position_to_out_index(self: BaseRedisManagerProtocol, position):
    #     position_out_index = WBItemPosition()
    #     position_out_index.position = 0
    #     position_out_index.keyword_text = position.keyword_text
    #     position_out_index.adv_id = position.adv_id
    #     position_out_index.nmid = position.nmid
    #     position_out_index.adv_type = position.adv_type
    #     await typing.cast("Any", self).add_positions_to_redis([position_out_index])
