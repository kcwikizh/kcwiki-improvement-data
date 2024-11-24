import requests
from bs4 import BeautifulSoup
from utils import ImprovementCache, ItemDataHelper, ShipInfoCache

REQUEST_WEBSITE = 'https://akashi-list.me/'


# 获取网页并构建文档树
def get_equip_tree() -> BeautifulSoup | None:
    response = requests.get(REQUEST_WEBSITE)
    beautiful_soup = BeautifulSoup(response.content, "html.parser")

    return beautiful_soup


def get_equip_detail_page(equip_id: str):
    response = requests.get(REQUEST_WEBSITE + f'detail/w{equip_id}.html')
    beautiful_soup = BeautifulSoup(response.content, "html.parser")

    return beautiful_soup


def get_item_info(soup: BeautifulSoup):
    elements = soup.select('div.grid-view div#weapon-remodel div.weapon')
    print(f'获取到{len(elements)}个装备信息，尝试进行拉取……')
    for element in elements:
        # 装备ID
        equip_id = element['id'][1:]
        get_equip_detail(equip_id)
    print('读取完成')


def get_equip_detail(equip_id):
    if ImprovementCache.get_cache(equip_id) is not None:  # 已经获取过了
        return

    print(f'Get Equip: {equip_id}')

    # 获取装备详细页面
    equip_detail_soup = get_equip_detail_page(equip_id)

    if '改修不可' in str(equip_detail_soup):  # 不需要处理
        ImprovementCache.set_cache(equip_id, {})
        print(f'Equip {equip_id} has not improvement data.')
        return

    equip_name_obj = equip_detail_soup.select_one('div.name')
    # No.xxx
    equip_number_words = equip_name_obj.select_one('span.no').get_text().strip()
    # 装备名
    equip_name = equip_name_obj.select_one('span.wname').get_text().strip()
    # 装备类型名
    equip_typename = (equip_name_obj.get_text()
                      .replace(equip_name, '')
                      .replace(equip_number_words, '')
                      .replace('Wiki WikiEn', '').strip())
    # 装备图标ID
    try:
        equip_icon_id = ItemDataHelper.get_icon_id_by_typename(equip_typename, equip_id)
    except KeyError:
        raise ValueError(f'TypeName not found: {equip_name} -> {equip_typename}')

    # print(equip_id, equip_typename, equip_name, equip_icon_id)

    equip_info = {
        'id': int(equip_id),
        'id_str': equip_id,
        'type': equip_typename,
        'icon': equip_icon_id,
        'name': equip_name,
        'improvement': [],
    }

    # # # # # 装备改修信息 # # # # #
    try:
        improve_obj = equip_detail_soup.select_one(
            'div.detail-row div.resource-table:not([class~="consume-table"])').select('table tr')
    except AttributeError:  # 走到这里说明之前的“改修不可”没拦截到，实际上无法改修
        ImprovementCache.set_cache(equip_id, {})
        print(f'Equip {equip_id} has not improvement data, skip.')
        return

    # 0~5改修的资材和装备消耗
    improve_low_dev_cost = improve_low_dev_cost_sure = 0
    improve_low_screw_cost = improve_low_screw_cost_sure = 0
    improve_low_equip_cost_id = 0
    improve_low_equip_cost_name = ''
    improve_low_equip_cost_num = 0

    # 6~9改修的资材和装备消耗
    improve_high_dev_cost = improve_high_dev_cost_sure = 0
    improve_high_screw_cost = improve_high_screw_cost_sure = 0
    improve_high_equip_cost_id = 0
    improve_high_equip_cost_name = ''
    improve_high_equip_cost_num = 0

    improve_upgrade_cost = []  # 装备升级消耗 [(紫菜, 紫菜确保, 螺丝, 螺丝确保, 消耗装备ID, 消耗装备名, 消耗装备数量, [可升级此装备的舰娘])]
    improve_upgrade_target_equip = []  # [(equip_id, equip_name, equip_level), ...]

    # 新型兵装资材、详报等道具的消耗
    improve_low_item_cost_id = []
    improve_high_item_cost_id = []
    improve_upgrade_item_cost_id = []

    improve_low_item_cost_name = []
    improve_high_item_cost_name = []
    improve_upgrade_item_cost_name = []

    improve_low_item_cost_num = []
    improve_high_item_cost_num = []
    improve_upgrade_item_cost_num = []

    improve_resource_cost = []
    upgrade_secretary = []
    for obj in improve_obj:
        # 改修更新
        if 'upgrade' in obj.attrs.get('class', []):
            upgrade_equip = obj.select('td')[-1]
            # print(upgrade_equip)

            upgrade_equip_id = int(upgrade_equip.select_one('a')['href'][2:])
            upgrade_equip = upgrade_equip.get_text().split('★')
            upgrade_equip_name = upgrade_equip[0].strip()

            # 改修后的装备星级
            if len(upgrade_equip) > 1:
                upgrade_equip_level = int(upgrade_equip[1])
            else:
                upgrade_equip_level = 0

            improve_upgrade_target_equip.append((upgrade_equip_id, upgrade_equip_name, upgrade_equip_level))

            upgrade_secretary = []

        # 获取改修资源
        if resource_obj := obj.select_one('td.resource'):
            improve_resource_cost.append(int(resource_obj.select_one('span.ri-fuel').get_text()))
            improve_resource_cost.append(int(resource_obj.select_one('span.ri-ammo').get_text()))
            improve_resource_cost.append(int(resource_obj.select_one('span.ri-steel').get_text()))
            improve_resource_cost.append(int(resource_obj.select_one('span.ri-bauxite').get_text()))
            # print(improve_resource_cost)

        # 范围说明文本
        range_text_obj = obj.select_one('th')
        if not range_text_obj:
            continue

        range_text = range_text_obj.get_text()
        if range_text in ['改修必要資材', '★']:  # 表头的文字跳过处理
            continue

        if range_text in ['0 ～ 5', '0 ~ 5']:  # 低级改修
            (improve_low_dev_cost, improve_low_dev_cost_sure,
             improve_low_screw_cost, improve_low_screw_cost_sure,
             improve_low_equip_cost_id, improve_low_equip_cost_name, improve_low_equip_cost_num) = get_improve_cost(
                equip_id, improve_low_item_cost_id, improve_low_item_cost_name, improve_low_item_cost_num, obj)

        elif range_text in ['6 ～ 9', '6 ~ 9']:  # 高级改修
            (improve_high_dev_cost, improve_high_dev_cost_sure,
             improve_high_screw_cost, improve_high_screw_cost_sure,
             improve_high_equip_cost_id, improve_high_equip_cost_name,
             improve_high_equip_cost_num) = get_improve_cost(
                equip_id, improve_high_item_cost_id, improve_high_item_cost_name, improve_high_item_cost_num, obj)

        elif range_text in ['MAX', 'Max', 'max']:  # TODO: remodel-info
            improve_upgrade_cost.append(get_improve_cost(
                equip_id, improve_upgrade_item_cost_id, improve_upgrade_item_cost_name,
                improve_upgrade_item_cost_num, obj) + (upgrade_secretary,))

        elif '二番艦指定' in range_text:
            upgrade_secretary = range_text.replace('二番艦指定', '').strip().split('・')
        elif range_text == '':
            continue
        else:
            raise ValueError(f'Except text: {range_text}')

    # print(improve_upgrade_cost, improve_upgrade_target_equip)

    # 秘书舰信息
    improve_supporter_obj = equip_detail_soup.select_one('div.detail-row div.support-ship-table').select(
        'table td div.support-ship')
    supporter_list = []  # [ship_id, weekday_enable]
    # print(improve_supporter_obj)
    for support_ship in improve_supporter_obj:
        img_obj = support_ship.select_one('img')

        if img_obj is not None:  # 避开12.7cm连装炮等是个船就能敲的情况
            if 'src' in img_obj.attrs:
                img_url = img_obj['src']
            elif 'data-src' in img_obj.attrs:
                img_url = img_obj['data-src']
            else:
                raise ValueError(f'img url not found: {img_obj}')

        weekday_enable = ['enable' in x.attrs.get('class', []) for x in support_ship.select('div.weeks span')]
        # print(weekday_enable)

        # 移除改修日期文本
        support_ship.select_one('div.weeks').decompose()
        ship_name = support_ship.get_text()

        if img_obj is not None:
            ShipInfoCache.set_id_by_img_url(ship_name, img_url)
            ship_id = ShipInfoCache.get_id(ship_name)

            supporter_list.append((ship_id, weekday_enable))
        else:
            supporter_list.append((0, weekday_enable))

    # 开始组装改修信息
    if len(improve_upgrade_target_equip) == 0:  # 如果没有装备可以更新
        improve_upgrade_target_equip.append((0, '', 0))

    for i in range(len(improve_upgrade_target_equip)):
        target_equip = improve_upgrade_target_equip[i]

        # 升级信息
        improve_info = {'upgrade': {}}
        improve_info['upgrade']['level'] = target_equip[2]
        improve_info['upgrade']['id'] = target_equip[0]
        improve_info['upgrade']['name'] = target_equip[1]
        improve_info['upgrade']['icon'] = ItemDataHelper.get_icon_id(target_equip[0])  # TODO: 暂时没办法拿到

        # 秘书舰信息
        req_dict = {}  # {weekday_enable: req}
        for support_ship_id, weekday_enable in supporter_list:
            weekday_hash = sum([1 << i for i in range(len(weekday_enable)) if weekday_enable[i]])
            if weekday_hash in req_dict:
                req_dict[weekday_hash]['secretary'].append(ShipInfoCache.get_name(support_ship_id))
                req_dict[weekday_hash]['secretaryIds'].append(support_ship_id)
                continue

            req_dict[weekday_hash] = {
                "day": weekday_enable,
                "secretary": [ShipInfoCache.get_name(support_ship_id)],
                "secretaryIds": [support_ship_id],
            }
        improve_info['req'] = list(req_dict.values())

        # 资源需求信息
        improve_info['consume'] = {}
        improve_info['consume']['fuel'] = improve_resource_cost[0]
        improve_info['consume']['ammo'] = improve_resource_cost[0]
        improve_info['consume']['steel'] = improve_resource_cost[0]
        improve_info['consume']['bauxite'] = improve_resource_cost[0]
        improve_info['consume']['material'] = [
            {
                "development": [improve_low_dev_cost, improve_low_dev_cost_sure],
                "improvement": [improve_low_screw_cost, improve_low_screw_cost_sure],
                "item": {
                    "icon": ItemDataHelper.get_icon_id(improve_low_equip_cost_id),
                    "name": improve_low_equip_cost_name,
                    "id": improve_low_equip_cost_id,
                    "count": improve_low_equip_cost_num,
                }
            },
            {
                "development": [improve_high_dev_cost, improve_high_dev_cost_sure],
                "improvement": [improve_high_screw_cost, improve_high_screw_cost_sure],
                "item": {
                    "icon": ItemDataHelper.get_icon_id(improve_high_equip_cost_id),
                    "name": improve_high_equip_cost_name,
                    "id": improve_high_equip_cost_id,
                    "count": improve_high_equip_cost_num,
                }
            }
        ]

        if len(improve_upgrade_cost) > 0:
            improve_upgrade_dev_cost, improve_upgrade_dev_cost_sure, improve_upgrade_screw_cost, improve_upgrade_screw_cost_sure, improve_upgrade_equip_cost_id, improve_upgrade_equip_cost_name, improve_upgrade_equip_cost_num, upgrade_secretary = \
                improve_upgrade_cost[i]

            if improve_upgrade_dev_cost == improve_upgrade_dev_cost_sure == improve_upgrade_screw_cost == improve_upgrade_screw_cost_sure == 0:
                pass
            else:
                improve_info['consume']['material'].append({
                    "development": [improve_upgrade_dev_cost, improve_upgrade_dev_cost_sure],
                    "improvement": [improve_upgrade_screw_cost, improve_upgrade_screw_cost_sure],
                    "item": {
                        "icon": ItemDataHelper.get_icon_id(improve_upgrade_equip_cost_id),
                        "name": improve_upgrade_equip_cost_name,
                        "id": improve_upgrade_equip_cost_id,
                        "count": improve_upgrade_equip_cost_num,
                    }
                })

        if len(improve_low_item_cost_id) > 0:
            improve_info['consume']['material'][0]['useitem'] = []
            fill_useitem(improve_info['consume']['material'][0]['useitem'],
                         improve_low_item_cost_id,
                         improve_low_item_cost_name,
                         improve_low_item_cost_num)

        if len(improve_high_item_cost_id) > 0:
            improve_info['consume']['material'][1]['useitem'] = []
            fill_useitem(improve_info['consume']['material'][1]['useitem'],
                         improve_high_item_cost_id,
                         improve_high_item_cost_name,
                         improve_high_item_cost_num)

        if len(improve_info['consume']['material']) > 2 and len(improve_upgrade_item_cost_id) > 0:
            improve_info['consume']['material'][2]['useitem'] = []
            fill_useitem(improve_info['consume']['material'][2]['useitem'],
                         improve_upgrade_item_cost_id,
                         improve_upgrade_item_cost_name,
                         improve_upgrade_item_cost_num)

        equip_info['improvement'].append(improve_info)
        # print(equip_info)
        print(f'Get equip improvement info success: {equip_id}')
        ImprovementCache.set_cache(equip_id, equip_info)


