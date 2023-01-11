from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from .models import DMCConfigurations
from django.http import JsonResponse
import traceback
import jwt
import json
import requests
from django.core import serializers
from django.forms.models import model_to_dict
import os
import xml
from requests.auth import HTTPDigestAuth
from pprint import pprint
from pdf.models import Tenant
from enum import Enum


class QuestionType(Enum):
    INPUT = 'input'
    SELECT_SINGLE = 'select_single'
    SELECT_MULTIPLE = 'select_multi'
    UNKNOWN = 'unknown'


def return_response(final_data, error_code, error_text):
    """
    The function used to give response in all APIs

    Args:
        final_data:
        error_code:
        error_text:

    Returns:
        response

    """
    # Adding the response status code
    if error_code is None:
        status_code = 200
        response = JsonResponse({"data": final_data},
                                safe=False,
                                status=status_code)
    else:
        if error_code == 802:
            return JsonResponse({"error": [{
                "code": error_code,
                "message": error_text
            }]}, status=401)
        elif error_code == 500:
            return JsonResponse({"error": [{
                "code": error_code,
                "message": error_text
            }]}, status=500)
        else:
            response = JsonResponse(
                {"error": [{
                    "code": error_code,
                    "message": error_text
                }]},
                safe=False,
                status=error_code)
    return response


def checkAuthorization(request):
    if 'Authorization' in request.headers:
        try:
            return jwt.decode(request.headers['Authorization'].split(' ')[-1], os.environ.get('PUBLIC_KEY'), algorithms='RS256')
        except Exception as e:
            raise Exception('Invalid Authorization token provided')
    else:
        raise Exception('No Authorization token provided')


@csrf_exempt
@api_view(['GET', 'POST'])
def getAllConfigurations(request):
    final_data = []
    error_text = error_code = None
    try:
        token_data = checkAuthorization(request)
        if request.method == 'GET':
            configurations = DMCConfigurations.objects.all()
            final_data = [c.serialize() for c in configurations]
        elif request.method == 'POST':
            existing_user = Tenant.objects.filter(
                email=token_data['user']["email"]).first()
            if not existing_user:
                raise Exception('User not found in db')
            else:
                existing_user = json.loads(existing_user.google_token)

            data = json.loads(request.body)
            doc_id = data.get('doc_id')
            title = data.get('title')
            description = data.get('description')
            version = data.get('version')
            if not doc_id:
                raise Exception('Invalid doc_id')
            if not title:
                raise Exception('Title is required')
            if not version:
                raise Exception('Version is required')

            config_json = data.get('config')
            result = requests.post(f"{os.environ.get('DOC_GEN_URL')}/register/", headers={
                'GA-OAUTH-TOKEN': existing_user['access_token'],
                'GA-OAUTH-REFRESHTOKEN': existing_user['refresh_token'],
            }, json={
                'type': 'GOOGLE_DOC',
                'data': doc_id,
                'template_engine': 'JINJA',
            })

            result = json.loads(result.content)
            if 'error' in result:
                raise Exception('Failed to register template')
            configuration = DMCConfigurations.objects.create(
                template_id=result['data']['id'], user_email=token_data['user']['email'], config=config_json, title=title, description=description, version=version)
            configuration.save()
            final_data = configuration.serialize()
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)


def map_cols_to_cols_details(data):
    # fetch keys details
    key_list = set()
    key_list.update(
        map(lambda x: x['col1'], data['config']['mapping'].values()))
    key_list.update(
        map(lambda x: x['col2'], data['config']['mapping'].values()))
    key_list.remove(None)
    key_list = list(key_list)
    map_keys_to_type_and_choices(
        data['config']['form_id'], key_list)
    # replace col with col_details
    for k, v in data['config']['mapping'].items():
        if v['col1']:
            col1_details = list(
                filter(lambda x: x['name'] == v['col1'], key_list))
            v['col1'] = col1_details[0]
        if v['col2']:
            col2_details = list(
                filter(lambda x: x['name'] == v['col2'], key_list))
            v['col2'] = col2_details[0]


