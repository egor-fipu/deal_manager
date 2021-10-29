import os
from typing import Optional, List

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Body
from pydantic import BaseModel, Field

app = FastAPI()

load_dotenv()

B24_ID = os.getenv('B24_ID')
B24_KEY = os.getenv('B24_KEY')
URL = f'https://{B24_ID}.bitrix24.ru/rest/1/{B24_KEY}'

PRODUCTS = 'PRODUCTS'
DELIVERY_ADDRESS = 'DELIVERY_ADDRESS'
DELIVERY_DATE = 'DELIVERY_DATE'
DELIVERY_CODE = 'DELIVERY_CODE'
DEAL_USERFIELD = {
    PRODUCTS: f'UF_CRM_{PRODUCTS}',
    DELIVERY_ADDRESS: f'UF_CRM_{DELIVERY_ADDRESS}',
    DELIVERY_DATE: f'UF_CRM_{DELIVERY_DATE}',
    DELIVERY_CODE: f'UF_CRM_{DELIVERY_CODE}'
}
FIELDS_TO_CHECK = {
    f'UF_CRM_{PRODUCTS}': 'products',
    f'UF_CRM_{DELIVERY_ADDRESS}': 'delivery_adress',
    f'UF_CRM_{DELIVERY_DATE}': 'delivery_date',
}


class Contact(BaseModel):
    name: Optional[str]
    surname: Optional[str]
    phone: str = Field(..., min_length=11, max_length=12)
    adress: Optional[str]


class Deal(BaseModel):
    title: Optional[str]
    description: Optional[str]
    client: Contact
    products: List[str]
    delivery_adress: str
    delivery_date: str
    delivery_code: str = Field(..., min_length=12, max_length=12)


def add_deal_userfield(field_name, user_type_id='string'):
    data = {
        'fields': {'FIELD_NAME': field_name, 'USER_TYPE_ID': user_type_id}
    }
    requests.post(f'{URL}/crm.deal.userfield.add', json=data)


def delete_deal_userfield(field_id):
    requests.post(f'{URL}/crm.deal.userfield.delete', json={'id': field_id})


def check_deal_userfield():
    response = requests.post(f'{URL}/crm.deal.userfield.list')
    response_data = response.json()
    userfield_list = response_data.get('result')
    if userfield_list is not None:
        userfield_dict = {}
        for item in userfield_list:
            userfield_dict[item['FIELD_NAME']] = {
                'ID': item['ID'],
                'USER_TYPE_ID': item['USER_TYPE_ID']
            }
        for field, crm_field in DEAL_USERFIELD.items():
            if crm_field not in userfield_dict:
                add_deal_userfield(field)
            else:
                if userfield_dict[crm_field]['USER_TYPE_ID'] != 'string':
                    delete_deal_userfield(userfield_dict[crm_field]['ID'])
                    add_deal_userfield(field)
    else:
        raise Exception(response_data)


def search_contact(client):
    data = {
        'filter': {'PHONE': client.get('phone')},
        'select': ['ID', 'NAME', 'LAST_NAME', 'PHONE', 'ADDRESS']
    }
    response = requests.post(f'{URL}/crm.contact.list', json=data)
    response_data = response.json()
    return response_data['result']


def add_contact(client):
    data = {
        'FIELDS': {
            'NAME': client.get('name'),
            'LAST_NAME': client.get('surname'),
            'PHONE': [{'VALUE': client.get('phone'), 'VALUE_TYPE': 'WORK'}],
            'ADDRESS': client.get('adress'),
        }
    }
    response = requests.post(f'{URL}/crm.contact.add', json=data)
    response_data = response.json()
    if response_data.get('result'):
        new_contact = search_contact(client)
        return new_contact[0]
    else:
        return f'Ошибка добавления контакта: {response_data}'


def get_or_create_contact(client):
    contact = search_contact(client)
    if contact:
        return {'contact': contact[0], 'new': False}
    else:
        return {'contact': add_contact(client), 'new': True}


def search_deal(deal):
    data = {
        'filter': {DEAL_USERFIELD[DELIVERY_CODE]: deal.get('delivery_code')},
        'select': [
            'ID',
            'TITLE',
            'ADDITIONAL_INFO',
            'CONTACT_ID',
            DEAL_USERFIELD[DELIVERY_CODE],
            DEAL_USERFIELD[PRODUCTS],
            DEAL_USERFIELD[DELIVERY_ADDRESS],
            DEAL_USERFIELD[DELIVERY_DATE]
        ]
    }
    response = requests.post(f'{URL}/crm.deal.list', json=data)
    response_data = response.json()
    return response_data['result']


def add_deal(deal, contact_id):
    data = {
        'fields':
            {
                'TITLE': deal.get('title'),
                'ADDITIONAL_INFO': deal.get('description'),
                'CONTACT_ID': contact_id,
                DEAL_USERFIELD[PRODUCTS]: ', '.join(deal.get('products')),
                DEAL_USERFIELD[DELIVERY_ADDRESS]: deal.get('delivery_adress'),
                DEAL_USERFIELD[DELIVERY_DATE]: deal.get('delivery_date'),
                DEAL_USERFIELD[DELIVERY_CODE]: deal.get('delivery_code'),
            }
    }
    response = requests.post(f'{URL}/crm.deal.add', json=data)
    response_data = response.json()
    if response_data.get('result'):
        new_deal = search_deal(deal)
        return new_deal[0]
    else:
        return f'Ошибка добавления задачи: {response_data}'


def update_deal(field_to_update):
    response = requests.post(f'{URL}/crm.deal.update', json=field_to_update)
    response_data = response.json()
    return response_data


def check_update_deal(old_deal, new_deal):
    field_to_update = {
        'id': old_deal['ID'],
        'fields': {}
    }
    for old_field, new_field in FIELDS_TO_CHECK.items():
        if type(new_deal.get(new_field)) == list:
            new_deal[new_field] = ', '.join(new_deal[new_field])
        if (old_deal[old_field] != new_deal.get(new_field)
                and new_deal.get(new_field)):
            field_to_update['fields'][old_field] = new_deal.get(new_field)
    if field_to_update['fields']:
        result = update_deal(field_to_update)
        if result.get('result'):
            upd_deal = search_deal(new_deal)
            return upd_deal[0]
        return f'Ошибка обновления задачи: {result}'
    return old_deal


def add_or_update_deal(contact, old_deal, input_deal):
    if contact['new']:
        if old_deal:
            return {
                'contact': contact['contact'],
                'deal': 'Сделка с таким "delivery_code" уже есть у другого контакта'
            }
        new_deal = add_deal(input_deal, contact['contact']['ID'])
        return {'contact': contact['contact'], 'deal': new_deal}
    if old_deal:
        if contact['contact']['ID'] != old_deal[0]['CONTACT_ID']:
            return {'contact': contact['contact'], 'deal': 'Сделка с таким "delivery_code" уже есть у другого контакта'}
        upd_deal = check_update_deal(old_deal[0], input_deal)
        return {'contact': contact['contact'], 'deal': upd_deal}
    new_deal = add_deal(input_deal, contact['contact']['ID'])
    return {'contact': contact['contact'], 'deal': new_deal}


try:
    check_deal_userfield()
except Exception as err:
    raise Exception(f'Ошибка проверки пользовательских полей: {err}')


@app.post('/api/v1')
def main(deal: Deal = Body(...)):
    try:
        deal = deal.dict()
        contact = get_or_create_contact(deal.get('client'))
        old_deal = search_deal(deal)
        result = add_or_update_deal(contact, old_deal, deal)
        return result
    except Exception as err:
        return {'Ошибка': err}
