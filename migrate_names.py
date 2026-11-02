#!/usr/bin/env python3
"""
Migrate card names:
- Split "Translit (English)" into name (translit) + name_en
- Add name_ru (Cyrillic)
- Replace self-references in text with <this>
- Same for back_face names
"""

import re
import yaml
from pathlib import Path

ROOT = Path(__file__).parent
CARDS_DIR = ROOT / "cards"

# Full lookup: translit name -> Cyrillic
# For cards with parens: key = translit part only
RU = {
    # common/black
    "Navka": "Навка",
    "Upyr": "Упырь",
    "Starukha-Vedma": "Старуха-Ведьма",
    "Mertvets iz Navi": "Мертвец из Нави",
    "Chert Melkiy": "Чёрт Мелкий",
    "Nochnaya Mara": "Ночная Мара",
    "Kladbishchenskiy Storozh": "Кладбищенский Сторож",
    "Drekavats": "Дрекавац",
    "Kladbishchenskiy vor": "Кладбищенский Вор",
    "Trup Ozhivshiy": "Труп Ожившый",
    "Sglaz": "Сглаз",
    "Pominki": "Поминки",
    "Ne Oglyadyvaisya": "Не Оглядывайся",
    "Holodnaya Zemlya": "Холодная Земля",
    "Noch Proderzhatsa": "Ночь Продержаться",
    "Kikimora": "Кикимора",
    "Ne svisti": "Не свисти",
    "Zakladnaya Chertu": "Заклад Чёрту",
    "Topkoye mesto": "Топкое Место",
    # common/blue
    "Kupets na Pristani": "Купец на Пристани",
    "Rusalka-Iskusitelnitsa": "Русалка-Искусительница",
    "Chudo-Rybka": "Чудо-Рыбка",
    "Lebed Belaya": "Лебедь Белая",
    "Gusi-Lebedi": "Гуси-Лебеди",
    "Utoplennik": "Утопленник",
    "Korabl Kupecheskiy": "Корабль Купеческий",
    "Vodyanitsa": "Водяница",
    "Starik-Rybak": "Старик-Рыбак",
    "Morskoy Kon": "Морской Конь",
    "Rechnoy Tuman": "Речной Туман",
    "Bluddyechko s Yablochkom": "Блюдечко с Яблочком",
    "Zov Morya": "Зов Моря",
    "Veschiy Son": "Вещий Сон",
    "Obman Zreniya": "Обман Зрения",
    "Otplyitye": "Отплытие",
    "V Bochke po Moryu": "В Бочке по Морю",
    "Treskuchiy Moroz": "Трескучий Мороз",
    "Starinnaya Letopis": "Старинная Летопись",
    # common/colorless
    "Lapot Samokhodny": "Лапоть Самоходный",
    "Samobranka": "Самобранка",
    "Volshebnoe Zerkaltse": "Волшебное Зеркальце",
    "Klubochek": "Клубочек",
    "Gorshochek Kashi": "Горшочек Каши",
    "Dubinka Samoboyka": "Дубинка Самобойка",
    # common/green
    "Medved-Shatun": "Медведь-Шатун",
    "Lisitsa-Khitryuga": "Лисица-Хитрюга",
    "Zayats-Beglets": "Заяц-Беглец",
    "Dub Vekovoy": "Дуб Вековой",
    "Sery Volk": "Серый Волк",
    "Yablonka Dobraya": "Яблонька Добрая",
    "Babushkina Koshka": "Бабушкина Кошка",
    "Lesnoy Starichok": "Лесной Старичок",
    "Voron-Vestnik": "Ворон-Вестник",
    "Turoviy Byk": "Туровий Бык",
    "Zhivaya Voda": "Живая Вода",
    "Lesnaya Tropa": "Лесная Тропа",
    "Priyut Leshego": "Приют Лешего",
    "Medovy Sbiten": "Медовый Сбитень",
    "Sokhatyy": "Сохатый",
    "Rys": "Рысь",
    "Bogatyrskaya Sila": "Богатырская Сила",
    "Muravyinaya Blagodarnost": "Муравьиная Благодарность",
    "Sekretnyy Posvist": "Секретный Посвист",
    # common/red
    "Udaloy Molodets": "Удалой Молодец",
    "Kuznets": "Кузнец",
    "Gorynychevo Otrodye": "Горыничево Отродье",
    "Okhrabrevshiy Mujik": "Осмелевший Мужик",
    "Sivka-Burka": "Сивка-Бурка",
    "Samokhodnaya Pech": "Самоходная Печь",
    "Razboynik s Bolshoy Dorogi": "Разбойник с Большой Дороги",
    "Kyyryy Oyuun": "Кыыр Ойуун",
    "Pugach": "Пугач",
    "Udal Molodetskaya": "Удаль Молодецкая",
    "Grom i Molniya": "Гром и Молния",
    "Po shuchyemu veleniyu": "По щучьему велению",
    "Klich Bogatyrskiy": "Клич Богатырский",
    "Tantsy vokrug Kostra": "Танцы вокруг Костра",
    "Ne Slezay s Konya": "Не Слезай с Коня",
    "Ukrast Tsarevnu": "Украсть Царевну",
    "Pechenegi": "Печенеги",
    "Polovtsy": "Половцы",
    "Stepnoy Pozhar": "Степной Пожар",
    "Nochnoy Nabeg": "Ночной Набег",
    # common/white
    "Pakhar": "Пахарь",
    "Kalika Perekhozhiy": "Калика Перехожий",
    "Derevenskiy Starosta": "Деревенский Староста",
    "Vityaz Storozhevoy": "Витязь Сторожевой",
    "Derevenskaya Devitsa": "Деревенская Девица",
    "Pogranichnaya Zastava": "Пограничная Застава",
    "Pastva Vernykh": "Паства Верных",
    "Konny Druzhinnnik": "Конный Дружинник",
    "Svetly Otrok": "Светлый Отрок",
    "Monastyrsky Kot": "Монастырский Кот",
    "Blagoslovenie": "Благословение",
    "Krestniy Khod": "Крестный Ход",
    "Utrenniy Zvon": "Утренний Звон",
    "Den Prostoyat": "День Простоять",
    "Proshcheniye": "Прощение",
    "Obraza na Shitah": "Образа на Щитах",
    "Ratnik": "Ратник",
    "Voyevoda": "Воевода",
    "Postrig": "Постриг",
    # rare/black
    "Koschei Bessmertny": "Кощей Бессмертный",
    "Marya Morevna": "Марья Моревна",
    "Pannochka": "Панночка",
    "Vedma iz Groba": "Ведьма из Гроба",
    "Chernaya Kniga": "Чёрная Книга",
    "Proklyatiye Roda": "Проклятие Рода",
    "Ne Ver Mertvym": "Не Верь Мёртвым",
    "Smert Koscheyeva": "Смерть Кощеева",
    # rare/blue
    "Tsar Morskoy": "Царь Морской",
    "Chudo-Yudo Ryba-Kit": "Чудо-Юдо Рыба-Кит",
    "Ucheniy Kot": "Учёный Кот",
    "Morskaya Tsarevna": "Морская Царевна",
    "Ne Govori Ni Slova": "Не Говори Ни Слова",
    "Prinesi To Ne Znayu Chto": "Принеси То Не Знаю Что",
    # rare/colorless
    "Yayco Koscheya": "Яйцо Кощея",
    "Sapogi-Skorokhody": "Сапоги-Скороходы",
    "Yagina Stupa": "Ягина Ступа",
    # rare/green
    "Baba Yaga": "Баба Яга",
    "Leshiy, Khozyain Lesa": "Леший, Хозяин Леса",
    "Konek-Gorbunok": "Конёк-Горбунок",
    "Khozyaika Mednoy Gory": "Хозяйка Медной Горы",
    "Svyashennoye Derevo": "Священное Дерево",
    "Spasti Bratsa": "Спасти Братца",
    # rare/lands
    "Kitezh-Grad": "Китеж-Град",
    "Ostrov Buyan": "Остров Буян",
    "Kalinov Most": "Калинов Мост",
    "Pole Brani": "Поле Брани",
    "Dremuchy Les": "Дремучий Лес",
    # rare/multicolor
    "Ivan Tsarevich": "Иван Царевич",
    "Ivan Durak": "Иван Дурак",
    "Vasilisa Premudraya": "Василиса Премудрая",
    "Dobrynya i Zmei": "Добрыня и Змей",
    "Sadko, Gost Bogatiy": "Садко, Гость Богатый",
    "Tsarevna Lebed": "Царевна Лебедь",
    "Chernomor": "Черномор",
    "Ruslan": "Руслан",
    "Vodyanoy Tsar": "Водяной Царь",
    "Poloz, Velikiy Zmei Urala": "Полоз, Великий Змей Урала",
    "Morozko, Dyed Moroz": "Морозко, Дед Мороз",
    # rare/red
    "Zmei Gorynych": "Змей Горыныч",
    "Alyosha Popovich": "Алёша Попович",
    "Zhar-Ptitsa": "Жар-Птица",
    "Tugarin Zmeyevich": "Тугарин Змеевич",
    "Ne Tushy Kostyor": "Не Туши Костёр",
    "Razbey Razboynikov": "Разбей Разбойников",
    # rare/white
    "Ilya Muromets": "Илья Муромец",
    "Knyaz Vladimir Krasno Solnyshko": "Князь Владимир Красно Солнышко",
    "Vasilisa Prekrasnaya": "Василиса Прекрасная",
    "Zastava Bogatyrskaya": "Застава Богатырская",
    "Iskupatsa v Kipyatke": "Искупаться в Кипятке",
    # uncommon/black
    "Viy": "Вий",
    "Mara-Nochnitsa": "Мара-Ночница",
    "Koscheyev Prisluzhnik": "Кощеев Прислужник",
    "Nochnoy Vsadnik": "Ночной Всадник",
    "Proklyanaya Knyaginya": "Проклятая Княгиня",
    "Prizrak Knyagini": "Призрак Княгини",
    "Mogilinschik": "Могильщик",
    "Proklyatiye Koscheyevo": "Проклятие Кощеево",
    "Pogrebalniy Obriad": "Погребальный Обряд",
    "Ne Otkryvay Sunduk": "Не Открывай Сундук",
    "Ispytaniye Lesa": "Испытание Леса",
    "Podzemnoye Tsarstvo": "Подземное Царство",
    # uncommon/blue
    "Sadko-Kupets": "Садко-Купец",
    "Vodyanoy": "Водяной",
    "Mechtatelniy Kupets": "Мечтательный Купец",
    "Ledyanoy Dukh": "Ледяной Дух",
    "Morskaya Puchina": "Морская Пучина",
    "Ledyanoy Vihr": "Ледяной Вихрь",
    "Ne Beri Chuzhogo": "Не Бери Чужого",
    "Morozko": "Морозко",
    # uncommon/colorless
    "Mech-Kladenets": "Меч-Кладенец",
    "Shapka-Nevidimka": "Шапка-Невидимка",
    "Gusli-Samogudy": "Гусли-Самогуды",
    "Letuchiy Korabl": "Летучий Корабль",
    # uncommon/green
    "Leshiy": "Леший",
    "Mishka Kosolapy": "Мишка Косолапый",
    "Zhivaya i Mortvaya Voda": "Живая и Мёртвая Вода",
    "Zapovednaya Polyana": "Заповедная Поляна",
    "Urozhay": "Урожай",
    "Naydi Tsvetok Paporotnika": "Найди Цветок Папоротника",
    # uncommon/lands
    "Rasputye": "Распутье",
    "Pristan": "Пристань",
    "Kapishche": "Капище",
    "Zastava": "Застава",
    "Opushka": "Опушка",
    "Gornaya Reka": "Горная Река",
    "Lesnoy Rodnik": "Лесной Родник",
    "Grot": "Грот",
    "Pozharishche": "Пожарище",
    "Torfyannik": "Торфяник",
    # uncommon/multicolor
    "Letopisets iz Kitezha": "Летописец из Китежа",
    "Razkayavshiysya Greshnik": "Раскаявшийся Грешник",
    "Knyaz Druzhiny": "Князь Дружины",
    "Babka-Travnitsa": "Бабка-Травница",
    "Utoplennaya Nevesta": "Утопленная Невеста",
    "Emelya-Lezheboka": "Емеля-Лежебока",
    "Yaga-Ispytatelnista": "Яга-Испытательница",
    "Dedushka Lesnoy": "Дедушка Лесной",
    "Kochevoy Ataman": "Кочевой Атаман",
    "Tsarevna-Lyagushka": "Царевна-Лягушка",
    # uncommon/red
    "Dobrynya Nikitich": "Добрыня Никитич",
    "Vsadnik na Krasnom Kone": "Всадник на Красном Коне",
    "Zmeyonok": "Змеёнок",
    "Solovey-Razboynik": "Соловей-Разбойник",
    "Maslenitsa": "Масленица",
    "Zmeyeborstvo": "Змееборство",
    "Sukhovey": "Суховей",
    # uncommon/white
    "Boyan-Pevets": "Боян-Певец",
    "Zasadny Polk": "Засадный Полк",
    "Snegurochka": "Снегурочка",
    "Talaya Voda": "Талая Вода",
    "Dyak": "Дьяк",
    "Vsadnik na Belom Kone": "Всадник на Белом Коне",
    "Ispytanye Morozko": "Испытание Морозко",
    "Kupala Noch": "Купала Ночь",
    "Izgnanie Nechisti": "Изгнание Нечисти",
    "Kolokol Blagovest": "Колокол Благовест",
}


