from rest_framework.renderers import JSONRenderer
from rest_framework.compat import (
    INDENT_SEPARATORS, LONG_SEPARATORS, SHORT_SEPARATORS
)
from rest_framework import status
import json
import six


class ApiRenderer(JSONRenderer):
    '''
    API Renderer
    '''
    @staticmethod
    def status_conditions_check_error(status_code, data):
        if status_code in [status.HTTP_303_SEE_OTHER]:
            message = data.get('error') if data.get('error', None) else data
            data = {
                'message': message['message'] if message.get('message') else message,
                'status': status.HTTP_303_SEE_OTHER
            }
        elif status_code in [status.HTTP_301_MOVED_PERMANENTLY]:
            message = data.get('error') if data.get('error', None) else data
            data = {
                'message': message['message'] if message.get('message') else message,
                'status': status.HTTP_301_MOVED_PERMANENTLY
            }
        else:
            error = data.get('error') if data.get('error', None) else data
            data = {
                'status': status_code,
                'message':  error.get('message') if error.get('message', None) else data
            }
        return data
        
    def status_conditions_check(self, status_code, data):
        if status_code in [status.HTTP_401_UNAUTHORIZED]:
            message = data.get('error') if data.get('error', None) else data
            data = {
                'message': message['message'] if message.get('message') else message,
                'status': status.HTTP_401_UNAUTHORIZED
            }
        elif status_code in [status.HTTP_302_FOUND, status.HTTP_404_NOT_FOUND]:
            message = data.get('error') if data.get('error', None) else data
            data = {
                'message': message['message'] if message.get('message') else message,
                'status': status.HTTP_302_FOUND
            }
        else:
            data = self.status_conditions_check_error(status_code, data)
        return data
    
    @staticmethod
    def success_status_check(data):
        if 'message' in data:
            extras = data['extras'] if data.get('extras') else None
            data = {
                'message': data['message'],
            }
            if extras:
                data['response'] = extras

        else:
            data = {
                'response': data,
            }
        data['status'] = status.HTTP_200_OK
        return data

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON, returning a bytestring.
        """
        if data is None:
            return bytes()

        renderer_context = renderer_context or {}
        indent = self.get_indent(accepted_media_type, renderer_context)
        
        if indent is None:
            separators = SHORT_SEPARATORS if self.compact else LONG_SEPARATORS
        else:
            separators = INDENT_SEPARATORS
        status_code = renderer_context['response'].status_code
        renderer_context['response'].status_code = status.HTTP_200_OK
        if status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            data = self.success_status_check(data)
        else:
            data = self.status_conditions_check(status_code, data)
        ret = json.dumps(
            data, cls=self.encoder_class,
            indent=indent, ensure_ascii=self.ensure_ascii,
            separators=separators
        )
        if isinstance(ret, six.text_type):
            ret = ret.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
            return bytes(ret.encode('utf-8'))
        return ret
