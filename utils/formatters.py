def booking_message_html(
    user_id: int,
    full_name: str,
    phone: str,
    work_date: str,
    slot_time: str,
    service_name: str,
    service_price: int,
    nail_length: str,
    nail_shape: str,
    coating_type: str,
    comment: str,
) -> str:
    comment_html = comment if comment else "—"
    return (
        "<b>Новая запись</b>\n"
        f"Дата: <b>{work_date}</b>\n"
        f"Время: <b>{slot_time}</b>\n"
        f"Услуга: <b>{service_name}</b> ({service_price}₽)\n"
        f"Длина: <b>{nail_length}</b>\n"
        f"Форма: <b>{nail_shape}</b>\n"
        f"Покрытие: <b>{coating_type}</b>\n"
        f"Комментарий: <b>{comment_html}</b>\n"
        f"Имя: <b>{full_name}</b>\n"
        f"Телефон: <b>{phone}</b>\n"
        f"User ID: <code>{user_id}</code>"
    )


def day_schedule_html(work_date: str, schedule_rows: list[dict]) -> str:
    if not schedule_rows:
        return f"<b>Расписание на {work_date}</b>\nНет слотов."

    lines = [f"<b>Расписание на {work_date}</b>"]
    for row in schedule_rows:
        if row["booking_id"]:
            lines.append(
                f"• {row['slot_time']} — <b>занято</b> ({row['full_name']}, {row['phone']})"
            )
        else:
            lines.append(f"• {row['slot_time']} — свободно")
    return "\n".join(lines)


def channel_schedule_html(work_date: str, schedule_rows: list[dict]) -> str:
    lines = [f"<b>Обновленное расписание на {work_date}</b>"]
    if not schedule_rows:
        lines.append("Слоты отсутствуют.")
        return "\n".join(lines)

    for row in schedule_rows:
        status = "занято" if row["booking_id"] else "свободно"
        lines.append(f"• {row['slot_time']} — {status}")
    return "\n".join(lines)