def fill_useitem(useitem_info, cost_id, cost_name, cost_num):
    for a in range(len(cost_id)):
        useitem_info.append({
            "icon": ItemDataHelper.get_icon_id(cost_id[a]),
            "name": cost_name[a],
            "id": cost_id[a],
            "count": cost_num[a],
        })


def get_improve_cost(equip_id, item_cost_id_list, item_cost_name_list, item_cost_num_list, obj):
    # 资材消耗
    dev_cost_text = obj.select('td')[0].get_text()
    if dev_cost_text in ('-', ''):
        dev_cost = dev_cost_sure = 0
    else:
        dev_cost, dev_cost_sure = [int(x.strip()) for x in dev_cost_text.split('/')]

    # 螺丝消耗
    screw_cost_text = obj.select('td')[1].get_text()
    if screw_cost_text in ('-', ''):
        screw_cost = screw_cost_sure = 0
    else:
        screw_cost, screw_cost_sure = [int(x.strip()) for x in screw_cost_text.split('/')]

    if dev_cost == dev_cost_sure == screw_cost == screw_cost_sure == 0:  # 基本上是没MAX改修的，后面不用处理
        return dev_cost, dev_cost_sure, screw_cost, screw_cost_sure, 0, '', 0

    # 装备消耗
    equip_cost_id = 0
    equip_cost_name = ''
    equip_cost_num = 0

    # 检查装备消耗
    if obj.select('td')[2].get_text() != '-':
        # print('[DEBUG]', obj)
        try:
            equip_cost_id = int(obj.select('td')[2].select_one('td.resource-img a')['href'][2:])
        except (KeyError, TypeError, ValueError):  # 如果装备素材是吃自己的话没有<a>标签
            equip_cost_id = int(equip_id)

        # 检查是否有辅助材料(新型兵装资材etc.)
        equip_cost_name = equip_cost_num = None
        main_equip_cost = obj.select('td')[2]
        sub_item_list = main_equip_cost.select('div a.nodec')

        if len(sub_item_list) == 0 and main_equip_cost.get_text().count(u'×') > 1:  # 一些老道具没有nodec节点，这么处理
            sub_item_list = main_equip_cost.select('div a')
            # print(main_equip_cost)
            try:
                name, count = [x.strip() for x in sub_item_list[0].get_text().split(u'×')]
                equip_cost_name = name
                equip_cost_num = int(count)
                sub_item_list[0].decompose()
            except ValueError:  # 处理装备素材是吃自己的话不带<a>的问题
                second_div_index = main_equip_cost.contents.index(main_equip_cost.select('div')[1])

                cost_obj = main_equip_cost.contents[second_div_index - 1]
                name, count = [x.strip() for x in cost_obj.get_text().split(u'×')]
                equip_cost_name = name
                equip_cost_num = int(count)

                # 清空第二个<div>之前的内容
                main_equip_cost.contents = main_equip_cost.contents[second_div_index:]

            sub_item_list = sub_item_list[1:]

        if len(sub_item_list) > 0:
            for sub_item in sub_item_list:
                # print('Subitem:', sub_item)
                try:
                    if 'title' in sub_item:
                        item_cost_id_list.append(ItemDataHelper.get_icon_id_by_typename(sub_item['title']))
                        item_cost_name_list.append(sub_item['title'])
                        item_cost_num_list.append(int(sub_item.get_text().replace(u'×', '').strip()))

                    else:
                        name_text = sub_item.get_text().split(u'×')
                        if len(name_text) >= 2:
                            name, count = name_text
                        else:
                            name, count = obj.select_one('td.resource-img').get_text().split(u'×')

                        item_cost_id_list.append(0)
                        item_cost_name_list.append(name.strip())
                        item_cost_num_list.append(int(count.strip()))

                    sub_item.decompose()  # 删除自己避免影响后面判断
                except KeyError:
                    raise ValueError(f'TypeName not found: {sub_item}')
                except Exception as e:
                    print('[ERROR]', obj.select('td')[2].get_text())
                    raise e

        if equip_cost_name is None:
            try:
                name, count = [x.strip() for x in main_equip_cost.get_text().split(u'×')]
                equip_cost_name = name
                equip_cost_num = int(count)

            except IndexError:  # 处理装备素材是吃自己的话不带<a>的问题
                name, count = [x.strip() for x in obj.select('td')[2].get_text().split(u'×')]
                equip_cost_name = name
                equip_cost_num = int(count)

    return dev_cost, dev_cost_sure, screw_cost, screw_cost_sure, equip_cost_id, equip_cost_name, equip_cost_num


if __name__ == '__main__':
    ImprovementCache.read_file()
    soup_obj = get_equip_tree()
    get_item_info(soup_obj)
