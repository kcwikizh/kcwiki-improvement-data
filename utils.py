import json
import re
import requests


class ImprovementCache:
    FILE_PATH = './improve_data.json'
    json_obj = {}

    @classmethod
    def read_file(cls):
        import os
        if not os.path.exists(cls.FILE_PATH):
            return

        with open(cls.FILE_PATH, 'r', encoding='utf-8') as f:
            cls.json_obj = json.loads(f.read())

    @classmethod
    def set_cache(cls, equip_id, equip_info):
        cls.json_obj[equip_id] = equip_info
        cls.save_file()

    @classmethod
    def get_cache(cls, equip_id):
        return cls.json_obj.get(equip_id, None)

    @classmethod
    def save_file(cls):
        with open(cls.FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(json.dumps(cls.json_obj, ensure_ascii=False, separators=(',', ':')))


def Printf(*args, color_str=''):
    if not color_str:
        print(*args)
        return

    print('\033[' + color_str, end='')
    print(*args, end='')
    print('\033[0m')


class ItemDataHelper:
    ITEM_DATA_URL = 'https://bot.kcwiki.moe/json/items.json'

    EQUIP_ICON_ID = {  # 该列表可能更新不及时，请尽量避免使用icon字段
        '小口径主砲': 1,
        '中口径主砲': 2,
        '大口径主砲': 3,
        '艦上戦闘機': 6,
        '艦上爆撃機': 7,
        '艦上攻撃機': 8,
        '艦上偵察機': 9,
        '水上偵察機': 10,
        '上陸用舟艇': 20,
        '対潜哨戒機': 22,
        '司令部施設': 34,
        '熟練搭乗員': 70,
        '新型航空兵装資材': 77,
    }

    json_obj = json.loads(requests.get(ITEM_DATA_URL).content)

    @classmethod
    def get_icon_id(cls, equip_id: str | int, default_val: str | int | None = 0):
        if equip_id == 0:
            return 0

        if type(equip_id) is int:
            equip_id = str(equip_id)

        equip_id = equip_id.rjust(3, '0')

        if equip_id not in cls.json_obj:
            Printf(f'[Warning] Equip id {equip_id} not in json_obj, length: {len(cls.json_obj)}', color_str='35m')
            return default_val

        return cls.json_obj[equip_id]['类别'][2]

    @classmethod
    def get_icon_id_by_typename(cls, typename: str, equip_id: str = '', default_val=0):
        if typename in cls.EQUIP_ICON_ID:
            return cls.EQUIP_ICON_ID[typename]

        if equip_id:
            icon_id = cls.get_icon_id(equip_id, None)
            if icon_id is not None:
                return icon_id

        raise ValueError(f'[ERROR] {typename} not in EQUIP_ICON_ID')
        # import traceback
        # traceback.print_stack()
        # return default_val


class ShipInfoCache:
    name_cache = {}  # {ship_name: ship_id}
    id_cache = {}  # {ship_id: ship_name}

    @classmethod
    def get_id(cls, ship_name: str, default_val=None):
        if ship_name not in cls.name_cache:
            return default_val
        return cls.name_cache[ship_name]

    @classmethod
    def get_name(cls, ship_id, default_val=''):
        if ship_id == 0:
            return '-'

        if ship_id not in cls.id_cache:
            return default_val
        return cls.id_cache[ship_id]

    @classmethod
    def set_id(cls, ship_name: str, ship_id: int):
        cls.name_cache[ship_name] = ship_id
        cls.id_cache[ship_id] = ship_name

    @classmethod
    def set_id_by_img_url(cls, ship_name: str, url: str):
        img_filename = url.split('/')[-1].split('.')[0]
        img_filename = re.sub(r'[A-Za-z]', '', img_filename)
        cls.set_id(ship_name, int(img_filename))
