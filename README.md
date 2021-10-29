# deal_manager
Cкрипт для получения заявки с сайта в формате JSON и ее добавления/обновления в
Bitrix24

## Описание
Скрипт на языке Python, который получает POST-запросы с сайта в формате JSON и либо 
создает заявку, либо обновляет ее

### Возможные варианты:
- Контакта нет в Bitrix24 (далее b24) → создаем и контакт и сделку и связываем 
их между собой
- Контакт есть в b24 → Проверяем есть ли уже такая заявка по delivery_code
- Заявки нет в b24 → Создаем заявку и связываем ее с контактом
- Заявка есть в b24 → Сравниваем заявку из b24 с ключевыми полями 
(delivery_adress, delivery_date, products) из пришедшей заявки
- Поля совпадают → Ничего не делаем
- Поля отличаются → Обновляем заявку

### Входной JSON:
```
{
    "title": "title",
    "description": "Some description",
    "client": {
        "name": "Jon",
        "surname": "Karter",
        "phone": "+77777777777",
        "adress": "st. Mira, 287, Moscow"
    },
    "products": ["Candy", "Carrot", "Potato"],
    "delivery_adress": "st. Mira, 211, Ekaterinburg",
    "delivery_date": "2021-01-01:16:00",
    "delivery_code": "#232nkF3fAdn"
}
```

### Выходные данные:
- crm.deal - Сделка Bitrix24
- crm.contact - Контакт Bitrix24

### Условия:
- не должно быть дубликатов контакта и сделки
- контакт должен быть привязан к сделке
- заявки с одинаковым delivery_code должны объединяться, если это требуется
- в приоритете те данные, которые пришли позже
- информация о клиенте не изменяется, может измениться только: delivery_adress, delivery_date, products
- контакт ищем по номеру телефона

## Технологии
 - python 3.7
 - fastapi
 - uvicorn
 - requests
 - python-dotenv

## Запуск программы
- Установить и активировать виртуальное окружение
- Установить зависимости из файла requirements.txt
```
python -m pip install --upgrade pip

pip install -r requirements.txt
```
- Установить в файле '.env' ID аккаунта в Bitrix24 (B24_ID) и
секретный ключ для обращения к API Bitrix24 (B24_KEY)

- Выполнить команду:
```
python main.py
```

## Подробное описание
Для работы необходимо установить в файле '.env' ID аккаунта в Bitrix24 (B24_ID) и
секретный ключ для обращения к API Bitrix24 (B24_KEY)

После запуска осуществляется проверка пользовательских полей в 'crm.deal'. 
Запрашиваются имеющиеся пользовательские поля (crm.deal.userfield.list). Если поля,
установленные в словаре 'DEAL_USERFIELD', отсутствуют в 'crm.deal', то они создаются.
Если типы полей не совпадают, то имеющиеся в 'crm.deal' поля с несоответствующими 
типами удаляются, и создаются новые с необходимыми типами данных.

Эндпоинт 'http://127.0.0.1:8000/api/v1/' принимает POST-запросы в формате JSON.
1. При поступлении запроса, происходит проверка наличия обязательных полей в запросе:
'client', 'phone' клиента, 'delivery_code'. При их отсутствии вернется указывающее на это
сообщение
2. Проверяются данные клиента по полю 'phone'
   - если клиента нет в 'crm.contact', он создается, и возвращаются данные о созданном клиенте из 'crm.contact'
   - если есть, то возвращаются старые данные о клиенте из 'crm.contact'
3. Проверяются данные сделки по полю 'delivery_code'
   - если сделки нет в 'crm.deal', она создается с привязкой к клиенту при наличии обязательных полей,
установленных в словаре 'FIELDS_TO_CHECK': 'products', 'delivery_adress', 'delivery_date'.
Возвращаются данные о созданной сделке из 'crm.deal'
   - если есть, при наличии изменений в каком-либо из полей: 'products', 'delivery_adress', 
'delivery_date' - сделка обновляется, возвращаются обновленные данные из 'crm.deal'. Если
сделка не обновлялась, то возвращаются старые данные из 'crm.deal'.