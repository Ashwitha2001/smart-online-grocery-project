from django.utils.deprecation import MiddlewareMixin
import logging

# Set up logging
logger = logging.getLogger(__name__)

class LoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Log the request method and path
        logger.info(f'Request Method: {request.method}, Request Path: {request.path}')

    def process_response(self, request, response):
        # Optionally, log the response status code
        logger.info(f'Response Status: {response.status_code}')
        return response