def split_name(full_name):
    """Split 'Translit (English)' -> (translit, english). Strips extra whitespace."""
    full_name = full_name.strip()
    m = re.match(r'^(.*?)\s*\(([^)]+)\)\s*$', full_name)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return full_name, full_name  # no parens -> translit == en


def replace_self_ref(text, old_full_name, translit):
    """Replace occurrences of the card's own name in its text with <this>."""
    if not text or not isinstance(text, str):
        return text
    # Try full name first (longest match), then translit
    result = text
    if old_full_name and old_full_name != translit:
        result = result.replace(old_full_name, "<this>")
    result = result.replace(translit, "<this>")
    return result


def process_face(face, old_full_name):
    """Process a single face dict: split name, add ru/en, replace self-refs."""
    old_name = face.get("name", "")
    translit, en = split_name(old_name)

    ru = RU.get(translit)
    if ru is None:
        print(f"  WARNING: no Cyrillic for '{translit}' (from '{old_name}')")
        ru = translit  # fallback

    face["name"] = translit
    face["name_ru"] = ru
    face["name_en"] = en

    # Replace self-references in text fields
    for field in ("text", "flavor_text"):
        if field in face and face[field]:
            face[field] = replace_self_ref(face[field], old_full_name or old_name, translit)

    return face


