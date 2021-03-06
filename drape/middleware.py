''' middlewares '''
import sys
import traceback

from . import config, response, http, cookie, session, version, router


_ctrl = None


def run(request):
    ''' run all middlewares '''
    global _ctrl
    if _ctrl is None:
        for middleware in _MIDDLEWARES:
            _ctrl = middleware(_ctrl)

    if _ctrl is None:
        return None

    return _ctrl(request)


def exception_traceback(func):
    ''' catch all exception and print them '''
    def process_exception(request):
        ' catch exception '
        try:
            return func(request)
        except Exception:
            body = ''
            if config.SYSTEM_IS_DEBUG:
                body += 'url: %s\n' % (
                    request.url(),
                )
                body += traceback.format_exc()

                body += 'environ:\n'
                for key, value in request.env.items():
                    body += '%s => %s\n' % (key, value)

            else:
                body = response.ERROR

            return response.Response(
                status=response.ERROR,
                headers={
                    'Content_Type': 'text/plain; charset=utf-8'
                },
                body=body
            )

    return process_exception


def httperror_processor(func):
    ''' catch all http error and make http response '''
    def process_exception(request):
        ' catch http error '
        try:
            return func(request)
        except http.HTTPError as exception:
            accept = request.chief_accept()
            if accept == 'application/json':
                return response.json_response(
                    obj=exception.body(),
                    status=exception.description,
                )
            else:
                return response.Response(
                    status=exception.description,
                    headers={
                        'Content-Type': 'text/plain; charset=utf-8'
                    },
                    body=exception.body()
                )

    return process_exception


def add_cookie(func):
    ''' start cookie '''
    def process_request(request):
        ' add cookie in request '
        request.cookie = cookie.Cookie(request)
        rsps = func(request)
        request.cookie.flush(rsps)

        return rsps

    return process_request


def add_session(func):
    ''' start session '''
    def process_request(request):
        ' add session in request '
        request.session = session.Session(request)
        rsps = func(request)
        request.session.save()

        return rsps

    return process_request


def add_extra_headers(func):
    ''' add extra headers '''
    def process_response(request):
        ' add headers '
        rsps = func(request)
        if not rsps.has_header('Content-Type'):
            rsps.set_header(
                'Content-Type',
                'text/html; charset=utf-8'
            )

        rsps.set_header(
            'X-Powered-By',
            'Python: %s, drape: %s' % (
                '%s.%s.%s' % (
                    sys.version_info.major,
                    sys.version_info.minor,
                    sys.version_info.micro
                ),
                version
            )
        )

        return rsps

    return process_response


def run_controller(_):
    ''' find controller by path and run '''
    router.compile_routes()

    def process_request(request):
        ' find controller and run '
        path = request.path()
        method = request.method()

        controller = router.find_controller(path, method)

        if not controller:
            raise http.NotFound(path)

        rsps = controller(request)
        if isinstance(rsps, response.Response):
            return rsps
        else:
            raise ValueError('not a response object: %s' % rsps)

    return process_request


_MIDDLEWARES = [
    run_controller,
    httperror_processor,
    add_extra_headers,
    add_session,
    add_cookie,
    exception_traceback,
]
