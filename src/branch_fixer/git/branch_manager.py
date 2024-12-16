from dataclasses import dataclass

@dataclass
class BranchStatus:
    name: str
    is_active: bool

class BranchManager:
    def __init__(self, repository):
        self.repository = repository

    def create_branch(self, name):
        pass

    def delete_branch(self, name):
        pass

    def list_branches(self):
        pass
