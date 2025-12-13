# Явный mapping-слой (адаптер) между полем TYPE в таблице public.users_topic
# (где будет указано "Индивидуальная"/"Парная" на русском языке)
# и полем PREFERRED_TOPIC_TYPE в таблице public.users_clientprofile (где указано "Individual"/"Couple" на английском)

CLIENT_TO_TOPIC_TYPE_MAP = {
    "individual": "Индивидуальная",
    "couple": "Парная",
}
