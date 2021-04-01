from typing import Any, Callable, Dict, Optional

from airflow.exceptions import AirflowSkipException
from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.providers.http.hooks.http import HttpHook
from airflow.utils.decorators import apply_defaults

class SimpleHttpSentinel(BaseOperator):
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