import abc

class Template(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_context(self, run: dict, tasks: dict) -> dict:
        raise NotImplementedError

    @abc.abstractmethod
    def get_subject(self, run: dict, tasks: dict) -> dict:
        raise NotImplementedError
