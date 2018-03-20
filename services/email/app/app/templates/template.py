from typing import List
from abc import ABCMeta, abstractmethod


class Template(metaclass=ABCMeta):
    @abstractmethod
    def get_context(self, run: dict, tasks: List[dict]) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_subject(self, run: dict, tasks: List[dict]) -> str:
        raise NotImplementedError
