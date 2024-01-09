class FastapiEventError(BaseException):
    pass


class ConfigurationError(FastapiEventError):
    pass


class MissingEventNameError(FastapiEventError):
    pass


class MissingEventNameDuringRegistration(MissingEventNameError):
    def __init__(self):
        super().__init__(
            "Event name cannot be determined during schema registration. "
            "Please ensure '__event_name__' is defined in your payload schema "
            "or 'event_name' is provided to @payload_schema.register() as a kwarg."
        )


class MissingEventNameDuringDispatch(MissingEventNameError):
    def __init__(self):
        super().__init__(
            "Event name cannot be determined during dispatch. "
            "Please ensure 'event_name' is provided to dispatch() as an argument "
            "or '__event_name__' is defined in your payload schema."
        )


class MultiplePayloadsDetectedDuringDispatch(FastapiEventError, ValueError):
    def __init__(self):
        super().__init__(
            "Multiple payloads detected during dispatch. "
            "Please ensure you're not providing both dict and pydantic.Model at the same time."
        )
