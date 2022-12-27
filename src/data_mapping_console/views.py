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
def getAllConfigurations(request):
    final_data = []
    error_text = error_code = None
    try:
        user = checkAuthorization(request)
        if request.method == 'GET':
            configurations = DMCConfigurations.objects.all()
            final_data = [c.serialize() for c in configurations]
        elif request.method == 'POST':
            data = json.loads(request.body)
            doc_id = data.get('doc_id')
            if not doc_id:
                raise Exception('Invalid doc_id')
            config_json = data.get('config')
            r = requests.post(request.scheme + '://' + request.get_host() + '/register/', headers=request.headers, json={
                'type': 'GOOGLE_DOC',
                'data': doc_id,
            })
            result = r.json()
            if r.status_code != 200 or 'error' in result:
                return return_response(None, result['error'][0]['code'], result['error'][0]['message'])
            else:
                configuration = DMCConfigurations.objects.create(
                    template_id=result['data']['id'], user_email=user['email'], config=config_json)
                configuration.save()
                final_data = configuration.serialize()
    except Exception as e:
        traceback.print_exc()
        error_code = 802
        error_text = f"Something went wrong!: {e}"
    finally:
        return return_response(final_data, error_code, error_text)


@csrf_exempt
def configurationOp(request, id):
    final_data = []
    error_text = error_code = None
    try:
        user = checkAuthorization(request)
        configuration = DMCConfigurations.objects.filter(pk=id).first()
        if not configuration:
            error_text = 'Not found'
            error_code = 404
        elif request.method == 'GET':
            final_data = configuration.serialize()
            req = requests.get(f"{os.getenv('TEMPLATOR_URL')}/{final_data['template_id']}")
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