def save_cards(yaml_path, cards):
    class CustomDumper(yaml.SafeDumper):
        pass

    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        special = ':{}[],"\'#&*!|>%@`'
        if any(c in data for c in special):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    CustomDumper.add_representer(str, str_representer)

    with open(yaml_path, 'w') as f:
        yaml.dump(cards, f, Dumper=CustomDumper, default_flow_style=False,
                  allow_unicode=True, sort_keys=False, width=200)


def migrate_file(yaml_path, dry_run=False):
    with open(yaml_path) as f:
        cards = yaml.safe_load(f)
    if not cards or not isinstance(cards, list):
        return

    changed = False
    for card in cards:
        if not isinstance(card, dict):
            continue
        if "name_ru" in card:
            continue  # already migrated

        old_full_name = card.get("name", "")
        process_face(card, old_full_name)
        changed = True

        bf = card.get("back_face")
        if bf and isinstance(bf, dict) and "name_ru" not in bf:
            old_bf_name = bf.get("name", "")
            process_face(bf, old_bf_name)

    if changed and not dry_run:
        save_cards(yaml_path, cards)
        print(f"  Updated: {yaml_path.relative_to(ROOT)}")
    elif changed:
        print(f"  Would update: {yaml_path.relative_to(ROOT)}")


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN ===")

    for yaml_path in sorted(CARDS_DIR.rglob("*.yaml")):
        migrate_file(yaml_path, dry_run=dry_run)

    print("Done.")
