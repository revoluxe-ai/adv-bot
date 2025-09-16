import json


class DayStat:
    def __init__(self, data):
        self.date = data['date']
        self.views = data['views']
        self.clicks = data['clicks']
        self.ctr = data['ctr']
        self.cpc = data['cpc']
        self.sum = data['sum']
        self.atbs = data['atbs']
        self.orders = data['orders']
        self.cr = data['cr']
        self.shks = data['shks']
        self.sum_price = data['sum_price']
        self.apps = data['apps']

    def to_json(self):
        return {
            'date': self.date,
            'views': self.views,
            'clicks': self.clicks,
            'ctr': self.ctr,
            'cpc': self.cpc,
            'sum': self.sum,
            'atbs': self.atbs,
            'orders': self.orders,
            'cr': self.cr,
            'shks': self.shks,
            'sum_price': self.sum_price,
            'apps': self.apps
        }

class FullAdvStat:
    def __init__(self, data):
        self.views = data['views']
        self.clicks = data['clicks']
        self.ctr = data['ctr']
        self.cpc = data['cpc']
        self.sum = data['sum']
        self.atbs = data['atbs']
        self.orders = data['orders']
        self.cr = data['cr']
        self.shks = data['shks']
        self.sum_price = data['sum_price']
        self.dates = data['dates']
        self.days = [DayStat(day_data) for day_data in data['days']]
        self.boosterStats = data['boosterStats']
        self.advertId = data['advertId']

    @property
    def adv_id(self):
        return self.advertId

    def to_json(self):
        return json.dumps({
            'views': self.views,
            'clicks': self.clicks,
            'ctr': self.ctr,
            'cpc': self.cpc,
            'sum': self.sum,
            'atbs': self.atbs,
            'orders': self.orders,
            'cr': self.cr,
            'shks': self.shks,
            'sum_price': self.sum_price,
            'dates': self.dates,
            'days': [day.to_json() for day in self.days],  # вызываем to_json для каждого объекта DayStat
            'boosterStats': self.boosterStats,
            'advertId': self.advertId
        })

    @staticmethod
    def from_json(json_data):
        data = json.loads(json_data)
        return FullAdvStat(data)

    @property
    def added_to_card(self):
        return self.atbs