@csrf_exempt
@api_view(['GET', 'PUT', 'DELETE'])
def configurationOp(request, config_id):
    final_data = []
    error_text = error_code = None
    try:
        token_data = checkAuthorization(request)
        configuration = DMCConfigurations.objects.filter(pk=config_id).first()
        if not configuration:
            error_text = 'Not found'
            error_code = 404
        elif request.method == 'GET':
            final_data = configuration.serialize()
            req = requests.get(
                f"{os.getenv('TEMPLATOR_URL')}/{final_data['template_id']}")
            req.raise_for_status()
            final_data['template'] = req.json()['body']
        elif request.method == 'PUT':
            data = json.loads(request.body)
            if 'template_id' in data:
                configuration.template_id = data['template_id']
            if 'status' in data:
                choices = [x[1] for x in DMCConfigurations.STATUS_CHOICES]
                if not data['status'] in choices:
                    raise Exception('Invalid status: choices ' + str(choices))
                configuration.status = data['status']
            if 'config' in data:
                configuration.config = data['config']
                if 'form_id' in data['config'] and 'mapping' in data['config']:
                    map_cols_to_cols_details(data)
            configuration.save()
            final_data = configuration.serialize()
        elif request.method == 'DELETE':
            configuration.delete()
            final_data = configuration.serialize()
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)


@csrf_exempt
@api_view(['POST'])
def preview(request, config_id):
    final_data = []
    error_text = error_code = None
    try:
        token_data = checkAuthorization(request)
        data = json.loads(request.body)
        if not 'data' in data:
            raise Exception('data is required')
        configuration = DMCConfigurations.objects.filter(
            pk=config_id).first()
        if not configuration:
            error_text = 'Not found'
            error_code = 404
        elif request.method == 'POST':
            data = {
                "id": configuration.template_id,
                "data": data['data']
            }
            req = requests.post(
                f"{os.getenv('TEMPLATOR_URL')}/process", json=data)
            if req.status_code == 201:
                final_data = req.json()[
                    'processed'] if "processed" in req.json() else None
            else:
                req.raise_for_status()
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)


def getODKFormListing(host, user, pw):
    url = f'http://{host}/xformsList'
    auth = HTTPDigestAuth(user, pw)
    result = requests.get(url, headers={
        'Content-Type': 'text/xml; charset=utf-8'
    }, auth=auth)

    if result.status_code != 200:
        raise Exception('failed to fetch form listing')

    form_list = []
    DOMTree = xml.dom.minidom.parseString(result.text)
    forms = DOMTree.getElementsByTagName('xform')
    for form in forms:
        form_list.append({
            'form_id': form.getElementsByTagName('formID')[0].firstChild.data,
            'form_name': form.getElementsByTagName('name')[0].firstChild.data,
            'download_url': form.getElementsByTagName('downloadUrl')[0].firstChild.data,
        })
    return form_list


def getODKSingleForm(host, form_id, user, pw):
    url = f'http://{host}/xformsList?formID={form_id}'
    auth = HTTPDigestAuth(user, pw)
    result = requests.get(url, headers={
        'Content-Type': 'text/xml; charset=utf-8'
    }, auth=auth)

    if result.status_code != 200:
        raise Exception('failed to fetch form of form id ' + form_id)

    DOMTree = xml.dom.minidom.parseString(result.text)
    download_url = DOMTree.getElementsByTagName('downloadUrl')
    if not download_url:
        raise Exception('form not found')

    download_url = download_url[0].firstChild.data
    resp = requests.get(download_url, headers={
        'Content-Type': 'text/xml; charset=utf-8'
    }, auth=auth)

    if resp.status_code != 200:
        raise Exception('failed to fetch form of form id ' + form_id)

    return resp.text


@csrf_exempt
@api_view(['GET'])
def getODKForms(request):
    final_data = []
    error_text = error_code = None

    try:
        token_data = checkAuthorization(request)
        host = os.environ.get('ODK_HOST')
        username = os.environ.get('ODK_USERNAME')
        password = os.environ.get('ODK_PASSWORD')
        final_data = getODKFormListing(host, username, password)
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)


def getNthNodesName(node, container):
    # skip jr:template
    # only element nodes will come in recursive calls
    if node.hasAttribute('jr:template'):
        return

    if node.childNodes:
        # node with only text in it
        if len(node.childNodes) == 1 and node.childNodes[0].nodeType == node.childNodes[0].TEXT_NODE:
            container.append(node.nodeName)
            return

        for child in node.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                getNthNodesName(child, container)
    else:
        container.append(node.nodeName)


def getElementsById(node, id, container):
    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            getElementsById(child, id, container)

    if node.nodeType == node.ELEMENT_NODE and node.hasAttribute('id') and node.getAttribute('id') == id:
        container.append(node)


def getElementByRef(node, ref, container):
    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            getElementByRef(child, ref, container)

    if node.nodeType == node.ELEMENT_NODE and node.hasAttribute('ref'):
        part_ref = node.getAttribute('ref').split('/')
        if (part_ref[-1] if part_ref else node.getAttribute('ref')) == ref:
            container.append(node)


