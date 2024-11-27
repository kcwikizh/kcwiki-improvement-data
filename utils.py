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
        # 不再存储无改修的装备ID
        if not equip_info:
            return
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


class Start2DataHelper:
    START2_DATA_URL = 'https://api.kcwiki.moe/start2'
    START2_FILENAME = './api_start2.json'
    ICON_ID_INDEX = 2  # 装备类型所在的位置

    json_obj = json.loads(requests.get(START2_DATA_URL).content)

    @classmethod
    def get_slotitem_type_id(cls, equip_id: str | int, default_val: str | int | None = 0):
        if equip_id == 0:
            return 0

        if type(equip_id) is str:
            equip_id = int(equip_id)

        target_equip = next((x for x in cls.json_obj['api_mst_slotitem'] if x["api_id"] == equip_id), None)

        if not target_equip:
            Printf(f'[Warning] Equip id {equip_id} not in json_obj, length: {len(cls.json_obj)}', color_str='35m')
            return default_val

        return target_equip['api_type'][cls.ICON_ID_INDEX]

    @classmethod
    def get_slotitem_type_id_by_typename(cls, typename: str, equip_id: str = ''):
        for equip_type in cls.json_obj.get('api_mst_slotitem_equiptype', []):
            if equip_type['api_name'] == typename:
                return equip_type['api_id']
            
        for useitem in cls.json_obj.get('api_mst_useitem', []):
            if useitem['api_name'] == typename:
                return useitem['api_id']
            
        # for slotitem in cls.json_obj.get('api_mst_slotitem', []):
        #     if slotitem['api_name'] == typename:
        #         return slotitem['api_id']

        if equip_id:
            icon_id = cls.get_slotitem_type_id(equip_id, None)
            if icon_id is not None:
                return icon_id

        raise ValueError(f'[ERROR] {typename} not in EQUIP_ICON_ID')
        # import traceback
        # traceback.print_stack()
        # return default_val

    @classmethod
    def get_ship_id_by_name(cls, ship_name: str) -> int:
        for ship_info in cls.json_obj['api_mst_ship']:
            if ship_info['api_name'] == ship_name:
                return ship_info['api_id']
        
        return -1
    
    @classmethod
    def get_ship_name_by_id(cls, ship_id: int) -> str:
        for ship_info in cls.json_obj['api_mst_ship']:
            if ship_info['api_id'] == ship_id:
                return ship_info['api_name']
        
        return ''

    @classmethod
    def dump_start2_json(cls):
        with open(cls.START2_FILENAME, 'w', encoding='utf-8') as f:
            f.write(json.dumps(cls.json_obj, ensure_ascii=False, separators=(',', ':')))


# 虽然有Start2了但是仍旧用这个存取name_cache以保证一些奇怪的名字可以hold住(比如"日本艦")
class ShipInfoCache:
    name_cache = {}  # {ship_name: ship_id}

    @classmethod
    def get_id(cls, ship_name: str, default_val=None):
        if ship_name in cls.name_cache:
            return cls.name_cache[ship_name]
        
        if ship_start2_id := Start2DataHelper.get_ship_id_by_name(ship_name):
            return ship_start2_id

        Printf(f'[Warning] Ship name {ship_name} not in name_cache, length: {len(cls.name_cache)}', color_str='35m')
        return default_val

    @classmethod
    def set_id(cls, ship_name: str, ship_id: int):
        # Printf(f'Debug: Set {ship_name} ==> {ship_id}', color_str='90m')
        cls.name_cache[ship_name] = ship_id

    @classmethod
    def set_id_by_img_url(cls, ship_name: str, url: str):
        img_filename = url.split('/')[-1].split('.')[0]
        img_filename = re.sub(r'[A-Za-z]', '', img_filename)
        cls.set_id(ship_name, int(img_filename))
