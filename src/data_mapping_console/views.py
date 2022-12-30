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
from pdf.views import register_template
import xml
from requests.auth import HTTPDigestAuth
from pprint import pprint


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
            url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            r = requests.get(url, headers={
                'Authorization': request.headers['Authorization'],
            })
            if r.status_code != 200:
                raise Exception('Invalid Authorization token provided')
            else:
                return r.json()
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
        # user = checkAuthorization(request)
        if request.method == 'GET':
            configurations = DMCConfigurations.objects.all()
            final_data = [c.serialize() for c in configurations]
        elif request.method == 'POST':
            data = json.loads(request.body)
            doc_id = data.get('doc_id')
            if not doc_id:
                raise Exception('Invalid doc_id')
            config_json = data.get('config')
            request._body = json.dumps({
                'type': 'GOOGLE_DOC',
                'data': doc_id,
                'template_engine': 'JINJA',
            })
            result = register_template(request)
            result = json.loads(result.content)
            if 'error' in result:
                raise Exception('Failed to register template')
            configuration = DMCConfigurations.objects.create(
                template_id=result['data']['id'], user_email='abc@example.com', config=config_json)
            configuration.save()
            final_data = configuration.serialize()
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)


@csrf_exempt
@api_view(['GET', 'PUT', 'DELETE'])
def configurationOp(request, config_id):
    final_data = []
    error_text = error_code = None
    try:
        # user = checkAuthorization(request)
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
        # user = checkAuthorization(request)
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


@csrf_exempt
@api_view(['GET'])
def parseODKForm(request, form_id):
    final_data = []
    error_text = error_code = None

    try:
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

        # print(container)
        final_data = container
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)