def getElementChoices(node, key_name, document):
    container = {}
    # finding keys
    for value_node in node.getElementsByTagName('value'):
        for child in value_node.childNodes:
            if child.nodeType == child.TEXT_NODE:
                container[child.data] = child.data
    # finding values of that key
    for k, v in container.items():
        for ele in document.getElementsByTagName('text'):
            if ele.hasAttribute('id') and ele.getAttribute('id').split('/')[-2] == key_name and ele.getAttribute('id').split('/')[-1] == f'{k}:label':
                child = ele.getElementsByTagName('value')[0].firstChild
                container[k] = child.data
    return container


def map_keys_to_type_and_choices(form_id, key_list):
    host = os.environ.get('ODK_HOST')
    username = os.environ.get('ODK_USERNAME')
    password = os.environ.get('ODK_PASSWORD')
    form = getODKSingleForm(host, form_id, username, password)
    DOMTree = xml.dom.minidom.parseString(form)
    # column type and choices mapping
    for i, item in enumerate(key_list):
        temp = []
        getElementByRef(DOMTree, item, temp)
        if temp:
            ele = temp[0]
            if ele.nodeName == 'input':
                key_list[i] = {
                    'name': item,
                    'type': QuestionType.INPUT.value,
                }
            elif ele.nodeName == 'select1':
                choices = getElementChoices(ele, item, DOMTree)
                key_list[i] = {
                    'name': item,
                    'type': QuestionType.SELECT_SINGLE.value,
                    'choices': choices
                }
            elif ele.nodeName == 'select':
                choices = getElementChoices(ele, item, DOMTree)
                key_list[i] = {
                    'name': item,
                    'type': QuestionType.SELECT_MULTIPLE.value,
                    'choices': choices
                }
            else:
                key_list[i] = {
                    'name': item,
                    'type': QuestionType.UNKNOWN.value,
                }
        else:
            key_list[i] = {
                'name': item,
                'type': QuestionType.UNKNOWN.value,
            }


@csrf_exempt
@api_view(['GET'])
def parseODKForm(request, form_id):
    final_data = []
    error_text = error_code = None

    try:
        token_data = checkAuthorization(request)
        host = os.environ.get('ODK_HOST')
        username = os.environ.get('ODK_USERNAME')
        password = os.environ.get('ODK_PASSWORD')
        form = getODKSingleForm(host, form_id, username, password)
        DOMTree = xml.dom.minidom.parseString(form)

        # get element with id = formid
        data = []
        getElementsById(DOMTree, form_id, data)
        if not data:
            raise Exception('odk form is not valid')

        container = []
        if data[0].childNodes:
            getNthNodesName(data[0], container)

        # repeat nodes
        for child in DOMTree.getElementsByTagName('repeat'):
            nodeset_attr = child.getAttribute('nodeset').split('/')
            if nodeset_attr:
                container.append(nodeset_attr[-1])

        map_keys_to_type_and_choices(form_id, container)
        final_data = container
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)


@csrf_exempt
@api_view(['POST'])
def login(request):
    final_data = []
    error_text = error_code = None
    body = json.loads(request.body)

    try:
        if not 'code' in body:
            raise Exception('Authorization code is required')

        url = "https://oauth2.googleapis.com/token"
        payload = {
            'code': body['code'],
            'client_id': os.getenv('GC_CLIENT_ID'),
            'client_secret': os.getenv('GC_CLIENT_SECRET'),
            'redirect_uri': os.getenv('DMC_GC_REDIRECT_URL'),
            'grant_type': 'authorization_code'
        }
        response = requests.post(url, json=payload)
        data = response.json()

        if 'error' in data:
            error_code = 400
            error_text = data['error']
        else:
            decoded = decode_id_token(data['id_token'])
            user = Tenant.objects.filter(email=decoded["email"]).first()
            if user:
                google_token = {**json.loads(user.google_token), **data}
                user.name = decoded["name"]
                user.email = decoded["email"]
                user.google_token = json.dumps(google_token)
                user.save()
            else:
                user = Tenant.objects.create(
                    name=decoded["name"], email=decoded["email"], google_token=json.dumps(data))

            jwt_data = {
                'user': {
                    'name': decoded['name'],
                    'email': decoded['email'],
                }
            }

            final_data = jwt.encode(jwt_data, os.environ.get(
                'PRIVATE_KEY'), algorithm="RS256")
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)


def decode_id_token(jwttoken):
    url = "https://www.googleapis.com/oauth2/v3/certs"
    client = jwt.PyJWKClient(url)
    pub_key = client.get_signing_key_from_jwt(jwttoken).key
    aud = jwt.decode(jwttoken, options={"verify_signature": False})["aud"]
    return jwt.decode(jwttoken, pub_key, algorithms=["RS256"], audience=aud, options={"verify_exp": False})
