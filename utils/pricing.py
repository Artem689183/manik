from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceItem:
    id: str
    title: str
    price: int
    description: str


@dataclass(frozen=True)
class ServiceCategory:
    id: str
    title: str
    services: list[ServiceItem]


SERVICE_CATALOG: list[ServiceCategory] = [
    ServiceCategory(
        id="classic",
        title="Классический маникюр",
        services=[
            ServiceItem("hygiene", "Гигиенический маникюр", 1200, "Без покрытия"),
            ServiceItem("polish", "Маникюр + покрытие гель-лак", 2200, "Снятие старого включено"),
            ServiceItem("french", "Маникюр + френч", 2600, "Классический/цветной френч"),
            ServiceItem("top_master", "Маникюр top-master", 3000, "Приоритетная запись"),
        ],
    ),
    ServiceCategory(
        id="strengthening",
        title="Укрепление и коррекция",
        services=[
            ServiceItem("base", "Укрепление базой", 2400, "Для натуральных ногтей"),
            ServiceItem("gel", "Укрепление гелем", 2800, "Средняя длина"),
            ServiceItem("repair", "Ремонт 1 ногтя", 250, "Трещины/сколы"),
            ServiceItem("correction", "Коррекция покрытия", 2500, "До 4 недель"),
        ],
    ),
    ServiceCategory(
        id="extension",
        title="Наращивание",
        services=[
            ServiceItem("short", "Наращивание (короткая длина)", 3200, "До 1-2 длины"),
            ServiceItem("medium", "Наращивание (средняя длина)", 3700, "3-4 длина"),
            ServiceItem("long", "Наращивание (длинные ногти)", 4300, "От 5 длины"),
            ServiceItem("correction_ext", "Коррекция наращивания", 3400, "До 4 недель"),
        ],
    ),
    ServiceCategory(
        id="design",
        title="Дизайн",
        services=[
            ServiceItem("simple", "Мини-дизайн (до 2 ногтей)", 300, "Слайдеры, стемпинг"),
            ServiceItem("complex", "Сложный дизайн (10 ногтей)", 1200, "Роспись, микс техник"),
            ServiceItem("cat_eye", "Эффект cat eye / втирка", 600, "Доплата к покрытию"),
            ServiceItem("rhinestones", "Стразы/декор", 400, "Доплата к покрытию"),
        ],
    ),
]

NAIL_LENGTH_OPTIONS: list[tuple[str, str]] = [
    ("short", "Короткие"),
    ("medium", "Средние"),
    ("long", "Длинные"),
]

NAIL_SHAPE_OPTIONS: list[tuple[str, str]] = [
    ("square", "Квадрат"),
    ("oval", "Овал"),
    ("almond", "Миндаль"),
    ("stiletto", "Стилет"),
    ("soft_square", "Мягкий квадрат"),
]

COATING_OPTIONS: list[tuple[str, str]] = [
    ("none", "Без покрытия"),
    ("gel_polish", "Гель-лак"),
    ("hard_gel", "Твердый гель"),
    ("polygel", "Полигель"),
]


def get_price_list_html() -> str:
    lines = ["<b>Прайс</b>"]
    for category in SERVICE_CATALOG:
        lines.append(f"\n<b>{category.title}</b>")
        for service in category.services:
            lines.append(
                f"• {service.title} — <b>{service.price}₽</b>\n"
                f"  <i>{service.description}</i>"
            )
    return "\n".join(lines)


def get_category_by_id(category_id: str) -> ServiceCategory | None:
    return next((c for c in SERVICE_CATALOG if c.id == category_id), None)


def get_service_by_id(category_id: str, service_id: str) -> ServiceItem | None:
    category = get_category_by_id(category_id)
    if not category:
        return None
    return next((s for s in category.services if s.id == service_id), None)


def option_label(options: list[tuple[str, str]], option_id: str) -> str:
    return next((label for key, label in options if key == option_id), option_id)
