# From https://github.com/apache/airflow/blob/master/airflow/providers/http/operators/http.py
from typing import Any, Callable, Dict, Optional

from airflow.exceptions import AirflowSkipException
from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.providers.http.hooks.http import HttpHook
from airflow.utils.decorators import apply_defaults

class SimpleHttpSentinel(BaseOperator):
    """
    Calls an endpoint on an HTTP system to execute an action
    .. seealso::
        For more information on how to use this operator, take a look at the guide:
        :ref:`howto/operator:SimpleHttpOperator`
    :param http_conn_id: The :ref:`http connection<howto/connection:http>` to run
        the operator against
    :type http_conn_id: str
    :param endpoint: The relative part of the full url. (templated)
    :type endpoint: str
    :param method: The HTTP method to use, default = "POST"
    :type method: str
    :param data: The data to pass. POST-data in POST/PUT and params
        in the URL for a GET request. (templated)
    :type data: For POST/PUT, depends on the content-type parameter,
        for GET a dictionary of key/value string pairs
    :param headers: The HTTP headers to be added to the GET request
    :type headers: a dictionary of string key/value pairs
    :param response_check: A check against the 'requests' response object.
        The callable takes the response object as the first positional argument
        and optionally any number of keyword arguments available in the context dictionary.
        It should return True for 'pass' and False otherwise.
    :type response_check: A lambda or defined function.
    :param response_filter: A function allowing you to manipulate the response
        text. e.g response_filter=lambda response: json.loads(response.text).
        The callable takes the response object as the first positional argument
        and optionally any number of keyword arguments available in the context dictionary.
    :type response_filter: A lambda or defined function.
    :param extra_options: Extra options for the 'requests' library, see the
        'requests' documentation (options to modify timeout, ssl, etc.)
    :type extra_options: A dictionary of options, where key is string and value
        depends on the option that's being modified.
    :param log_response: Log the response (default: False)
    :type log_response: bool
    :param auth_type: The auth type for the service
    :type auth_type: AuthBase of python requests lib
    """
    
    template_fields = [
        'endpoint',
        'data',
        'headers',
    ]
    template_fields_renderers = {'headers': 'json', 'data': 'py'}
    template_ext = ()
    ui_color = '#ffff00'

    @apply_defaults
    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        method: str = 'POST',
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        response_check: Optional[Callable[..., bool]] = None,
        response_filter: Optional[Callable[..., Any]] = None,
        extra_options: Optional[Dict[str, Any]] = None,
        http_conn_id: str = 'http_default',
        log_response: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.http_conn_id = http_conn_id
        self.method = method
        self.endpoint = endpoint
        self.headers = headers or {}
        self.data = data or {}
        self.response_check = response_check
        self.response_filter = response_filter
        self.extra_options = extra_options or {}
        self.log_response = log_response
        if kwargs.get('xcom_push') is not None:
            raise AirflowException("'xcom_push' was deprecated, use 'BaseOperator.do_xcom_push' instead")

    def execute(self, context: Dict[str, Any]) -> Any:
        from airflow.utils.operator_helpers import make_kwargs_callable

        http = HttpHook(self.method, http_conn_id=self.http_conn_id)

        self.log.info("Calling HTTP method")

        response = http.run(self.endpoint, self.data, self.headers, self.extra_options)
        if self.log_response:
            self.log.info(response.text)
        if self.response_check:
            kwargs_callable = make_kwargs_callable(self.response_check)
            if not kwargs_callable(response, **context):
                raise AirflowSkipException("Response check returned False.")
        if self.response_filter:
            kwargs_callable = make_kwargs_callable(self.response_filter)
            return kwargs_callable(response, **context)
        return response.text