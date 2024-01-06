class FastapiEventError(BaseException):
    pass


class ConfigurationError(FastapiEventError):
    pass


class MissingEventNameDuringRegistration(FastapiEventError):
    def __init__(self):
        super().__init__(
            "Event name cannot be determined during schema registration. "
            "Please ensure '__event_name__' is defined in your payload schema "
            "or 'event_name' is provided to @payload_schema.register() as a kwarg."
        )
