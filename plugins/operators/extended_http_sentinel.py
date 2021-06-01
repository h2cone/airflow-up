# From https://gist.github.com/nndd91/56c2337b89e2b8705a90da088020b609
from typing import Any, Dict

from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowSkipException
from airflow.exceptions import AirflowException
from airflow.hooks.http_hook import HttpHook

"""
Extend Simple Http Operator with a callable function to formulate data. This data function will
be able to access the context to retrieve data such as task instance. This allow us to write cleaner 
code rather than writing one long template line to formulate the json data.
"""


class ExtendedHttpSentinel(SimpleHttpOperator):
    template_fields = [
        "endpoint",
        "data",
        "headers",
    ]
    template_fields_renderers = {"headers": "json", "data": "py"}
    template_ext = ()
    ui_color = "#ffff00"

    @apply_defaults
    def __init__(self, data_fn, *args, **kwargs):
        super(ExtendedHttpSentinel, self).__init__(*args, **kwargs)
        if not callable(data_fn):
            raise AirflowException("`data_fn` param must be callable")
        self.data_fn = data_fn
        self.context = None

    def execute(self, context: Dict[str, Any]) -> Any:
        from airflow.utils.operator_helpers import make_kwargs_callable

        self.context = context
        data = self.execute_callable(context)
        http = HttpHook(self.method, http_conn_id=self.http_conn_id)

        self.log.info("Calling HTTP method")
        self.log.info("The data to pass: {}".format(data))

        response = http.run(self.endpoint, data, self.headers, self.extra_options)
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

    def execute_callable(self, context):
        return self.data_fn(**context)
