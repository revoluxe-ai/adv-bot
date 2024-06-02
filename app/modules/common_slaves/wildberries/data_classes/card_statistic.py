class CardStatistic:
    def __repr__(self):
        return str(self.nmid)
    def __init__(self, data):
        self._data = data


    @property
    def X(self):
        return self._X


    @X.setter
    def X(self, value):
        self._X = value


    @property
    def nmid(self):
        return self._data['nmID']
    @property
    def offer_id(self):
        return self._data['vendorCode']

    @property
    def brand(self):
        return self._data['brandName']

    @property
    def category_name(self):
        return self._data['object']['name']

    @property
    def stock_fbo(self):
        return self._data['stocks']['stocksWb']

    @property
    def stock_fbs(self):
        return self._data['stocks']['stocksMp']

    @property
    def openCardCount_previous(self):
        return self._data['statistics']['previousPeriod']['openCardCount']
    @property
    def addToCartCount_previous(self):
        return self._data['statistics']['previousPeriod']['addToCartCount']

    @property
    def ordersCount_previous(self):
        return self._data['statistics']['previousPeriod']['ordersCount']

    @property
    def ordersSumRub_previous(self):
        return self._data['statistics']['previousPeriod']['ordersSumRub']

    @property
    def buyoutsCount_previous(self):
        return self._data['statistics']['previousPeriod']['buyoutsCount']

    @property
    def buyoutsSumRub_previous(self):
        return self._data['statistics']['previousPeriod']['buyoutsSumRub']

    @property
    def cancelCount_previous(self):
        return self._data['statistics']['previousPeriod']['cancelCount']

    @property
    def cancelSumRub_previous(self):
        return self._data['statistics']['previousPeriod']['cancelSumRub']

    @property
    def avgOrdersCountPerDay_previous(self):
        return self._data['statistics']['previousPeriod']['avgOrdersCountPerDay']

    @property
    def avgPriceRub_previous(self):
        return self._data['statistics']['previousPeriod']['avgPriceRub']

    @property
    def addToCartPercent_previous(self):
        return self._data['statistics']['previousPeriod']['conversions']['addToCartPercent']

    @property
    def cartToOrderPercent_previous(self):
        return self._data['statistics']['previousPeriod']['conversions']['cartToOrderPercent']

    @property
    def buyoutsPercent_previous(self):
        return self._data['statistics']['previousPeriod']['conversions']['buyoutsPercent']

    @property
    def openCardCount_current(self):
        return self._data['statistics']['selectedPeriod']['openCardCount']

    @property
    def addToCartCount_current(self):
        return self._data['statistics']['selectedPeriod']['addToCartCount']

    @property
    def ordersCount_current(self):
        return self._data['statistics']['selectedPeriod']['ordersCount']

    @property
    def ordersSumRub_current(self):
        return self._data['statistics']['selectedPeriod']['ordersSumRub']

    @property
    def buyoutsCount_current(self):
        return self._data['statistics']['selectedPeriod']['buyoutsCount']

    @property
    def buyoutsSumRub_current(self):
        return self._data['statistics']['selectedPeriod']['buyoutsSumRub']

    @property
    def cancelCount_current(self):
        return self._data['statistics']['selectedPeriod']['cancelCount']

    @property
    def cancelSumRub_current(self):
        return self._data['statistics']['selectedPeriod']['cancelSumRub']

    @property
    def avgOrdersCountPerDay_current(self):
        return self._data['statistics']['selectedPeriod']['avgOrdersCountPerDay']

    @property
    def avgPriceRub_current(self):
        return self._data['statistics']['selectedPeriod']['avgPriceRub']

    @property
    def addToCartPercent_current(self):
        return self._data['statistics']['selectedPeriod']['conversions']['addToCartPercent']

    @property
    def cartToOrderPercent_current(self):
        return self._data['statistics']['selectedPeriod']['conversions']['cartToOrderPercent']

    @property
    def buyoutsPercent_current(self):
        return self._data['statistics']['selectedPeriod']['conversions']['buyoutsPercent']

    @property
    def openCardDynamics(self):
        return self._data['statistics']['periodComparison']['openCardDynamics']

    @property
    def addToCartDynamics(self):
        return self._data['statistics']['periodComparison']['addToCartDynamics']

    @property
    def ordersCountDynamics(self):
        return self._data['statistics']['periodComparison']['ordersCountDynamics']

    @property
    def ordersSumRubDynamics(self):
        return self._data['statistics']['periodComparison']['ordersSumRubDynamics']

    @property
    def buyoutsCountDynamics(self):
        return self._data['statistics']['periodComparison']['buyoutsCountDynamics']

    @property
    def buyoutsSumRubDynamics(self):
        return self._data['statistics']['periodComparison']['buyoutsSumRubDynamics']

    @property
    def cancelCountDynamics(self):
        return self._data['statistics']['periodComparison']['cancelCountDynamics']

    @property
    def cancelSumRubDynamics(self):
        return self._data['statistics']['periodComparison']['cancelSumRubDynamics']

    @property
    def avgOrdersCountPerDayDynamics(self):
        return self._data['statistics']['periodComparison']['avgOrdersCountPerDayDynamics']

    @property
    def avgPriceRubDynamics(self):
        return self._data['statistics']['periodComparison']['avgPriceRubDynamics']

    @property
    def addToCartPercent_dynamics(self):
        return self._data['statistics']['periodComparison']['conversions']['addToCartPercent']

    @property
    def cartToOrderPercent_dynamics(self):
        return self._data['statistics']['periodComparison']['conversions']['cartToOrderPercent']

    @property
    def buyoutsPercent_dynamics(self):
        return self._data['statistics']['periodComparison']['conversions']['buyoutsPercent']


