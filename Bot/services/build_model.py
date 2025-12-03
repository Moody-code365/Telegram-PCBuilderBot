class PCBuild:

    def __init__(self):
        self.cpu = None
        self.motherboard = None
        self.gpu = None
        self.ram = None
        self.psu = None
        self.ssd = None
        self.hdd = None
        self.case = None
        self.cooler = None

    def set_part(self, part_name: str, component: dict):

        setattr(self, part_name, component)

    def total_price(self) -> int:

        price = 0
        for attr in ["cpu", "motherboard", "gpu", "ram",
                     "psu", "ssd", "hdd", "case", "cooler"]:
            item = getattr(self, attr)
            if item and "price" in item:
                price += item["price"]
        return price

    def as_dict(self) -> dict:

        data = {}
        for attr in ["cpu", "motherboard", "gpu", "ram",
                     "psu", "ssd", "hdd", "case", "cooler"]:
            item = getattr(self, attr)
            data[attr] = item
        return data
