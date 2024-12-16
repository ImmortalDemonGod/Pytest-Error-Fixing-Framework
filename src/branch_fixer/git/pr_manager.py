from dataclasses import dataclass

@dataclass
class PRDetails:
    id: int
    title: str
    status: str

class PRManager:
    def __init__(self, repository):
        self.repository = repository

    def create_pr(self, title, description):
        pass

    def close_pr(self, pr_id):
        pass

    def list_prs(self):
        pass
