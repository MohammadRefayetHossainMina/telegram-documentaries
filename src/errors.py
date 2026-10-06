"""Shared failure type for the documentary pipeline."""


class PipelineError(Exception):
    """A stage failed in a way the chat can recover from."""
